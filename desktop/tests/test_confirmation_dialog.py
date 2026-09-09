"""Testovi za ConfirmationDialog (QM-3): armed delay, approve/reject, escape."""

import time

from PySide6.QtCore import Qt

from desktop.ui.confirmation_dialog import ARM_DELAY_MS, ConfirmationDialog


def test_approve_disabled_until_armed(qapp):
    dlg = ConfirmationDialog("test_tool", "high", {}, "conf-1")
    assert dlg.armed is False
    assert dlg._approve_btn.isEnabled() is False

    time.sleep(ARM_DELAY_MS / 1000 + 0.1)
    qapp.processEvents()

    assert dlg.armed is True
    assert dlg._approve_btn.isEnabled() is True


def test_approve_emits_confirmation_id(qapp):
    dlg = ConfirmationDialog("test_tool", "high", {}, "conf-1")
    time.sleep(ARM_DELAY_MS / 1000 + 0.1)
    qapp.processEvents()

    emitted = []
    dlg.approved.connect(emitted.append)
    dlg._approve_btn.click()
    assert emitted == ["conf-1"]


def test_reject_emits_confirmation_id(qapp):
    dlg = ConfirmationDialog("test_tool", "high", {}, "conf-1")
    emitted = []
    dlg.rejected.connect(emitted.append)
    dlg._reject_btn.click()
    assert emitted == ["conf-1"]


def test_escape_rejects_not_approves(qapp):
    dlg = ConfirmationDialog("test_tool", "high", {}, "conf-1")
    rejected = []
    approved = []
    dlg.rejected.connect(rejected.append)
    dlg.approved.connect(approved.append)

    dlg._on_reject()  # isti put kao Escape u keyPressEvent

    assert rejected == ["conf-1"]
    assert approved == []
