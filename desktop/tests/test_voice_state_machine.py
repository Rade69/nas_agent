"""Testovi za reconnect state mašinu i politiku (OA-1)."""

from desktop.voice.state import (
    ErrorClass,
    ReconnectPolicy,
    backoff_seconds,
    classify_error,
    should_reconnect,
)


def test_classify_network_errors():
    assert classify_error("ConnectionClosedError") == ErrorClass.NETWORK
    assert classify_error("ConnectionError") == ErrorClass.NETWORK
    assert classify_error("ConnectError") == ErrorClass.NETWORK
    assert classify_error("getaddrinfo failed") == ErrorClass.NETWORK
    assert classify_error("Errno 11001") == ErrorClass.NETWORK


def test_classify_auth_errors():
    assert classify_error("InvalidStatus") == ErrorClass.AUTH
    assert classify_error("401 Unauthorized") == ErrorClass.AUTH
    assert classify_error("invalid api key") == ErrorClass.AUTH


def test_classify_rate_limit():
    assert classify_error("429 rate limit") == ErrorClass.RATE_LIMIT
    assert classify_error("ratelimit exceeded") == ErrorClass.RATE_LIMIT


def test_classify_manual_disconnect():
    assert classify_error("whatever", manual_disconnect=True) == ErrorClass.MANUAL_DISCONNECT


def test_backoff_sequence_capped():
    assert backoff_seconds(1) == 2.0
    assert backoff_seconds(2) == 4.0
    assert backoff_seconds(3) == 8.0
    assert backoff_seconds(4) == 8.0  # capped
    assert backoff_seconds(10) == 8.0


def test_should_reconnect_only_network_and_rate_limit():
    assert should_reconnect(ErrorClass.NETWORK, 0) is True
    assert should_reconnect(ErrorClass.RATE_LIMIT, 0) is True
    assert should_reconnect(ErrorClass.AUTH, 0) is False
    assert should_reconnect(ErrorClass.FATAL, 0) is False
    assert should_reconnect(ErrorClass.MANUAL_DISCONNECT, 0) is False


def test_should_reconnect_bounded():
    assert should_reconnect(ErrorClass.NETWORK, 2) is True  # attempt 3
    assert should_reconnect(ErrorClass.NETWORK, 3) is False  # premašio max


def test_reconnect_policy_network_then_bounded():
    policy = ReconnectPolicy(max_attempts=3)
    assert policy.on_disconnect("ConnectionClosedError") == (True, 2.0)
    assert policy.on_disconnect("ConnectionClosedError") == (True, 4.0)
    assert policy.on_disconnect("ConnectionClosedError") == (True, 8.0)
    # četvrti pokušaj prelazi max_attempts → bez reconnecta
    assert policy.on_disconnect("ConnectionClosedError") == (False, 0.0)


def test_reconnect_policy_auth_not_retried():
    policy = ReconnectPolicy()
    assert policy.on_disconnect("InvalidStatus") == (False, 0.0)


def test_reconnect_policy_reset():
    policy = ReconnectPolicy(max_attempts=3)
    policy.on_disconnect("ConnectionClosedError")
    policy.on_disconnect("ConnectionClosedError")
    policy.reset()
    assert policy.on_disconnect("ConnectionClosedError") == (True, 2.0)
