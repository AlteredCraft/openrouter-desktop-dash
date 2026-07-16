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


def test_missing_keys_yields_no_entries():
    assert keyring.normalize_keys(keys=None) == []


# --- normalize_wifi: config -> a clean list of {"ssid","password"} entries -------------

def test_multi_network_dicts_are_normalized_in_order():
    entries = keyring.normalize_wifi(
        networks=[
            {"ssid": "office-net", "password": "secret1"},
            {"ssid": "cafe-net", "password": "secret2"},
        ]
    )
    assert entries == [
        {"ssid": "office-net", "password": "secret1"},
        {"ssid": "cafe-net", "password": "secret2"},
    ]


def test_password_defaults_to_empty_for_open_networks():
    entries = keyring.normalize_wifi(networks=[{"ssid": "Guest"}])
    assert entries == [{"ssid": "Guest", "password": ""}]


def test_placeholder_and_blank_ssids_are_dropped():
    entries = keyring.normalize_wifi(
        networks=[
            {"ssid": "your-wifi-name"},   # untouched template
            {"ssid": "", "password": "x"},
            {"ssid": "   ", "password": "x"},
            {"ssid": "real-net", "password": "pw"},
        ]
    )
    assert entries == [{"ssid": "real-net", "password": "pw"}]


def test_non_dict_items_are_ignored():
    entries = keyring.normalize_wifi(networks=[None, 42, {"ssid": "only"}])
    assert entries == [{"ssid": "only", "password": ""}]


def test_missing_networks_yields_no_entries():
    assert keyring.normalize_wifi(networks=None) == []


def test_untouched_template_yields_no_keys():
    entries = keyring.normalize_keys(keys=[{"key": "sk-or-v1-...", "name": "warp"}])
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


def test_entries_returns_all_in_order():
    ring = keyring.KeyRing([{"key": "a"}, {"key": "b"}, {"key": "c"}])
    assert ring.entries() == [{"key": "a"}, {"key": "b"}, {"key": "c"}]


def test_entries_does_not_move_the_selection():
    # The account rollup iterates every key; doing so must not shift the on-screen index.
    ring = keyring.KeyRing([{"key": "a"}, {"key": "b"}, {"key": "c"}])
    ring.next()
    before = ring.index
    ring.entries()
    assert ring.index == before
    assert ring.current() == {"key": "b"}


def test_entries_is_a_copy():
    # Mutating the returned list must not corrupt the ring.
    ring = keyring.KeyRing([{"key": "a"}, {"key": "b"}])
    got = ring.entries()
    got.append({"key": "x"})
    assert len(ring) == 2
