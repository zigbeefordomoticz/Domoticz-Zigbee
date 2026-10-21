#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Regression coverage for the Associated Devices request issued by a TopologyV2
Network Topology scan.

_initNeighboursTableEntry() asks every router it starts scanning for its
associated device list, with a NWK_addr_req carrying RequestType 0x01 -- the
extended response, the only one that returns NumAssocDev / NWKAddrAssocDevList
and so the only one Decode8040() stores anything from.

That request used to be gated on "Full-Function Device" being present in the
device's Capability, falling back to RequestType 0x00 otherwise. Capability is
written in exactly one place (Modules/deviceAnnoucement.py, on a device
announce) and the coordinator never announces itself -- initLODZigate() builds
ListOfDevices["0000"] with no Capability key at all. The coordinator therefore
always took the fallback, and the devices associated to it were never
collected: precisely the end devices parented straight to the coordinator.

These tests pin RequestType 0x01 for the coordinator, for a router that has no
Capability recorded, and for a router whose Capability says reduced-function.

Classes/NetworkMap.py imports the real Modules.* package, which conflicts with
the stubs tests/conftest.py installs for the rest of the session, so the checks
run in a subprocess fully isolated from the pytest session -- same approach as
tests/Classes/test_scan_classes_deviceconf.py.
"""

import subprocess  # nosec B404
import sys
import textwrap
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

PREAMBLE = textwrap.dedent(
    """
    import sys, types
    from unittest.mock import MagicMock

    domoticz = types.ModuleType("DomoticzEx")
    for _name in ("Unit", "Connection", "Log", "Debug", "Error", "Status"):
        setattr(domoticz, _name, MagicMock(name=_name))
    domoticz.Configuration = MagicMock(name="Configuration", return_value={})
    sys.modules["DomoticzEx"] = domoticz

    import Classes.NetworkMap as nm


    class Log:
        def logging(self, *args, **kwargs):
            pass


    class PluginConf:
        def __init__(self, conf):
            self.pluginConf = conf


    SENT = []


    def record_nwk_address_request(self, nwkid, ieee, u8RequestType="00", u8StartIndex="00"):
        SENT.append((nwkid, ieee, u8RequestType, u8StartIndex))


    def make_network_map(list_of_devices):
        # mgmt_rtg() would push a real ZDP request; the routing table is not what
        # these tests are about.
        nm.mgmt_rtg = lambda self, nwkid, table: None
        nm.zdp_NWK_address_request = record_nwk_address_request

        instance = nm.NetworkMap(
            "zigpy",
            PluginConf({"TopologyV2": 1, "numTopologyReports": 4}),
            MagicMock(),
            list_of_devices,
            {},
            {},
            1,
            Log(),
            False,
        )
        instance.Neighbours = {}
        return instance


    def request_type_for(nwkid, device):
        del SENT[:]
        instance = make_network_map({nwkid: device})
        nm._initNeighboursTableEntry(instance, nwkid)
        assert len(SENT) == 1, "expected exactly one NWK_addr_req, got %s" % (SENT,)
        assert SENT[0][0] == nwkid
        assert SENT[0][1] == device["IEEE"]
        return SENT[0][2]
    """
)

# The coordinator record as initLODZigate() builds it: no Capability, no MacCapa.
COORDINATOR = {"IEEE": "00124b0022aabbcc", "LogicalType": "Coordinator", "Ep": {}}

CASES = {
    # The coordinator: the regression this fixes. is_a_router() returns True for
    # "0000" unconditionally, so it is scanned -- it just was never asked for its
    # associated devices.
    "coordinator": ("0000", COORDINATOR),
    # A router that has never announced itself since the plugin learnt it, so no
    # Capability was ever recorded.
    "router_without_capability": ("1234", {"IEEE": "00158d0001020304", "LogicalType": "Router"}),
    # A router whose announced Capability is reduced-function. It is still asked:
    # is_a_router() already let it through on LogicalType, and a node that cannot
    # answer an extended response costs the same request as the 0x00 fallback did.
    "router_reduced_function": (
        "5678",
        {"IEEE": "00158d0005060708", "LogicalType": "Router", "Capability": ["Reduced-Function Device"]},
    ),
}


def _run(snippet):
    """Execute `snippet` against the real (unstubbed) plugin modules."""
    result = subprocess.run(  # nosec B603
        [sys.executable, "-c", PREAMBLE + textwrap.dedent(snippet)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    return result.stdout.strip()


@pytest.mark.parametrize("case", sorted(CASES))
def test_associated_devices_request_is_always_extended(case):
    """Every node a TopologyV2 scan starts is asked with RequestType 0x01."""
    nwkid, device = CASES[case]
    assert _run(f"""
        print(request_type_for({nwkid!r}, {device!r}))
    """) == "01"


def test_associated_devices_not_requested_without_topology_v2():
    """Without TopologyV2 there are no per-device tables to fill, so nothing is asked."""
    assert _run("""
        instance = make_network_map({"0000": dict(%r)})
        instance.pluginconf.pluginConf["TopologyV2"] = 0
        nm._initNeighboursTableEntry(instance, "0000")
        print(len(SENT))
    """ % (COORDINATOR,)) == "0"
