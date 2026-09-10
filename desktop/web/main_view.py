"""desktop/web/main_view.py — QWebEngineView host za React GUI (CR-1).

QMainWindow koji učitava postojeći React production bundle i izlaže
`window.ricky` bridge preko QWebChannel-a. Zamjenjuje Electron BrowserWindow +
preload.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QUrl
from PySide6.QtWebChannel import QWebChannel
from PySide6.QtWebEngineCore import QWebEngineScript
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import QMainWindow

from desktop.web.bridge import RickyWebBridge


def _inject_qwebchannel(view: QWebEngineView) -> None:
    """Injektuje qwebchannel.js kroz QWebEngineScript (CSP blokira qrc script src)."""
    handle = QFile(":/qtwebchannel/qwebchannel.js")
    if not handle.open(QIODevice.OpenModeFlag.ReadOnly):
        return
    source = bytes(handle.readAll()).decode("utf-8")
    handle.close()
    script = QWebEngineScript()
    script.setName("qwebchannel")
    script.setSourceCode(source)
    script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
    script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
    script.setRunsOnSubFrames(False)
    view.page().scripts().insert(script)


class MainWebWindow(QMainWindow):
    def __init__(self, controller, parent=None) -> None:
        super().__init__(parent)
        self._controller = controller
        self.setWindowTitle("Ricky")
        self.resize(1280, 820)

        self.view = QWebEngineView(self)
        self.setCentralWidget(self.view)

        self.channel = QWebChannel(self)
        self.bridge = RickyWebBridge(
            controller.backend.client, window=self, controller=controller
        )
        self.channel.registerObject("ricky", self.bridge)
        self.view.page().setWebChannel(self.channel)
        _inject_qwebchannel(self.view)

        from desktop.core.debug_log import debugLog
        from PySide6.QtCore import QTimer

        def _on_load(ok: bool) -> None:
            debugLog("[web] react loadFinished:", ok)

            def _check() -> None:
                self.view.page().runJavaScript(
                    "JSON.stringify({ricky: typeof window.ricky,"
                    " getSettings: typeof (window.ricky && window.ricky.getSettings),"
                    " rootChildren: (document.getElementById('root')||{}).childElementCount})",
                    lambda result: debugLog("[web] js:", result),
                )

            QTimer.singleShot(5000, _check)

        self.view.loadFinished.connect(_on_load)

        self._wire_signals()
        self._load_react()

    def _wire_signals(self) -> None:
        bus = self._controller.bus
        bridge = self.bridge
        bus.state_changed.connect(bridge.voiceStateChanged)
        bus.audio_input_level.connect(bridge.voiceInputLevelChanged)
        bus.audio_output_level.connect(bridge.voiceOutputLevelChanged)
        bus.connected_changed.connect(bridge.voiceConnectedChanged)
        bus.user_transcript.connect(bridge.voiceUserTranscript)
        bus.assistant_transcript.connect(bridge.voiceAssistantTranscript)
        bus.error.connect(bridge.voiceError)
        self._controller.confirmation_required.connect(bridge.confirmationRequired)

    def _load_react(self) -> None:
        dist = Path(__file__).resolve().parents[2] / "dist" / "index.html"
        if dist.exists():
            self.view.load(QUrl.fromLocalFile(str(dist)))
        else:
            self.view.setHtml(
                "<html><body style='background:#111;color:#eee;font-family:sans-serif'>"
                "<h2>React bundle nije buildovan</h2>"
                "<p>Pokreni: <code>npm run build</code></p></body></html>"
            )
