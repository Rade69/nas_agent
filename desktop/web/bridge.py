"""desktop/web/bridge.py — RickyWebBridge (CR-2).

QObject izložen React-u preko QWebChannel-a. Zamjenjuje Electron preload/IPC:
React `window.ricky.*` pozivi idu na ove allowlisted slotove, koji delegiraju na
postojeći Python BackendClient / native Qt shell. Nema generičkog Python prolaza.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Signal, Slot

from desktop.core.process_bridge import BackendClient


class RickyWebBridge(QObject):
    # Python → JS signali (voice + native events).
    voiceStateChanged = Signal(str)
    voiceInputLevelChanged = Signal(float)
    voiceOutputLevelChanged = Signal(float)
    voiceConnectedChanged = Signal(bool)
    voiceUserTranscript = Signal(str)
    voiceAssistantTranscript = Signal(str)
    voiceError = Signal(str)
    voiceReconnecting = Signal()
    voiceInputStreamOpened = Signal(str)
    voiceInputWarning = Signal(str)
    confirmationRequired = Signal(dict)
    confirmationResult = Signal(dict)
    killSwitchTriggered = Signal()
    companionVoiceState = Signal(str)
    companionToggleVoice = Signal()

    def __init__(self, client: BackendClient, window=None, controller=None, parent=None) -> None:
        super().__init__(parent)
        self._client = client
        self._window = window
        self._controller = controller

    # ── backend helpers ──────────────────────────────────────────────────────

    def _get(self, path: str) -> Any:
        return self._client.request(path, timeout=10.0).json()

    def _send(self, path: str, method: str, body: dict | None = None) -> Any:
        return self._client.request(path, method=method, json=body if body is not None else {}, timeout=15.0).json()

    # ── settings ─────────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def getSettings(self) -> Any:
        from desktop.core.debug_log import debugLog

        debugLog("[bridge] getSettings")
        return self._get("/settings")

    @Slot("QVariant", result="QVariant")
    def updateSettings(self, payload: Any) -> Any:
        return self._send("/settings", "PATCH", dict(payload or {}))

    # ── events ───────────────────────────────────────────────────────────────

    @Slot(str, result="QVariant")
    def listEvents(self, since: str) -> Any:
        query = f"?since={since}" if since else ""
        return self._get(f"/events{query}")

    # ── plans ────────────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def listPlans(self) -> Any:
        return self._get("/plans")

    @Slot("QVariant", result="QVariant")
    def createPlan(self, payload: Any) -> Any:
        return self._send("/plans", "POST", dict(payload or {}))

    @Slot(str, result="QVariant")
    def getPlan(self, plan_id: str) -> Any:
        return self._get(f"/plans/{plan_id}")

    @Slot("QVariant", result="QVariant")
    def updatePlan(self, payload: Any) -> Any:
        data = dict(payload or {})
        return self._send(f"/plans/{data.pop('planId', '')}", "PATCH", data)

    @Slot("QVariant", result="QVariant")
    def updatePlanStep(self, payload: Any) -> Any:
        data = dict(payload or {})
        pid = data.pop("planId", "")
        sid = data.pop("stepId", "")
        return self._send(f"/plans/{pid}/steps/{sid}", "PATCH", data)

    # ── confirmations ────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def listPendingConfirmations(self) -> Any:
        return self._get("/confirmations/pending")

    @Slot("QVariant", result="QVariant")
    def createConfirmation(self, payload: Any) -> Any:
        return self._send("/confirmations", "POST", dict(payload or {}))

    @Slot(str, result="QVariant")
    def approveConfirmation(self, confirmation_id: str) -> Any:
        result = self._send(f"/confirmations/{confirmation_id}/approve", "POST")
        # CR-4: voice retry originalnog tool call-a sa odobrenim confirmation_id.
        if self._controller is not None:
            self._controller.approve_voice_confirmation(confirmation_id)
        return result

    @Slot(str, result="QVariant")
    def rejectConfirmation(self, confirmation_id: str) -> Any:
        result = self._send(f"/confirmations/{confirmation_id}/reject", "POST")
        if self._controller is not None:
            self._controller.reject_voice_confirmation(confirmation_id)
        return result

    @Slot(str, result="QVariant")
    def cancelConfirmation(self, confirmation_id: str) -> Any:
        return self._send(f"/confirmations/{confirmation_id}", "DELETE")

    @Slot("QVariant", result="QVariant")
    def publishConfirmationResult(self, payload: Any) -> Any:
        # QM: rezultat retryja iz mini prozora -> aktivna sesija (best-effort).
        return {"ok": True}

    @Slot(str, result="QVariant")
    def rewriteText(self, payload_json: str) -> Any:
        return self._send("/text/rewrite", "POST", {"text": payload_json})

    # ── tools ────────────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def getToolSpecs(self) -> Any:
        return self._get("/tools").get("tools", [])

    @Slot("QVariant", result="QVariant")
    def executeTool(self, payload: Any) -> Any:
        return self._send("/tools/execute", "POST", dict(payload or {}))

    @Slot(result="QVariant")
    def cancelAllExecutions(self) -> Any:
        return self._send("/tools/executions/cancel-all", "POST")

    # ── screenshots ──────────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def listScreenshots(self) -> Any:
        return self._get("/screenshots")

    @Slot(result="QVariant")
    def deleteAllScreenshots(self) -> Any:
        return self._send("/screenshots", "DELETE")

    # ── browser bridge ───────────────────────────────────────────────────────

    @Slot(result="QVariant")
    def getBrowserBridgeStatus(self) -> Any:
        return self._get("/browser-bridge/status")

    @Slot("QVariant", result="QVariant")
    def startBrowserPairing(self, payload: Any) -> Any:
        return self._send("/browser-bridge/pairing/start", "POST", dict(payload or {}))

    @Slot("QVariant", result="QVariant")
    def cancelBrowserPairing(self, payload: Any) -> Any:
        return self._send("/browser-bridge/pairing/cancel", "POST", dict(payload or {}))

    # ── audio devices (PC-3B) ────────────────────────────────────────────────

    @Slot(result="QVariant")
    def listAudioDevices(self) -> Any:
        from desktop.voice.devices import AudioDeviceService

        svc = AudioDeviceService()
        return {
            "inputs": [{"index": d.index, "name": d.name} for d in svc.list_inputs()],
            "outputs": [{"index": d.index, "name": d.name} for d in svc.list_outputs()],
        }

    # ── native (window / dialogs) ────────────────────────────────────────────

    @Slot()
    def minimizeApp(self) -> None:
        if self._window is not None:
            self._window.showMinimized()

    @Slot()
    def toggleMaximizeApp(self) -> None:
        if self._window is None:
            return
        if self._window.isMaximized():
            self._window.showNormal()
        else:
            self._window.showMaximized()

    @Slot()
    def quitApp(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.instance().quit()

    @Slot(str)
    def setModeFromUI(self, mode: str) -> None:
        return None

    @Slot(str)
    def debugLog(self, msg: str) -> None:
        from desktop.core.debug_log import debugLog as _log

        _log("[react]", msg)

    @Slot(result="QVariant")
    def saveThumbnailAs(self, payload: Any = None) -> Any:
        return {"ok": False}

    @Slot(result="QVariant")
    def addThumbnailReference(self) -> Any:
        return {"ok": False}

    @Slot()
    def companionMenu(self) -> None:
        return None

    @Slot()
    def companionStop(self) -> None:
        if self._controller is not None:
            self._controller.stop_voice()

    # ── voice lifecycle (CR-3) ───────────────────────────────────────────────

    @Slot(result="QVariant")
    def createRealtimeToken(self) -> Any:
        return self._send("/realtime/session", "POST", {"session": {"type": "realtime"}})

    @Slot()
    def startVoice(self) -> None:
        from desktop.core.debug_log import debugLog

        debugLog("[bridge] startVoice -> controller.start_voice")
        if self._controller is not None:
            self._controller.start_voice()

    @Slot()
    def stopVoice(self) -> None:
        from desktop.core.debug_log import debugLog

        debugLog("[bridge] stopVoice")
        if self._controller is not None:
            self._controller.stop_voice()
