"""desktop/voice/guards.py — runtime zaštite (OA-1 §7.6–7.8).

Čiste, testabilne zaštite bez I/O:
  - ToolLoopGuard — ograničava broj tool rundi po user turn-u (bez beskonačne
    petlje koju model sam vozi).
  - DuplicateCallGuard — isti call_id se izvršava najviše jednom.
  - GenerationGuard — stale event iz stare sesije se odbacuje.
"""

from __future__ import annotations


class ToolLoopGuard:
    """Ograničava tool rundi unutar jednog user turn-a.

    Novi pravi user turn resetuje budžet; model nastavak (continuation) nakon
    tool rezultata NE resetuje.
    """

    def __init__(self, max_rounds: int = 8) -> None:
        self.max_rounds = max_rounds
        self._rounds = 0

    def on_new_user_turn(self) -> None:
        self._rounds = 0

    def on_tool_round(self) -> None:
        self._rounds += 1

    @property
    def exhausted(self) -> bool:
        return self._rounds >= self.max_rounds

    @property
    def rounds(self) -> int:
        return self._rounds


class DuplicateCallGuard:
    """Sprječava duplo izvršenje istog Realtime call_id (stale/retry događaj)."""

    def __init__(self, max_completed: int = 200) -> None:
        self._inflight: set[str] = set()
        self._completed: set[str] = set()
        self._max_completed = max_completed

    def start(self, call_id: str) -> bool:
        """Registruje inflight; False ako je call_id već viđen (duplikat)."""
        if call_id in self._inflight or call_id in self._completed:
            return False
        self._inflight.add(call_id)
        return True

    def finish(self, call_id: str) -> None:
        self._inflight.discard(call_id)
        self._completed.add(call_id)
        self._trim()

    def _trim(self) -> None:
        while len(self._completed) > self._max_completed:
            self._completed.pop()


class GenerationGuard:
    """Odbacuje async callback-ove iz starih konekcija (stale session)."""

    def __init__(self) -> None:
        self._generation = 0

    def next_generation(self) -> int:
        self._generation += 1
        return self._generation

    @property
    def current(self) -> int:
        return self._generation

    def is_stale(self, generation: int) -> bool:
        return generation != self._generation
