"""Windows UI element targeting tool handlers (FAZA 14).

Element-based UI automation using Windows UI Automation (UIA) via the
uiautomation library. Reduces reliance on raw coordinate clicks.

Tool handlers:
  - computer_find_elements  — search UI elements by app/control_type/name/…
  - computer_click_element  — click (or invoke) a matched element
  - computer_set_text_element — set text value on a matched element
  - computer_get_element_text — read text from a matched element

Coordinate click (FAZA 13 computer_click) remains as fallback.
"""
from __future__ import annotations

import sys
import time
from typing import Any


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _ensure_uia():
    """Lazy-import uiautomation and ensure COM is initialized on this thread."""
    if sys.platform != "win32":
        raise RuntimeError("Element targeting tools are only supported on Windows.")
    import uiautomation as auto  # type: ignore[import-not-found]
    # uiautomation auto-initializes COM on first call, but we ensure it here.
    return auto


def _find_first_element(auto, criteria: dict[str, Any]):
    """Find the first UIA element matching the given criteria.

    Supported criteria keys:
      - app             (str): process name, e.g. "notepad.exe"
      - title_contains  (str): substring match on window title
      - control_type    (str): UIA ControlType name, e.g. "Edit", "Button", "Window"
      - name            (str): exact or substring match on element Name
      - automation_id   (str): exact AutomationId
      - class_name      (str): exact ClassName

    Returns the element or None. Raises ValueError if app/title_contains
    don't match any top-level window.
    """
    app_filter = criteria.get("app")
    title_filter = criteria.get("title_contains")
    control_type = criteria.get("control_type")
    name_filter = criteria.get("name")
    auto_id = criteria.get("automation_id")
    class_name = criteria.get("class_name")

    # --- Step 1: find the target window ---
    root = auto.GetRootControl()
    if app_filter or title_filter:
        condition = None
        if app_filter and title_filter:
            condition = lambda c: (
                c.ClassName == app_filter and title_filter.lower() in (c.Name or "").lower()
            )
        elif app_filter:
            condition = lambda c: c.ClassName == app_filter
        elif title_filter:
            condition = lambda c: title_filter.lower() in (c.Name or "").lower()

        windows = [c for c in root.GetChildren() if condition(c)] if condition else []
        if not windows:
            raise ValueError(
                f"No window found matching app={app_filter!r}, title_contains={title_filter!r}."
            )
        target = windows[0]
    else:
        target = root

    # --- Step 2: search within the window for the specific element ---
    if control_type or name_filter or auto_id or class_name:
        # Build a composite condition
        def _match(el):
            if control_type:
                try:
                    if el.ControlTypeName != control_type:
                        return False
                except Exception:
                    return False
            if name_filter:
                try:
                    if name_filter.lower() not in (el.Name or "").lower():
                        return False
                except Exception:
                    return False
            if auto_id:
                try:
                    if el.AutomationId != auto_id:
                        return False
                except Exception:
                    return False
            if class_name:
                try:
                    if el.ClassName != class_name:
                        return False
                except Exception:
                    return False
            return True

        # Search descendants
        matched = None
        for child in target.GetDescendants():
            if _match(child):
                matched = child
                break

        if matched is None:
            raise ValueError(
                f"No element found matching criteria in window {target.Name!r}."
            )
        return matched

    return target


def _describe_element(el) -> dict[str, str]:
    """Return a safe dict summary of a UIA element's key properties."""
    try:
        return {
            "name": el.Name or "",
            "control_type": el.ControlTypeName or "",
            "automation_id": el.AutomationId or "",
            "class_name": el.ClassName or "",
            "bounding_rect": str(getattr(el, "BoundingRectangle", "")),
            "is_enabled": str(getattr(el, "IsEnabled", "")),
        }
    except Exception:
        return {"error": "Could not read element properties."}


# ---------------------------------------------------------------------------
# Tool handlers
# ---------------------------------------------------------------------------


def _handle_find_elements(arguments: dict[str, Any]) -> dict[str, Any]:
    """Find UI elements matching search criteria."""
    auto = _ensure_uia()

    app = str(arguments.get("app", "")).strip() or None
    title_contains = str(arguments.get("title_contains", "")).strip() or None
    control_type = str(arguments.get("control_type", "")).strip() or None
    name = str(arguments.get("name", "")).strip() or None
    automation_id = str(arguments.get("automation_id", "")).strip() or None
    class_name = str(arguments.get("class_name", "")).strip() or None
    max_results = max(1, min(50, int(arguments.get("max_results", 10) or 10)))

    if not any([app, title_contains, control_type, name, automation_id, class_name]):
        raise ValueError("At least one search criterion is required (app, title_contains, control_type, name, automation_id, or class_name).")

    criteria = {k: v for k, v in {
        "app": app,
        "title_contains": title_contains,
        "control_type": control_type,
        "name": name,
        "automation_id": automation_id,
        "class_name": class_name,
    }.items() if v is not None}

    root = auto.GetRootControl()
    windows: list = []
    if app or title_contains:
        if app and title_contains:
            windows = [
                c for c in root.GetChildren()
                if c.ClassName == app and title_contains.lower() in (c.Name or "").lower()
            ]
        elif app:
            windows = [c for c in root.GetChildren() if c.ClassName == app]
        elif title_contains:
            windows = [c for c in root.GetChildren() if title_contains.lower() in (c.Name or "").lower()]
        if not windows:
            return {"elements": [], "count": 0, "message": f"No windows found matching app={app!r}, title_contains={title_contains!r}.", "search_criteria": criteria}
    else:
        windows = [root]

    elements = []
    for win in windows[:3]:  # search up to 3 matching windows
        search_root = win
        if control_type or name or automation_id or class_name:
            for child in search_root.GetDescendants():
                if len(elements) >= max_results:
                    break
                match = True
                if control_type:
                    try:
                        if child.ControlTypeName != control_type:
                            match = False
                    except Exception:
                        match = False
                if match and name:
                    try:
                        if name.lower() not in (child.Name or "").lower():
                            match = False
                    except Exception:
                        match = False
                if match and automation_id:
                    try:
                        if child.AutomationId != automation_id:
                            match = False
                    except Exception:
                        match = False
                if match and class_name:
                    try:
                        if child.ClassName != class_name:
                            match = False
                    except Exception:
                        match = False
                if match:
                    elements.append(_describe_element(child))

    return {
        "elements": elements,
        "count": len(elements),
        "message": f"Found {len(elements)} element(s).",
        "search_criteria": criteria,
    }


def _handle_click_element(arguments: dict[str, Any]) -> dict[str, Any]:
    """Click a UI element identified by its properties."""
    auto = _ensure_uia()

    app = str(arguments.get("app", "")).strip() or None
    title_contains = str(arguments.get("title_contains", "")).strip() or None
    control_type = str(arguments.get("control_type", "")).strip() or None
    name = str(arguments.get("name", "")).strip() or None
    automation_id = str(arguments.get("automation_id", "")).strip() or None
    class_name = str(arguments.get("class_name", "")).strip() or None

    if not app and not title_contains:
        raise ValueError("app or title_contains is required to locate the target window.")

    criteria = {k: v for k, v in {
        "app": app, "title_contains": title_contains, "control_type": control_type,
        "name": name, "automation_id": automation_id, "class_name": class_name,
    }.items() if v}

    element = _find_first_element(auto, criteria)

    try:
        element.Click()
    except Exception as e:
        # Fallback: try Invoke pattern for buttons
        try:
            invoke_pattern = element.GetPattern(auto.PatternId.InvokePattern)
            invoke_pattern.Invoke()
        except Exception:
            raise ValueError(f"Could not click element: {e}") from e

    time.sleep(0.05)
    return {
        "message": f"Clicked element: {element.Name or element.ControlTypeName}.",
        "element": _describe_element(element),
    }


def _handle_set_text_element(arguments: dict[str, Any]) -> dict[str, Any]:
    """Set text on a UI element (Edit control, etc.)."""
    auto = _ensure_uia()

    text = str(arguments.get("text", ""))
    if not text:
        raise ValueError("text is required to set on the element.")

    app = str(arguments.get("app", "")).strip() or None
    title_contains = str(arguments.get("title_contains", "")).strip() or None
    control_type = str(arguments.get("control_type", "")).strip() or None
    name = str(arguments.get("name", "")).strip() or None
    automation_id = str(arguments.get("automation_id", "")).strip() or None
    class_name = str(arguments.get("class_name", "")).strip() or None

    if not app and not title_contains:
        raise ValueError("app or title_contains is required to locate the target window.")

    criteria = {k: v for k, v in {
        "app": app, "title_contains": title_contains, "control_type": control_type,
        "name": name, "automation_id": automation_id, "class_name": class_name,
    }.items() if v}

    element = _find_first_element(auto, criteria)

    # Try ValuePattern first (preferred for Edit controls)
    try:
        value_pattern = element.GetPattern(auto.PatternId.ValuePattern)
        value_pattern.SetValue(text)
    except Exception:
        # Fallback: set focus and type via keyboard simulation
        element.SetFocus()
        time.sleep(0.05)
        element.SendKeys(text)

    return {
        "message": f"Set text on element: {element.Name or element.ControlTypeName}.",
        "element": _describe_element(element),
        "text_length": len(text),
    }


def _handle_get_element_text(arguments: dict[str, Any]) -> dict[str, Any]:
    """Read text from a UI element."""
    auto = _ensure_uia()

    app = str(arguments.get("app", "")).strip() or None
    title_contains = str(arguments.get("title_contains", "")).strip() or None
    control_type = str(arguments.get("control_type", "")).strip() or None
    name = str(arguments.get("name", "")).strip() or None
    automation_id = str(arguments.get("automation_id", "")).strip() or None
    class_name = str(arguments.get("class_name", "")).strip() or None

    if not app and not title_contains:
        raise ValueError("app or title_contains is required to locate the target window.")

    criteria = {k: v for k, v in {
        "app": app, "title_contains": title_contains, "control_type": control_type,
        "name": name, "automation_id": automation_id, "class_name": class_name,
    }.items() if v}

    element = _find_first_element(auto, criteria)

    text_value = ""
    try:
        # Try ValuePattern first (Edit controls)
        value_pattern = element.GetPattern(auto.PatternId.ValuePattern)
        text_value = value_pattern.Value or ""
    except Exception:
        pass

    name_value = ""
    try:
        name_value = element.Name or ""
    except Exception:
        pass

    return {
        "message": f"Read from element: {element.Name or element.ControlTypeName}.",
        "element": _describe_element(element),
        "text": text_value or name_value,
        "source": "value" if text_value else "name",
    }


def make_handlers() -> dict[str, Any]:
    return {
        "computer_find_elements": _handle_find_elements,
        "computer_click_element": _handle_click_element,
        "computer_set_text_element": _handle_set_text_element,
        "computer_get_element_text": _handle_get_element_text,
    }