#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.AssociatedDevicesScan — the state machine that collects
the Associated Devices table as the second half of a zigpy topology scan.

What is pinned here:

  - one request in flight, coordinator first
  - a paged list is followed to its end before the node is called answered,
    and a page in flight does not spend the node's timeout budget
  - a silent node times out and the scan moves on
  - the whole collection cannot hang: there is a tick ceiling
  - the transmit-queue gate defers without spending a budget
  - a completed collection reports its table; an abandoned one reports None, so
    the scan is filed without the table rather than with half of it
  - a response for a node this collection did not ask is refused, so the
    TopologyV2 scan that issues the same request keeps working

The class is instantiated directly, with a recorded sender in place of
zdp_NWK_address_request: no transport, no zigpy, and nothing that drags the real
Modules.* chain into the session alongside the conftest stubs.
"""

import pytest

from Classes.AssociatedDevicesScan import (NODE_TICK_BUDGET, PHASE_IDLE,
                                           PHASE_RUNNING,
                                           AssociatedDevicesScan)

FFD = ["Full-Function Device", "Main Powered"]


class Log:
    def logging(self, *args, **kwargs):
        pass


class PluginConf:
    def __init__(self, conf=None):
        self.pluginConf = conf or {}


class ControllerLink:
    def __init__(self, load=0):
        self.load = load

    def loadTransmit(self):
        return self.load


# Every NWK_addr_req the collector issues, as (nwkid, ieee, type, index), and
# every per-node outcome reported. One list per test, reset by the `sent`
# fixture and shared with make_scan().
SENT = []
OUTCOMES = []


@pytest.fixture
def sent():
    del SENT[:]
    del OUTCOMES[:]
    return SENT


def record_request(self, nwkid, ieee, u8RequestType="00", u8StartIndex="00"):
    SENT.append((nwkid, ieee, u8RequestType, u8StartIndex))


def make_scan(list_of_devices=None, load=0):
    """A collector plus the list of tables it reported, as [table_or_None].

    The per-node outcome reported alongside each table lands in OUTCOMES, so the
    tests that do not care about it keep reading `reported` as a flat list.
    """
    reported = []

    def completed(associated_devices, outcome):
        reported.append(associated_devices)
        OUTCOMES.append(outcome)
    if list_of_devices is None:
        list_of_devices = {
            "0000": {"IEEE": "00124b0022aabbcc", "LogicalType": "Coordinator"},
            "1111": {"IEEE": "00158d0000000001", "Status": "inDB", "Capability": FFD},
            "2222": {"IEEE": "00158d0000000002", "Status": "inDB", "Capability": FFD},
        }
    scan = AssociatedDevicesScan(
        PluginConf(), ControllerLink(load), list_of_devices, {}, Log(), record_request,
        on_completed=completed,
    )
    return scan, reported


def answer(scan, nwkid, device_list, num_assoc=None, start_index=0):
    """One extended address response, as Decode8040() hands it over."""
    children = len(device_list) // 4
    return scan.response_received(
        nwkid, children if num_assoc is None else num_assoc, start_index, device_list
    )


# ---------------------------------------------------------------------------
# Starting
# ---------------------------------------------------------------------------
def test_start_scan_asks_the_coordinator_first(sent):
    scan, _ = make_scan()
    assert scan.start_scan() is True
    assert scan.phase == PHASE_RUNNING

    scan.continue_scan()
    assert len(sent) == 1
    assert sent[0][0] == "0000"
    assert sent[0][2] == "01", "must be the extended response"
    assert sent[0][3] == "00", "the first page starts at index 0"


def test_start_scan_with_nothing_to_ask(sent):
    """No router and no coordinator record: there is no second half to the scan."""
    scan, reported = make_scan({"2222": {"IEEE": "00158d0000000002", "Status": "inDB",
                                         "Capability": ["Reduced-Function Device"]}})
    assert scan.start_scan() is False
    assert scan.phase == PHASE_IDLE
    assert sent == []
    # Nothing reported: the caller files the scan itself on a False return.
    assert reported == []


def test_only_one_request_is_in_flight(sent):
    scan, _ = make_scan()
    scan.start_scan()
    scan.continue_scan()
    scan.continue_scan()
    assert len(sent) == 1, "a second node must not be asked while the first is pending"


def test_a_node_without_an_ieee_is_skipped(sent):
    """NWK_addr_req asks by IEEE; there is nothing to send without one."""
    scan, reported = make_scan({"0000": {"LogicalType": "Coordinator"}})
    scan.start_scan()
    scan.continue_scan()
    assert sent == []
    assert reported == [{}]


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------
def test_a_node_that_answers_releases_the_next_one(sent):
    scan, _ = make_scan()
    scan.start_scan()
    scan.continue_scan()
    assert answer(scan, "0000", "1a2b3c4d") is True

    scan.continue_scan()
    assert [request[0] for request in sent] == ["0000", "1111"]


def test_the_collected_table_is_reported_on_completion(sent):
    scan, reported = make_scan()
    scan.start_scan()
    for nwkid, children in (("0000", "1a2b3c4d"), ("1111", "5e6f"), ("2222", "")):
        scan.continue_scan()
        answer(scan, nwkid, children)
    scan.continue_scan()

    assert scan.phase == PHASE_IDLE
    assert reported == [{"0000": ["1a2b", "3c4d"], "1111": ["5e6f"], "2222": []}]


def test_a_node_asked_that_reported_no_child_is_in_the_table(sent):
    """An empty list is an answer: that router parents nobody. It is not the
    same as a node that was never asked, which is absent."""
    scan, reported = make_scan()
    scan.start_scan()
    scan.continue_scan()
    answer(scan, "0000", "")
    assert reported == []
    assert scan.collected["0000"] == []


def test_a_duplicate_address_within_one_node_is_recorded_once(sent):
    scan, reported = make_scan()
    scan.start_scan()
    scan.continue_scan()
    answer(scan, "0000", "1a2b1a2b")
    assert scan.collected["0000"] == ["1a2b"]


# ---------------------------------------------------------------------------
# Paging
# ---------------------------------------------------------------------------
def test_a_paged_list_is_followed_to_its_end(sent):
    """Decode8040() asks for the next page itself, so the collector must not
    call the node answered on the first response."""
    scan, reported = make_scan()
    scan.start_scan()
    scan.continue_scan()

    assert answer(scan, "0000", "1a2b3c4d", num_assoc=4, start_index=0) is True
    scan.continue_scan()
    assert len(sent) == 1, "the node is still answering; nothing else may be asked"

    assert answer(scan, "0000", "5e6f7a8b", num_assoc=4, start_index=2) is True
    scan.continue_scan()
    assert [request[0] for request in sent] == ["0000", "1111"]
    assert scan.collected["0000"] == ["1a2b", "3c4d", "5e6f", "7a8b"]


def test_a_page_in_flight_does_not_spend_the_node_budget(sent):
    """A long list must not be cut short by the per-node timeout."""
    scan, _ = make_scan()
    scan.start_scan()
    scan.continue_scan()

    for index in range(0, 4 * NODE_TICK_BUDGET, 2):
        scan.continue_scan()
        answer(scan, "0000", "1a2b3c4d", num_assoc=1000, start_index=index)

    assert scan.nodes["0000"] != "TimedOut"
    assert [request[0] for request in sent] == ["0000"]


# ---------------------------------------------------------------------------
# Timing out
# ---------------------------------------------------------------------------
def test_a_silent_node_times_out_and_the_scan_moves_on(sent):
    scan, _ = make_scan()
    scan.start_scan()
    scan.continue_scan()
    for _ in range(NODE_TICK_BUDGET):
        scan.continue_scan()

    assert scan.nodes["0000"] == "TimedOut"
    assert [request[0] for request in sent] == ["0000", "1111"]


def test_a_node_that_timed_out_is_absent_from_the_table(sent):
    scan, reported = make_scan()
    scan.start_scan()
    for _ in range(3 * (NODE_TICK_BUDGET + 1)):
        scan.continue_scan()

    assert reported == [{}], "every node was silent, so nothing was collected"


def test_the_collection_cannot_hang(sent):
    """A node whose pages never stop must not keep the report pending forever."""
    scan, reported = make_scan()
    scan.start_scan()
    for _ in range(scan.scan_budget + 1):
        scan.continue_scan()
        answer(scan, scan.current or "0000", "1a2b", num_assoc=255, start_index=0)

    assert scan.phase == PHASE_IDLE
    assert reported == [None], "an abandoned collection reports no table at all"


# ---------------------------------------------------------------------------
# Gates
# ---------------------------------------------------------------------------
def test_a_loaded_transmit_queue_defers_without_spending_a_budget(sent):
    scan, _ = make_scan(load=99)
    scan.start_scan()
    for _ in range(10):
        scan.continue_scan()

    assert sent == []
    assert scan.scan_ticks == 0, "a deferred tick is not a tick against the scan"
    assert scan.phase == PHASE_RUNNING


def test_continue_scan_does_nothing_when_idle(sent):
    scan, reported = make_scan()
    scan.continue_scan()
    assert sent == []
    assert reported == []


# ---------------------------------------------------------------------------
# Abandoning
# ---------------------------------------------------------------------------
def test_abort_reports_no_table_rather_than_a_partial_one(sent):
    """Half a table would read as routers with no children, which is a
    different claim from not having collected the table."""
    scan, reported = make_scan()
    scan.start_scan()
    scan.response_received("0000", 1, 0, "1a2b")
    scan.abort("radio is restarting")

    assert scan.phase == PHASE_IDLE
    assert reported == [None]


def test_abort_when_idle_reports_nothing(sent):
    """onStop() and the radio-restart guard call this unconditionally."""
    scan, reported = make_scan()
    scan.abort("plugin is stopping")
    assert reported == []


# ---------------------------------------------------------------------------
# Not ours
# ---------------------------------------------------------------------------
def test_a_response_for_a_node_never_asked_is_refused(sent):
    scan, _ = make_scan()
    scan.start_scan()
    assert scan.response_received("9999", 1, 0, "1a2b") is False
    assert "9999" not in scan.collected


def test_a_response_while_idle_is_refused(sent):
    """The TopologyV2 scan issues the same request and feeds the same decoder."""
    scan, _ = make_scan()
    assert scan.response_received("0000", 1, 0, "1a2b") is False
    assert scan.collected == {}


def test_in_progress_tracks_the_phase(sent):
    scan, _ = make_scan()
    assert scan.in_progress() is False
    scan.start_scan()
    assert scan.in_progress() is True
    scan.abort("done")
    assert scan.in_progress() is False


# ---------------------------------------------------------------------------
# The per-node outcome
# ---------------------------------------------------------------------------
def test_the_outcome_says_which_nodes_answered(sent):
    """The table is flat, so it cannot tell a node that timed out from a router
    that answered "no children". A standalone collection is a whole scan, so
    that distinction has to be recorded somewhere."""
    scan, reported = make_scan()
    scan.start_scan()

    scan.continue_scan()
    answer(scan, "0000", "1a2b")          # answers
    scan.continue_scan()
    answer(scan, "1111", "")              # answers, no children
    for _ in range(NODE_TICK_BUDGET + 1):  # 2222 stays silent
        scan.continue_scan()

    assert reported == [{"0000": ["1a2b"], "1111": []}]
    assert OUTCOMES == [{"0000": "ok", "1111": "ok", "2222": "timeout"}]


def test_the_outcome_vocabulary_is_the_api_one(sent):
    """"ok" / "timeout" as /topology-scan spells them, so the report needs no
    translation on the way out."""
    scan, _ = make_scan()
    scan.start_scan()
    scan.continue_scan()
    answer(scan, "0000", "1a2b")
    for _ in range(2 * (NODE_TICK_BUDGET + 1)):
        scan.continue_scan()

    assert set(OUTCOMES[0].values()) <= {"ok", "timeout"}


def test_an_abandoned_collection_reports_no_outcome_either(sent):
    scan, reported = make_scan()
    scan.start_scan()
    scan.continue_scan()
    answer(scan, "0000", "1a2b")
    scan.abort("radio is restarting")

    assert reported == [None]
    assert OUTCOMES == [None]
