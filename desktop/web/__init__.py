"""desktop/web/ — PySide6 + QWebEngineView + QWebChannel host (CR-1/CR-2).

React ostaje presentation layer; ovaj paket ga ugrađuje u native Qt shell i
izlaže allowlisted `window.ricky` bridge preko QWebChannel-a (zamjena za
Electron preload/IPC).
"""
