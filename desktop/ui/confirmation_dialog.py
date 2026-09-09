"""desktop/ui/confirmation_dialog.py — Qt confirmation dijalog (QM-3).

Port src/components/ConfirmationDialog.tsx: prikazuje akciju, rizik i payload,
sa "Odobri" dugmetom koje je disable-ovano tokom armed delay-a (FAZA S-4/S30)
da slučajni dupli-klik/makro ne prođe kroz high-risk potvrdu. Escape = odbijanje
(nikad odobravanje). Emituje `approved`/`rejected` signale sa confirmation_id.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

ARM_DELAY_MS = 250

# Best-effort lokalizacija (sr-Latn default) — isti nivo kao de/es/fr disclaimer.
RISK_LABELS = {
    "low": "Nizak rizik",
    "medium": "Srednji rizik",
    "high": "Visok rizik",
    "critical": "Kritično",
}

# Payload polja sa poznatim labelama (port PAYLOAD_FIELD_KEYS iz React verzije).
FIELD_LABELS = {
    "to": "Primaoc",
    "recipient": "Primaoc",
    "email": "Primaoc",
    "subject": "Naslov",
    "title": "Naslov",
    "text": "Sadržaj",
    "body": "Sadržaj",
    "appName": "Aplikacija",
}
KNOWN_FIELDS = set(FIELD_LABELS)


class ConfirmationDialog(QDialog):
    approved = Signal(str)  # confirmation_id
    rejected = Signal(str)  # confirmation_id

    def __init__(
        self,
        action_name: str,
        risk_level: str,
        payload: dict[str, Any],
        confirmation_id: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._confirmation_id = confirmation_id
        self._armed = False

        self.setWindowTitle("Potvrda")
        self.setModal(True)
        self.setMinimumWidth(360)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Tražena je potvrda za sljedeću akciju:"))

        self._action_label = QLabel(action_name)
        self._action_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(self._action_label)

        risk = RISK_LABELS.get(risk_level, risk_level)
        self._risk_label = QLabel(f"Rizik: {risk}")
        layout.addWidget(self._risk_label)

        recognized = {k: v for k, v in payload.items() if k in KNOWN_FIELDS}
        for key, value in recognized.items():
            layout.addWidget(QLabel(f"{FIELD_LABELS[key]}: {value}"))

        unknown = {k: v for k, v in payload.items() if k not in KNOWN_FIELDS}
        if unknown:
            import json

            detail = QLabel(f"Detalji:\n{json.dumps(unknown, ensure_ascii=False, indent=2)}")
            detail.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            layout.addWidget(detail)

        buttons = QHBoxLayout()
        self._reject_btn = QPushButton("Odbij")
        self._reject_btn.clicked.connect(self._on_reject)
        self._approve_btn = QPushButton("Odobri")
        self._approve_btn.setEnabled(False)  # armed delay (S-4/S30)
        self._approve_btn.clicked.connect(self._on_approve)
        buttons.addWidget(self._reject_btn)
        buttons.addWidget(self._approve_btn)
        layout.addLayout(buttons)

        QTimer.singleShot(ARM_DELAY_MS, self._arm)

    @property
    def armed(self) -> bool:
        return self._armed

    def _arm(self) -> None:
        self._armed = True
        self._approve_btn.setEnabled(True)

    def _on_approve(self) -> None:
        if self._armed:
            self.approved.emit(self._confirmation_id)
            self.accept()

    def _on_reject(self) -> None:
        self.rejected.emit(self._confirmation_id)
        self.reject()

    def keyPressEvent(self, event) -> None:  # noqa: N802
        if event.key() == Qt.Key.Key_Escape:
            self._on_reject()  # Escape = odbijanje, NIKAD odobravanje
        else:
            super().keyPressEvent(event)
