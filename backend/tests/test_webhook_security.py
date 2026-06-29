"""Unit tests for webhook signature + replay protection (Phase 1)."""

import hashlib
import hmac

from app import webhook_security as ws


def _sig(body: bytes, secret: bytes, ts: str | None = None) -> str:
    msg = body if ts is None else f"{ts}.".encode() + body
    return "sha256=" + hmac.new(secret, msg, hashlib.sha256).hexdigest()


def test_timestamp_folded_into_signature():
    body = b'{"a":1}'
    # A signature over the body alone must not validate once a timestamp is
    # required, and vice-versa.
    assert ws.verify_signature(body, "k", _sig(body, b"k"))
    assert not ws.verify_signature(body, "k", _sig(body, b"k"), timestamp="123")
    assert ws.verify_signature(body, "k", _sig(body, b"k", "123"), timestamp="123")


def test_timestamp_within_tolerance():
    assert ws.timestamp_within_tolerance("1000", now=1000)
    assert ws.timestamp_within_tolerance("1000", now=1000 + 299)
    assert not ws.timestamp_within_tolerance("1000", now=1000 + 301)
    assert not ws.timestamp_within_tolerance("not-a-number", now=1000)


def test_is_replay_detects_repeats_and_expires():
    ws._seen.clear()
    assert ws.is_replay("sig-a", now=1000) is False
    assert ws.is_replay("sig-a", now=1100) is True  # within window → replay
    # Past the tolerance window the entry is swept and the value is fresh again.
    assert ws.is_replay("sig-a", now=1000 + 301) is False
