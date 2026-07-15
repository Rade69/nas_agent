"""Gmail draft-preparation adapter (docs/EMAIL_COMPOSE_TOOL_PLAN_V2_GMAIL.md).

Faza A (2026-07-13): narrow, allowlist-only operations for filling a Gmail
compose draft. This module has NO click/keypress capability by design — it
can only DOM.focus + Input.insertText into pre-identified To/Subject/Body
fields. There is no method here that could reach the Send button even by
mistake, which is the plan's core "structurally unreachable Send" guarantee
(see plan section 4.4) — it is not a generic browser-automation tool.

Chrome runs in an isolated, app-owned profile (own --user-data-dir, never
the user's regular Chrome profile) with a loopback-only, randomly-chosen
CDP debug port that only this process connects to. Confirmed working
end-to-end (including the WRITE path) in the Faza A0 spike — agent_reports/
2026-07-13_email-faza-a0-spike-findings.md documents the live-tested
selectors and the one correction to the plan (compose must be opened via
Page.navigate AFTER confirming login, not as the initial launch URL, since
Google's OAuth redirect chain drops the #compose=new hash fragment).

Synchronous by design (websockets.sync.client), matching ToolExecutor's
synchronous handler contract (app/agent/tool_executor.py) — see
docs/EMAIL_COMPOSE_TOOL_SECURITY_REVIEW_2026-07-13.md section 3.9 for why an
async handler registered as-is would be unsafe under the current executor.

Manual end-to-end verification against a real Gmail account (agent_reports/
2026-07-13_email-faza-a-gmail-draft-adapter.md) found and fixed four real
bugs beyond the A0 spike's findings — see that report for the full story;
the two most important fixes are baked into this module:
  - login/navigation detection needs to wait for the URL to actually settle
    (a CDP target can exist before the page finishes loading/redirecting);
  - CDP's own DOM.querySelector(nodeId=..., selector=...) unreliably missed
    elements confirmed present by a JS-side scoped query, so field lookup
    uses Runtime.callFunctionOn on a resolved node object instead.
"""
from __future__ import annotations

import json
import socket
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import httpx
from websockets.sync.client import ClientConnection, connect as ws_connect

from app.core.errors import AppError

CHROME_CANDIDATES = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
]
INBOX_URL = "https://mail.google.com/mail/u/0/#inbox"
COMPOSE_URL = "https://mail.google.com/mail/u/0/#inbox?compose=new"
GMAIL_ORIGIN = "https://mail.google.com/"
LAUNCH_TIMEOUT_S = 15.0

# Selectors confirmed live against real Gmail in the Faza A0 spike. `name`
# and `role` attributes are used wherever possible because they are
# language-independent — aria-label text ("Predmet"/"Subject", "Tijelo
# poruke"/"Message Body") varies with the Gmail account's interface
# language and must never be relied on for targeting.
SELECTOR_DIALOG = '[role="dialog"]'
SELECTOR_SUBJECT = 'input[name="subjectbox"]'
SELECTOR_BODY = '[role="textbox"][contenteditable="true"]'
SELECTOR_RECIPIENT = 'input[role="combobox"]'


def _find_chrome() -> Path:
    for candidate in CHROME_CANDIDATES:
        if candidate.exists():
            return candidate
    raise AppError(
        "CHROME_NOT_FOUND",
        "Google Chrome is not installed at a known location.",
        status_code=500,
    )


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@dataclass
class GmailSession:
    """Handle for one isolated-Chrome CDP session — owns the Chrome
    subprocess and the single CDP WebSocket connection to its Gmail tab."""

    process: subprocess.Popen
    port: int
    profile_dir: Path
    ws: ClientConnection
    _next_id: int = field(default=1, repr=False)

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        self.ws.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("id") == request_id:
                if "error" in message:
                    raise AppError(
                        "GMAIL_CDP_ERROR",
                        f"CDP call {method} failed: {message['error']}",
                        status_code=502,
                    )
                return message.get("result", {})

    def close(self) -> None:
        try:
            self.ws.close()
        except Exception:
            pass
        try:
            self.process.terminate()
        except Exception:
            pass


def launch_isolated_chrome(data_dir: Path) -> GmailSession:
    """Start Chrome in a fresh/persistent, app-owned profile — never the
    user's regular Chrome profile or history. Loopback-only debug port,
    chosen at random each launch, connected to by no one but this process."""
    chrome = _find_chrome()
    profile_dir = data_dir / "gmail_isolated_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)
    port = _free_port()

    process = subprocess.Popen(
        [
            str(chrome),
            f"--remote-debugging-port={port}",
            "--remote-debugging-address=127.0.0.1",
            f"--user-data-dir={profile_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            INBOX_URL,
        ]
    )

    deadline = time.monotonic() + LAUNCH_TIMEOUT_S
    ws_url: str | None = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"http://127.0.0.1:{port}/json", timeout=1.0)
            targets = [
                t
                for t in response.json()
                if t.get("type") == "page" and "mail.google.com" in t.get("url", "")
            ]
            if targets:
                ws_url = targets[0]["webSocketDebuggerUrl"]
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.3)

    if ws_url is None:
        process.terminate()
        raise AppError(
            "GMAIL_LAUNCH_TIMEOUT",
            "Chrome did not produce a reachable Gmail page target in time.",
            status_code=502,
        )

    ws = ws_connect(ws_url, max_size=10 * 1024 * 1024)
    session = GmailSession(process=process, port=port, profile_dir=profile_dir, ws=ws)
    session.call("DOM.enable")
    session.call("Runtime.enable")
    session.call("Page.enable")
    # A CDP target existing does not mean the initial navigation has
    # finished. Gmail's own load path redirects through
    # accounts.google.com (session/cookie validation) before landing back
    # on mail.google.com, and a target briefly shows about:blank with
    # document.readyState already "complete" while that's in flight —
    # checking readyState alone observes that transient state and wrongly
    # concludes the profile is logged out. Wait for the URL itself to
    # settle (unchanged across two consecutive checks, not about:blank)
    # before handing the session back.
    _wait_for_url_to_settle(session)
    return session


def _wait_for_url_to_settle(session: GmailSession, timeout_s: float = 15.0) -> None:
    deadline = time.monotonic() + timeout_s
    previous_url: str | None = None
    while time.monotonic() < deadline:
        current = _current_url(session)
        if current and current != "about:blank" and current == previous_url:
            return
        previous_url = current
        time.sleep(0.5)


def _current_url(session: GmailSession) -> str:
    result = session.call("Runtime.evaluate", {"expression": "location.href", "returnByValue": True})
    return result.get("result", {}).get("value", "")


def is_logged_in(session: GmailSession) -> bool:
    """True only if the current page is actually on mail.google.com — if the
    isolated profile has no session yet, Gmail's own JS redirects to
    accounts.google.com, which this catches without guessing at DOM content."""
    return _current_url(session).startswith(GMAIL_ORIGIN)


def _verify_origin(session: GmailSession) -> None:
    url = _current_url(session)
    if not url.startswith(GMAIL_ORIGIN):
        raise AppError(
            "GMAIL_ORIGIN_MISMATCH",
            f"Expected an origin starting with {GMAIL_ORIGIN!r}, got {url!r}.",
            status_code=409,
        )


def _count_matches(session: GmailSession, root_node_id: int, selector: str) -> int:
    result = session.call("DOM.querySelectorAll", {"nodeId": root_node_id, "selector": selector})
    return len(result.get("nodeIds", []))


def open_compose(session: GmailSession) -> int:
    """Navigate to a fresh compose draft and return its dialog nodeId.

    Faza A0 correction: compose is opened via Page.navigate AFTER confirming
    login, never as Chrome's initial launch URL — Google's OAuth redirect
    chain drops the #compose=new hash fragment on a cold, logged-out profile.

    Fail-closed: raises if login is missing, if zero compose dialogs appear,
    or if more than one is open (never guesses which draft is "the" one —
    same principle the plan applies to Outlook's multi-window case).
    """
    if not is_logged_in(session):
        raise AppError(
            "GMAIL_NOT_LOGGED_IN",
            "The isolated Gmail profile is not logged in. Manual login is required first.",
            status_code=409,
        )

    session.call("Page.navigate", {"url": COMPOSE_URL})
    _wait_for_url_to_settle(session)
    _verify_origin(session)

    # The URL updates to include "?compose=new" synchronously, but Gmail's
    # own JS still has to render the compose panel into the DOM after that —
    # a single immediate check can catch it before the dialog exists yet.
    # Poll briefly instead of assuming URL-settled implies DOM-ready.
    root_node_id = None
    dialog_count = 0
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        document = session.call("DOM.getDocument", {"depth": -1, "pierce": True})
        root_node_id = document["root"]["nodeId"]
        dialog_count = _count_matches(session, root_node_id, SELECTOR_DIALOG)
        if dialog_count > 0:
            break
        time.sleep(0.3)

    if dialog_count == 0:
        raise AppError("GMAIL_COMPOSE_NOT_FOUND", "No compose dialog appeared after navigation.", status_code=502)
    if dialog_count > 1:
        raise AppError(
            "GMAIL_MULTIPLE_COMPOSE_DIALOGS",
            f"Found {dialog_count} compose dialogs; refusing to guess which one to use. "
            "Close other drafts first.",
            status_code=409,
        )

    query = session.call("DOM.querySelector", {"nodeId": root_node_id, "selector": SELECTOR_DIALOG})
    dialog_node_id = query.get("nodeId")
    if not dialog_node_id:
        raise AppError("GMAIL_COMPOSE_NOT_FOUND", "Compose dialog node could not be resolved.", status_code=502)
    return dialog_node_id


def _find_in_dialog(session: GmailSession, dialog_node_id: int, selector: str) -> int:
    # Faza A manual verification (2026-07-13): the CDP DOM domain's own
    # DOM.querySelector(nodeId=..., selector=...) unreliably returned no
    # match for elements confirmed present by a JS-side query scoped to the
    # same dialog subtree (Runtime.callFunctionOn + querySelector on the
    # resolved node object) — root cause not fully isolated (suspected DOM
    # domain node-tree staleness after Gmail's own React-style re-renders),
    # but the JS-scoped approach was reproducibly reliable in manual testing
    # against live Gmail, so it is used here instead. This is still a plain
    # read-only DOM query narrowly scoped to the dialog's own subtree via
    # objectId, not arbitrary script execution against the page.
    resolved = session.call("DOM.resolveNode", {"nodeId": dialog_node_id})
    dialog_object_id = resolved["object"]["objectId"]
    result = session.call(
        "Runtime.callFunctionOn",
        {
            "objectId": dialog_object_id,
            "functionDeclaration": f"function() {{ return this.querySelector({json.dumps(selector)}); }}",
            "returnByValue": False,
        },
    )
    child_object_id = result.get("result", {}).get("objectId")
    if not child_object_id:
        raise AppError(
            "GMAIL_FIELD_NOT_FOUND",
            f"Could not find an element matching {selector!r} inside the compose dialog.",
            status_code=502,
        )
    node_info = session.call("DOM.requestNode", {"objectId": child_object_id})
    node_id = node_info.get("nodeId")
    if not node_id:
        raise AppError(
            "GMAIL_FIELD_NOT_FOUND",
            f"Element matching {selector!r} was found but could not be resolved to a DOM node.",
            status_code=502,
        )
    return node_id


def _focus_and_insert(session: GmailSession, node_id: int, text: str) -> None:
    # DOM.focus targets the node directly — no synthesized mouse click, so
    # there is no coordinate/timing window where a click could land on the
    # wrong element. Input.insertText is the same primitive a real user's
    # IME/paste uses, not a per-character keypress simulation.
    session.call("DOM.focus", {"nodeId": node_id})
    session.call("Input.insertText", {"text": text})


def set_subject_field(session: GmailSession, dialog_node_id: int, subject: str) -> None:
    node_id = _find_in_dialog(session, dialog_node_id, SELECTOR_SUBJECT)
    _focus_and_insert(session, node_id, subject)


def set_body_field(session: GmailSession, dialog_node_id: int, body: str) -> None:
    node_id = _find_in_dialog(session, dialog_node_id, SELECTOR_BODY)
    _focus_and_insert(session, node_id, body)


def set_recipient_field(
    session: GmailSession,
    dialog_node_id: int,
    to: str,
    cc: str | None = None,
    bcc: str | None = None,
) -> None:
    node_id = _find_in_dialog(session, dialog_node_id, SELECTOR_RECIPIENT)
    _focus_and_insert(session, node_id, to)
    # Faza A limitation (spike did not test the Cc/Bcc reveal links or their
    # field selectors) — explicit error instead of silently dropping cc/bcc.
    if cc or bcc:
        raise AppError(
            "GMAIL_CC_BCC_NOT_SUPPORTED",
            "Cc/Bcc are not supported by this adapter yet (Faza A limitation).",
            status_code=501,
        )


def _read_field_value(session: GmailSession, dialog_node_id: int, selector: str) -> str:
    node_id = _find_in_dialog(session, dialog_node_id, selector)
    resolved = session.call("DOM.resolveNode", {"nodeId": node_id})
    object_id = resolved["object"]["objectId"]
    result = session.call(
        "Runtime.callFunctionOn",
        {
            "objectId": object_id,
            "functionDeclaration": "function() { return this.value !== undefined ? this.value : this.innerText; }",
            "returnByValue": True,
        },
    )
    return result.get("result", {}).get("value", "") or ""


def verify_draft_values(session: GmailSession, dialog_node_id: int, expected_subject: str, expected_to: str) -> bool:
    subject_value = _read_field_value(session, dialog_node_id, SELECTOR_SUBJECT)
    to_value = _read_field_value(session, dialog_node_id, SELECTOR_RECIPIENT)
    return subject_value == expected_subject and expected_to in to_value


def close_isolated_chrome(session: GmailSession) -> None:
    session.close()
