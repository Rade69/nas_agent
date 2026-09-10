"""Testovi za runtime guards (OA-1 §7.6–7.8)."""

from desktop.voice.guards import DuplicateCallGuard, GenerationGuard, ToolLoopGuard


# --- ToolLoopGuard ---

def test_tool_loop_exhausts_budget():
    guard = ToolLoopGuard(max_rounds=3)
    assert guard.exhausted is False
    guard.on_tool_round()
    guard.on_tool_round()
    guard.on_tool_round()
    assert guard.exhausted is True


def test_tool_loop_new_user_turn_resets():
    guard = ToolLoopGuard(max_rounds=3)
    guard.on_tool_round()
    guard.on_tool_round()
    guard.on_new_user_turn()
    assert guard.exhausted is False
    assert guard.rounds == 0


# --- DuplicateCallGuard ---

def test_duplicate_call_guard_blocks_inflight_and_completed():
    guard = DuplicateCallGuard()
    assert guard.start("abc") is True
    assert guard.start("abc") is False  # već inflight
    guard.finish("abc")
    assert guard.start("abc") is False  # već completed


def test_duplicate_call_guard_allows_distinct_ids():
    guard = DuplicateCallGuard()
    assert guard.start("a") is True
    assert guard.start("b") is True


# --- GenerationGuard ---

def test_generation_guard_stale():
    guard = GenerationGuard()
    gen1 = guard.next_generation()
    assert guard.is_stale(gen1) is False
    guard.next_generation()
    assert guard.is_stale(gen1) is True
