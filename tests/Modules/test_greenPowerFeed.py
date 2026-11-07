#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules/greenPowerFeed.py, the Green Power pairing feed:

  hints      commissioning / window-closed / not-pairing / encrypted / none
  window     opened with its end, expired → closed, disabled
  snapshot   events after a Seq, oldest first, copies; ring of FEED_SIZE
  gp_feed    one feed per plugin
"""

from types import SimpleNamespace

import pytest

from Modules.greenPowerFeed import (HEARD_ENCRYPTED, HEARD_KNOWN,
                                    HEARD_WINDOW_OPEN, GreenPowerFeed, gp_feed,
                                    gp_src_id, heard_hint)

NOW = 1_794_057_000
IEEE = "00000000c220bd02"


@pytest.mark.parametrize("command_id,flags,hint", [
    (0xE0, HEARD_WINDOW_OPEN, "commissioning"),
    (0xE0, 0, "window-closed"),
    (0x21, 0, "not-pairing"),
    (0x21, HEARD_WINDOW_OPEN, "not-pairing"),
    (0x21, HEARD_ENCRYPTED, "encrypted"),
    (0x21, HEARD_KNOWN | HEARD_WINDOW_OPEN, None),
    (0xE0, HEARD_KNOWN | HEARD_WINDOW_OPEN, None),
    (0xE3, HEARD_WINDOW_OPEN, None),
])
def test_hint(command_id, flags, hint):
    assert heard_hint(command_id, flags) == hint


def test_src_id_of_a_synthetic_ieee():
    assert gp_src_id(IEEE) == "0xC220BD02"


def test_window_opened_then_expired():
    feed = GreenPowerFeed()
    feed.window("opened", 240, now=NOW)

    assert feed.snapshot(now=NOW + 10)["Window"] == {"State": "opened", "Until": NOW + 240}
    assert feed.snapshot(now=NOW + 240)["Window"] == {"State": "closed", "Until": None}


def test_window_disabled_has_no_end():
    feed = GreenPowerFeed()
    feed.window("disabled", 240, now=NOW)

    assert feed.snapshot(now=NOW)["Window"] == {"State": "disabled", "Until": None}


def test_snapshot_after_a_seq():
    feed = GreenPowerFeed()
    feed.window("opened", 240, now=NOW)
    feed.heard(IEEE, 0xE0, HEARD_WINDOW_OPEN, None, -64, 212, now=NOW + 3)
    feed.add("commissioned", now=NOW + 3, IEEE=IEEE)

    answer = feed.snapshot(since=1, now=NOW + 4)

    assert answer["Seq"] == 3
    assert [e["Event"] for e in answer["Events"]] == ["heard", "commissioned"]
    assert answer["Events"][0]["Time"] == NOW + 3
    assert feed.snapshot(since=3, now=NOW + 4)["Events"] == []


def test_snapshot_returns_copies():
    feed = GreenPowerFeed()
    feed.add("removed", now=NOW, IEEE=IEEE)

    feed.snapshot()["Events"][0]["IEEE"] = "changed"

    assert feed.snapshot()["Events"][0]["IEEE"] == IEEE


def test_only_the_last_events_are_kept():
    feed = GreenPowerFeed(size=3)
    for _ in range(5):
        feed.add("heard", now=NOW)

    answer = feed.snapshot()
    assert [e["Seq"] for e in answer["Events"]] == [3, 4, 5]
    assert answer["Seq"] == 5


def test_unknown_command_is_shown_in_hex():
    entry = GreenPowerFeed().heard(IEEE, 0x9F, 0, None, -70, 200, now=NOW)

    assert entry["CommandName"] == "0x9f"


def test_one_feed_per_plugin():
    plugin = SimpleNamespace()

    assert gp_feed(plugin) is gp_feed(plugin)
