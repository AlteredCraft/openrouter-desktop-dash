"""Host-side unit tests for the pure key-ring logic (run with `make test`)."""
import pytest

import keyring


# --- normalize_keys: config -> a clean list of {"key","name"} entries ------------------

def test_multi_key_dicts_are_normalized_in_order():
    entries = keyring.normalize_keys(
        keys=[
            {"key": "sk-or-v1-aaa", "name": "warp"},
            {"key": "sk-or-v1-bbb", "name": "prod"},
        ]
    )
    assert entries == [
        {"key": "sk-or-v1-aaa", "name": "warp"},
        {"key": "sk-or-v1-bbb", "name": "prod"},
    ]


def test_bare_string_keys_get_a_none_name():
    entries = keyring.normalize_keys(keys=["sk-or-v1-aaa", "sk-or-v1-bbb"])
    assert entries == [
        {"key": "sk-or-v1-aaa", "name": None},
        {"key": "sk-or-v1-bbb", "name": None},
    ]


def test_placeholder_and_blank_entries_are_dropped():
    entries = keyring.normalize_keys(
        keys=[
            {"key": "sk-or-v1-...", "name": "template"},  # untouched placeholder
            {"key": "", "name": "empty"},
            {"key": "   ", "name": "whitespace"},
            {"key": "sk-or-v1-real", "name": "real"},
        ]
    )
    assert entries == [{"key": "sk-or-v1-real", "name": "real"}]


def test_empty_name_falls_back_to_none():
    entries = keyring.normalize_keys(keys=[{"key": "sk-or-v1-aaa", "name": ""}])
    assert entries == [{"key": "sk-or-v1-aaa", "name": None}]


def test_non_dict_non_string_items_are_ignored():
    entries = keyring.normalize_keys(keys=[None, 42, {"key": "sk-or-v1-aaa"}])
    assert entries == [{"key": "sk-or-v1-aaa", "name": None}]


def test_falls_back_to_single_key_when_multi_absent():
    entries = keyring.normalize_keys(api_key="sk-or-v1-solo", key_name="warp")
    assert entries == [{"key": "sk-or-v1-solo", "name": "warp"}]


def test_multi_key_takes_precedence_over_single():
    entries = keyring.normalize_keys(
        keys=[{"key": "sk-or-v1-multi", "name": "m"}],
        api_key="sk-or-v1-solo",
        key_name="warp",
    )
    assert entries == [{"key": "sk-or-v1-multi", "name": "m"}]


def test_single_key_used_when_multi_is_all_placeholders():
    entries = keyring.normalize_keys(
        keys=[{"key": "sk-or-v1-...", "name": "template"}],
        api_key="sk-or-v1-solo",
        key_name="warp",
    )
    assert entries == [{"key": "sk-or-v1-solo", "name": "warp"}]


def test_untouched_template_yields_no_keys():
    entries = keyring.normalize_keys(keys=None, api_key="sk-or-v1-...", key_name="")
    assert entries == []


# --- KeyRing: cycle with a current selection -------------------------------------------

def test_empty_ring_raises():
    with pytest.raises(ValueError):
        keyring.KeyRing([])


def test_current_starts_at_first_entry():
    ring = keyring.KeyRing([{"key": "a", "name": "one"}, {"key": "b", "name": "two"}])
    assert ring.current() == {"key": "a", "name": "one"}
    assert ring.index == 0
    assert len(ring) == 2


def test_next_and_prev_wrap_around():
    ring = keyring.KeyRing([{"key": "a"}, {"key": "b"}, {"key": "c"}])
    assert ring.next() == {"key": "b"}
    assert ring.next() == {"key": "c"}
    assert ring.next() == {"key": "a"}   # wraps forward
    assert ring.prev() == {"key": "c"}   # wraps backward
    assert ring.prev() == {"key": "b"}


def test_has_multiple_reflects_count():
    assert keyring.KeyRing([{"key": "a"}]).has_multiple is False
    assert keyring.KeyRing([{"key": "a"}, {"key": "b"}]).has_multiple is True


def test_position_is_one_based_current_of_total():
    ring = keyring.KeyRing([{"key": "a"}, {"key": "b"}, {"key": "c"}])
    assert ring.position() == (1, 3)
    ring.next()
    assert ring.position() == (2, 3)
    ring.next()
    assert ring.position() == (3, 3)


def test_single_key_ring_stays_put():
    ring = keyring.KeyRing([{"key": "a", "name": "solo"}])
    assert ring.next() == {"key": "a", "name": "solo"}
    assert ring.prev() == {"key": "a", "name": "solo"}
    assert ring.position() == (1, 1)
