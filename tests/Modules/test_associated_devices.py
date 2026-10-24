#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Modules.associated_devices — which nodes an Associated Devices
collection asks, and how it reads a paged extended address response.

The module is deliberately free of plugin dependencies so these run in the
normal pytest session, with no stub and no subprocess.
"""

from Modules.associated_devices import (DEPARTED_STATUSES,
                                        EXTENDED_REQUEST_TYPE, is_last_page,
                                        node_can_have_children, nodes_to_scan,
                                        notify_associated_devices_scan,
                                        split_device_list)

# ---------------------------------------------------------------------------
# node_can_have_children
# ---------------------------------------------------------------------------
FFD = ["Full-Function Device", "Main Powered", "Receiver during Idle"]
RFD = ["Reduced-Function Device", "Standard security"]


def test_coordinator_is_always_asked():
    """The coordinator record has no Capability and no Status, and its children
    are the ones no router can report."""
    assert node_can_have_children("0000", {"LogicalType": "Coordinator"}) is True
    assert node_can_have_children("0000", {}) is True
    assert node_can_have_children("0000", None) is True


def test_router_with_full_function_capability():
    assert node_can_have_children("1234", {"Status": "inDB", "Capability": FFD}) is True


def test_reduced_function_capability_is_believed_over_logical_type():
    """A Livolo (MacCapa 0x80) or an Aqara Opple (0x84) decodes to
    reduced-function while LogicalType may well say Router -- which is why
    NetworkMap.is_a_router() had to exclude those models by name."""
    device = {"Status": "inDB", "Capability": RFD, "LogicalType": "Router", "DeviceType": "FFD"}
    assert node_can_have_children("1234", device) is False


def test_logical_type_used_when_nothing_was_announced():
    assert node_can_have_children("1234", {"Status": "inDB", "LogicalType": "Router"}) is True
    assert node_can_have_children("1234", {"Status": "inDB", "LogicalType": "End Device"}) is False


def test_device_type_ffd_used_when_nothing_was_announced():
    assert node_can_have_children("1234", {"Status": "inDB", "DeviceType": "FFD"}) is True


def test_mac_capa_bit_used_as_last_resort():
    # 0x8e: full-function, main powered, receiver on idle
    assert node_can_have_children("1234", {"Status": "inDB", "MacCapa": "8e"}) is True
    # 0x80: Livolo, reduced-function
    assert node_can_have_children("1234", {"Status": "inDB", "MacCapa": "80"}) is False


def test_mac_capa_that_cannot_be_read_is_not_a_router():
    for mac_capa in ("", "  ", "zz", None, [], {}):
        assert node_can_have_children("1234", {"Status": "inDB", "MacCapa": mac_capa}) is False


def test_a_device_that_left_is_never_asked():
    """Asking one spends a whole per-node timeout budget for nothing."""
    for status in DEPARTED_STATUSES:
        assert node_can_have_children("1234", {"Status": status, "Capability": FFD}) is False


def test_a_device_still_pairing_is_not_asked():
    assert node_can_have_children("1234", {"Status": "004d", "Capability": FFD}) is False


def test_a_non_mapping_record_is_not_asked():
    """ListOfDevices entries are not plain dicts, and a corrupted one is a str."""
    assert node_can_have_children("1234", "corrupted") is False
    assert node_can_have_children("1234", None) is False


# ---------------------------------------------------------------------------
# nodes_to_scan
# ---------------------------------------------------------------------------
def test_nodes_to_scan_puts_the_coordinator_first():
    list_of_devices = {
        "ffff": {"Status": "inDB", "Capability": FFD},
        "0000": {"LogicalType": "Coordinator"},
        "1111": {"Status": "inDB", "Capability": FFD},
        "2222": {"Status": "inDB", "Capability": RFD},
    }
    assert nodes_to_scan(list_of_devices) == ["0000", "1111", "ffff"]


def test_nodes_to_scan_without_a_coordinator_record():
    assert nodes_to_scan({"1111": {"Status": "inDB", "Capability": FFD}}) == ["1111"]


def test_nodes_to_scan_with_nothing_to_ask():
    assert nodes_to_scan({"2222": {"Status": "inDB", "Capability": RFD}}) == []


# ---------------------------------------------------------------------------
# is_last_page
# ---------------------------------------------------------------------------
def test_a_single_page_that_covers_the_count_is_the_last():
    assert is_last_page(3, 0, 3) is True


def test_a_short_first_page_is_not_the_last():
    assert is_last_page(10, 0, 4) is False


def test_the_page_that_reaches_the_count_is_the_last():
    assert is_last_page(10, 6, 4) is True


def test_a_node_reporting_more_than_it_sends_does_not_page_forever():
    """`>=` rather than `==`: a node whose count never matches what it sends
    would otherwise be asked for the next page indefinitely."""
    assert is_last_page(10, 8, 4) is True


def test_an_empty_list_for_a_node_with_no_children_is_the_last_page():
    assert is_last_page(0, 0, 0) is True


def test_a_response_with_no_counters_is_treated_as_complete():
    assert is_last_page(None, None, 0) is True
    assert is_last_page("3", 0, 1) is True


# ---------------------------------------------------------------------------
# split_device_list
# ---------------------------------------------------------------------------
def test_split_device_list():
    assert split_device_list("1a2b3c4d") == ["1a2b", "3c4d"]


def test_split_device_list_drops_a_trailing_fragment():
    """Half an address is not a node."""
    assert split_device_list("1a2b3c") == ["1a2b"]
    assert split_device_list("1a2") == []


def test_split_device_list_of_an_empty_payload():
    assert split_device_list("") == []
    assert split_device_list(None) == []


# ---------------------------------------------------------------------------
# notify_associated_devices_scan
# ---------------------------------------------------------------------------
class Plugin:
    pass


class Collector:
    def __init__(self, answer):
        self.answer = answer
        self.calls = []

    def response_received(self, nwkid, num_assoc_devices, start_index, device_list):
        self.calls.append((nwkid, num_assoc_devices, start_index, device_list))
        return self.answer


def test_notify_without_a_collector_is_a_no_op():
    """Every extended address response goes through here, including the ones a
    TopologyV2 scan asked for while no collection is running."""
    assert notify_associated_devices_scan(Plugin(), "0000", 1, 0, "1a2b") is False


def test_notify_hands_the_page_over():
    plugin = Plugin()
    plugin.associated_devices_scan = Collector(True)
    assert notify_associated_devices_scan(plugin, "0000", 2, 0, "1a2b3c4d") is True
    assert plugin.associated_devices_scan.calls == [("0000", 2, 0, "1a2b3c4d")]


def test_notify_reports_a_response_the_collection_did_not_ask_for():
    plugin = Plugin()
    plugin.associated_devices_scan = Collector(False)
    assert notify_associated_devices_scan(plugin, "9999", 1, 0, "1a2b") is False


def test_the_request_type_is_the_extended_one():
    """RequestType 0x01 is the only one carrying NWKAddrAssocDevList."""
    assert EXTENDED_REQUEST_TYPE == "01"
