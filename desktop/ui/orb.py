"""desktop/ui/orb.py — companion orb widget u PySide6 (QM-2).

Port `spikes/pyside6_orb_spike.py` u pravu app strukturu: centralni Riki avatar
sa tri pulsirajuća prstena po glasovnom stanju, frameless/transparent/
always-on-top prozor sa drag-om, minimize/restore i multi-monitor odbranom.
Uklonjen spike-only kod (auto-ciklus stanja, keyboard test, screenshot režim) —
stvarni VoiceState dolazi kroz `postavi_voice_state()` iz poller-a (QM-2) i
glasovne integracije (QM-3).

Vjerno prema: electron/core/companionWindow.cjs (window flags), src/components/
RickyOrb.tsx (size="floating" → 84px), src/styles/09-ricky-orb.css (triple-ring
animacija po stanju), assets/Riki-avatar.png (centralna slika).
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import QApplication, QWidget

from desktop.ui.voice_state import map_voice_state_to_orb_state

ORB_SIZE = 84  # RickyOrb "floating" veličina — companion prozor koristi baš nju
AVATAR_PUTANJA = Path(__file__).resolve().parents[2] / "assets" / "Riki-avatar.png"

# inset% iz CSS-a (.ricky-orb__ring--outer/middle/inner) → radijus prstena
# kao razlomak ORB_SIZE/2. Manji inset% = veći prsten (bliže ivici kutije).
RING_INSET = {"outer": 0.01, "middle": 0.08, "inner": 0.18}

# Boja/period/amplituda po stanju i po prstenu — pročitano iz @keyframes u
# 09-ricky-orb.css. period=0 znači "bez pulsa". amp = širenje radijusa (razlomak),
# op = (bazna, dodatna) providnost. Ključevi odgovaraju orb stanjima iz
# desktop/ui/voice_state.py (warning = waiting_confirmation/interrupted).
STANJA: dict[str, dict] = {
    "idle": {
        "naziv": "Idle",
        "outer": dict(boja=(62, 166, 255), period=3800, amp=0.035, op=(0.55, 0.30)),
        "middle": dict(boja=(157, 220, 255), period=4400, amp=0.035, op=(0.55, 0.30), obrni=True),
        "inner": None,
        "avatar_period": 3200,
        "avatar_amp": 0.015,
        "avatar_glow": (31, 134, 255),
    },
    "listening": {
        "naziv": "Sluša",
        "outer": dict(boja=(91, 209, 255), period=1250, amp=0.10, op=(0.55, 0.45), organski=True),
        "middle": dict(boja=(126, 246, 255), period=950, amp=0.10, op=(0.55, 0.45), organski=True),
        "inner": None,
        "avatar_period": 820,
        "avatar_amp": 0.035,
        "avatar_glow": (0, 183, 255),
    },
    "thinking": {
        "naziv": "Razmišlja",
        "outer": dict(boja=(116, 104, 255), period=3200, amp=0.045, op=(0.48, 0.34), rotira=True),
        "middle": dict(boja=(62, 166, 255), period=2400, amp=0.06, op=(0.45, 0.27)),
        "inner": None,
        "avatar_period": 2800,
        "avatar_amp": 0.015,
        "avatar_glow": (31, 134, 255),
    },
    "speaking": {
        "naziv": "Govori",
        "outer": dict(boja=(91, 209, 255), period=900, amp=0.12, op=(0.48, 0.47), organski=True),
        "middle": dict(boja=(159, 122, 255), period=720, amp=0.12, op=(0.48, 0.47), organski=True),
        "inner": dict(boja=(126, 246, 255), period=550, amp=0.12, op=(0.45, 0.45), organski=True),
        "avatar_period": 820,
        "avatar_amp": 0.035,
        "avatar_glow": (0, 213, 255),
    },
    "warning": {
        "naziv": "Čeka potvrdu",
        "outer": dict(boja=(245, 165, 36), period=1800, amp=0.04, op=(0.58, 0.32)),
        "middle": None,
        "inner": None,
        "avatar_period": 3200,
        "avatar_amp": 0.015,
        "avatar_glow": (245, 165, 36),
    },
    "error": {
        "naziv": "Greška",
        "outer": dict(boja=(239, 68, 68), period=550, amp=0.045, op=(0.75, 0.20), konacno=3),
        "middle": None,
        "inner": None,
        "avatar_period": 0,
        "avatar_amp": 0.0,
        "avatar_glow": (239, 68, 68),
    },
    "muted": {
        "naziv": "Isključen mikrofon",
        "outer": dict(boja=(141, 154, 170), period=0, amp=0.0, op=(0.22, 0.0)),
        "middle": None,
        "inner": None,
        "avatar_period": 0,
        "avatar_amp": 0.0,
        "avatar_glow": None,
        "zasicenje": 0.35,  # grayscale(.45) približno
    },
}


def _puls(elapsed_ms: int, period_ms: int, obrni: bool = False) -> float:
    """0..1 ease-in-out oscilacija — Python ekvivalent CSS keyframes 0%→50%→100%."""
    if period_ms <= 0:
        return 0.0
    faza = (elapsed_ms % period_ms) / period_ms
    if obrni:
        faza = 1.0 - faza
    return (math.sin(faza * 2 * math.pi - math.pi / 2) + 1) / 2


def _puls_organski(elapsed_ms: int, base_period_ms: int, faza_pomak: float = 0.0) -> float:
    """0..1, kombinuje tri sinusoide različitih frekvencija umjesto jedne.

    Korisnikov feedback (2026-07-20): jednostavan _puls() djeluje mehanički.
    Ovo je jeftina aproksimacija slojevitog, audio-reaktivnog pokreta bez stvarne
    audio amplitude — tri sloja različite frekvencije/težine, normalizovani.
    """
    if base_period_ms <= 0:
        return 0.0
    ukupno, tezina_uk = 0.0, 0.0
    for frek, tezina in ((1.0, 0.55), (1.9, 0.30), (3.3, 0.15)):
        perioda = base_period_ms / frek
        faza = ((elapsed_ms + faza_pomak * base_period_ms) % perioda) / perioda
        ukupno += tezina * math.sin(faza * 2 * math.pi)
        tezina_uk += tezina
    return max(0.0, min(1.0, (ukupno / tezina_uk + 1) / 2))


class RickyOrbWidget(QWidget):
    """Avatar + tri nezavisna pulsirajuća prstena — 1:1 prema RickyOrb.tsx."""

    def __init__(self) -> None:
        super().__init__()
        self.stanje = "idle"
        self.stanje_od_ms = 0
        self.mrtva_tocka = None  # za drag
        self.zakljucano = False  # position lock (kontekst meni)

        # Isto kao companionWindow.cjs: frame:false, transparent:true,
        # alwaysOnTop:true (floating), skipTaskbar:true, hasShadow:false.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool  # najbliže skipTaskbar na Windowsu
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._puna_velicina = (144, 160)  # ORB_WIN_W x ORB_WIN_H
        self._mini_velicina = (28, 28)
        self.minimizirano = False
        self.resize(*self._puna_velicina)

        # Avatar učitan i predizrezan u krug jednom (perf) — izvor je kvadratna
        # slika bez alfa kanala, isto kao CSS border-radius:999px na <img>.
        self._avatar = self._ucitaj_avatar_kao_krug()

        self._tik = QTimer(self)
        self._tik.timeout.connect(self._otkucaj)
        self._tik.start(16)  # ~60fps
        self._elapsed_ms = 0

        self._prati_ekran = None  # postavlja se u showEvent, kad handle postoji
        self._audio_nivo = 0.0  # stvarna amplituda 0..1 (OA-3, audio-reactive)

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        # BUG 2026-07-20 (korisnik prijavio): providnost puca kad se orb prevuče
        # na drugi monitor — poznat Qt/Windows problem kod prelaska preko
        # monitora sa drugačijim DPI scaling-om. Odbrambena popravka: na
        # promjenu ekrana ponovo primijeni translucent atribut + repaint.
        handle = self.windowHandle()
        if handle is not None and self._prati_ekran is None:
            self._prati_ekran = handle
            handle.screenChanged.connect(self._na_promjenu_ekrana)

    def _na_promjenu_ekrana(self, novi_ekran) -> None:
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.hide()
        self.show()
        self.update()

    def set_locked(self, zakljucano: bool) -> None:
        self.zakljucano = zakljucano

    def is_locked(self) -> bool:
        return self.zakljucano

    def toggle_minimize(self) -> None:
        self.minimizirano = not self.minimizirano
        vel = self._mini_velicina if self.minimizirano else self._puna_velicina
        # Zadrži poziciju centra, ne gornji-lijevi ugao, da ne "skoči".
        stari_centar = self.geometry().center()
        self.resize(*vel)
        novi = self.geometry()
        novi.moveCenter(stari_centar)
        self.move(novi.topLeft())
        self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_minimize()

    def _ucitaj_avatar_kao_krug(self) -> QPixmap | None:
        if not AVATAR_PUTANJA.exists():
            return None
        izvor = QPixmap(str(AVATAR_PUTANJA))
        dim = int(ORB_SIZE * 1.12)  # CSS: .ricky-orb-img je 112% kontejnera
        skaliran = izvor.scaled(
            dim, dim, Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        # centriran crop na kvadrat dim×dim (object-fit: cover, position 53% Y)
        x = (skaliran.width() - dim) // 2
        y = int((skaliran.height() - dim) * 0.53)
        skaliran = skaliran.copy(x, max(0, y), dim, dim)

        krug = QPixmap(dim, dim)
        krug.fill(Qt.GlobalColor.transparent)
        p = QPainter(krug)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        putanja = QPainterPath()
        putanja.addEllipse(0, 0, dim, dim)
        p.setClipPath(putanja)
        p.drawPixmap(0, 0, skaliran)
        p.end()
        return krug

    def postavi_stanje(self, stanje: str) -> None:
        """Postavi vizuelno orb stanje (7 vrijednosti iz voice_state.ORB_STATES)."""
        if stanje in STANJA and stanje != self.stanje:
            self.stanje = stanje
            self.stanje_od_ms = self._elapsed_ms
            self.update()

    def postavi_voice_state(self, voice_state: str) -> None:
        """Prihvati kanonski VoiceState (9 vrijednosti) i mapiraj u vizuelno stanje."""
        self.postavi_stanje(map_voice_state_to_orb_state(voice_state))

    def postavi_audio_nivo(self, nivo: float) -> None:
        """Stvarna amplituda 0..1 iz audio streama — orb "čuje" korisnika (OA-3)."""
        self._audio_nivo = max(0.0, min(1.0, float(nivo)))
        if self.stanje in ("listening", "speaking"):
            self.update()

    def _otkucaj(self) -> None:
        self._elapsed_ms += 16
        self.update()

    # ── Crtanje — ekvivalent CSS-a, ručno, jer Qt nema radial-gradient/keyframes ─

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self.minimizirano:
            self._crtaj_minimiziranu_tacku(p)
            p.end()
            return

        cx, cy = self.width() / 2, self.height() / 2 - 8
        info = STANJA[self.stanje]
        proteklo_u_stanju = self._elapsed_ms - self.stanje_od_ms
        baza_r = ORB_SIZE / 2

        # REDOSLIJED JE BITAN: prvo avatar, pa prstenovi preko njega sa
        # CompositionMode_Screen (CSS mix-blend-mode:screen, prstenovi IZNAD).
        self._crtaj_avatar(p, cx, cy, baza_r, info)

        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Screen)
        for ime_prstena in ("outer", "middle", "inner"):
            konf = info.get(ime_prstena)
            if not konf:
                continue
            self._crtaj_prsten(p, cx, cy, baza_r, ime_prstena, konf, proteklo_u_stanju)
        p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)

        p.end()

    def _crtaj_prsten(self, p: QPainter, cx, cy, baza_r, ime, konf, proteklo_ms) -> None:
        r, g, b = konf["boja"]
        period = konf["period"]
        obrni = konf.get("obrni", False)
        konacno = konf.get("konacno")

        if konacno and period:
            if proteklo_ms >= konacno * period:
                puls = 0.0
            else:
                puls = _puls(proteklo_ms, period, obrni)
        elif konf.get("organski") and period:
            faza_pomak = 0.33 if ime == "middle" else (0.66 if ime == "inner" else 0.0)
            sinteticki = _puls_organski(self._elapsed_ms, period, faza_pomak)
            # OA-3: stvarna audio amplituda nadjačava sintetički puls — orb
            # reaguje na pravi glas, a organski puls ostaje bazni "život" u tišini.
            puls = max(sinteticki, self._audio_nivo)
        else:
            puls = _puls(self._elapsed_ms, period, obrni) if period else 0.5

        inset = RING_INSET[ime]
        radijus = baza_r * (1 - inset) * (1 + konf["amp"] * puls)
        op_baza, op_dod = konf["op"]
        opacity = op_baza + op_dod * puls

        rotacija = 6 * puls if konf.get("rotira") else 0.0

        p.save()
        if rotacija:
            p.translate(cx, cy)
            p.rotate(rotacija)
            p.translate(-cx, -cy)

        pen = QPen(QColor(r, g, b, int(255 * opacity)))
        pen.setWidthF(1.2)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radijus, radijus)

        glow = QRadialGradient(QPointF(cx, cy), radijus + 5)
        glow.setColorAt(max(0.0, (radijus - 5) / (radijus + 5)), QColor(r, g, b, 0))
        glow.setColorAt(radijus / (radijus + 5), QColor(r, g, b, int(90 * opacity)))
        glow.setColorAt(1.0, QColor(r, g, b, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), radijus + 5, radijus + 5)
        p.restore()

    def _crtaj_avatar(self, p: QPainter, cx, cy, baza_r, info) -> None:
        puls = _puls(self._elapsed_ms, info["avatar_period"]) if info["avatar_period"] else 0.5
        skala = 1.0 + info["avatar_amp"] * (puls - 0.5) * 2 if info["avatar_period"] else 1.0

        # Stvaran poluprečnik NACRTANOG avatara — glow MORA početi tačno na ovoj
        # ivici, inače ga neprozirna slika prekrije i boja se nikad ne vidi.
        avatar_r = (self._avatar.width() * skala / 2) if self._avatar else baza_r * 0.56

        if info.get("avatar_glow"):
            r, g, b = info["avatar_glow"]
            glow_r = avatar_r * 1.45
            edge = avatar_r / glow_r
            grad = QRadialGradient(QPointF(cx, cy), glow_r)
            grad.setColorAt(max(0.0, edge - 0.08), QColor(r, g, b, 0))
            grad.setColorAt(min(0.99, edge + 0.12), QColor(r, g, b, int(160 * (0.6 + 0.4 * puls))))
            grad.setColorAt(1.0, QColor(r, g, b, 0))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(grad)
            p.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        if self._avatar is None:
            p.setBrush(QColor(20, 30, 50))
            p.setPen(QPen(QColor(80, 120, 180), 1))
            p.drawEllipse(QPointF(cx, cy), baza_r * skala, baza_r * skala)
            return

        dim = self._avatar.width() * skala
        opacity = info.get("zasicenje", 1.0) if self.stanje == "muted" else 1.0
        p.setOpacity(opacity)
        p.drawPixmap(
            QRectF(cx - dim / 2, cy - dim / 2, dim, dim),
            self._avatar,
            QRectF(0, 0, self._avatar.width(), self._avatar.height()),
        )
        p.setOpacity(1.0)

    def _crtaj_minimiziranu_tacku(self, p: QPainter) -> None:
        info = STANJA[self.stanje]
        boja = info.get("avatar_glow") or (100, 110, 130)
        r, g, b = boja
        cx, cy = self.width() / 2, self.height() / 2
        rad = min(self.width(), self.height()) / 2 - 2

        puls = _puls(self._elapsed_ms, info["avatar_period"]) if info["avatar_period"] else 0.5
        opacity = 0.75 + 0.25 * puls if info["avatar_period"] else 0.85

        glow = QRadialGradient(QPointF(cx, cy), rad * 1.6)
        glow.setColorAt(0.4, QColor(r, g, b, int(200 * opacity)))
        glow.setColorAt(1.0, QColor(r, g, b, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(glow)
        p.drawEllipse(QPointF(cx, cy), rad * 1.6, rad * 1.6)

        p.setBrush(QColor(r, g, b, 230))
        p.drawEllipse(QPointF(cx, cy), rad * 0.55, rad * 0.55)

    # ── Drag cijelim licem — isto kao -webkit-app-region: drag ───────────────

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() == Qt.MouseButton.LeftButton and not self.zakljucano:
            self.mrtva_tocka = event.globalPosition().toPoint() - self.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if self.mrtva_tocka is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self.mrtva_tocka)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        self.mrtva_tocka = None


def _instance() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app
