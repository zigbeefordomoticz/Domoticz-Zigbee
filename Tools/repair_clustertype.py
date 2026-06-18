#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Repair empty per-endpoint ``ClusterType`` cross-references (issue #1987).

Background
----------
``ListOfDevices[nwk]["Ep"][ep]["ClusterType"]`` maps a Domoticz widget Idx to the
widget type and is what lets the plugin push updates to the right widget. A long
standing bug (fixed forward in ``Modules/zclClusterHelpers.py``) could wipe this map
when a device re-announced its Model Name. Devices damaged *before* that fix keep
replaying the empty map from the persisted ``DeviceList.txt``.

This standalone, manually-run tool rebuilds the missing ``ClusterType`` entries from
the Domoticz widgets that still exist in the Domoticz database. The widgets carry all
the information we need:

  - ``DeviceStatus.DeviceID``  -> the Zigbee IEEE address
  - ``DeviceStatus.ID``        -> the Domoticz Idx == the ClusterType key
  - ``DeviceStatus.Name``      -> ``[<NickName|Model>_]<cType>-<IEEE>-<EP>``
                                  (see ``deviceName()`` in Modules/domoCreate.py)

From the widget name we recover the endpoint (``EP``) and the widget type (``cType``)
and re-register ``Ep[EP]["ClusterType"][str(Idx)] = cType`` for any endpoint whose
ClusterType is currently empty/missing.

Safety
------
- Dry-run by default: prints the proposed changes and writes nothing.
- ``--apply`` is required to write, and a timestamped ``.bak`` copy is made first.
- Only *adds* missing widget keys; never removes or overwrites an existing entry.

Usage
-----
    # inspect (dry-run)
    python3 Tools/repair_clustertype.py --db /path/to/domoticz.db --hwid 3 \
        --devicelist /path/to/Data/DeviceList-3.txt

    # actually write the repaired DeviceList
    python3 Tools/repair_clustertype.py --db /path/to/domoticz.db --hwid 3 \
        --devicelist /path/to/Data/DeviceList-3.txt --apply
"""

import argparse
import ast
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


def load_widgets(db_path: Path, hwid: int):
    """Return {ieee: [(idx, unit, name), ...]} for every widget of the given hardware."""
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT ID, DeviceID, Unit, Name FROM DeviceStatus WHERE HardwareID = ?",
            (hwid,),
        )
        rows = cursor.fetchall()
    finally:
        conn.close()

    widgets = {}
    for idx, device_id, unit, name in rows:
        widgets.setdefault(str(device_id), []).append((str(idx), unit, name))
    return widgets


def load_devicelist_txt(path: Path):
    """
    Load a DeviceList.txt file into an ordered list of (nwkid, device_dict).

    The file format is one device per line: ``<nwkid> : <python-dict-repr>`` (the same
    format printed by Tools/printLOD.py).
    """
    devices = []
    with open(path, "r") as handle:
        for line in handle:
            if not line.strip():
                continue
            nwkid, raw = line.split(":", 1)
            nwkid = nwkid.replace(" ", "").replace("'", "")
            devices.append((nwkid, ast.literal_eval(raw)))  # nosec B307 - trusted local plugin data
    return devices


def parse_widget_name(name: str, model):
    """
    Recover (cType, ep) from a widget name ``[<NickName|Model>_]<cType>-<IEEE>-<EP>``.

    Returns None when the name does not match the expected pattern.
    """
    if not name or name.count("-") < 2:
        return None

    # Endpoint and IEEE are the last two dash-separated tokens; cType values do not
    # contain a dash, so a right split is unambiguous.
    left, _ieee, ep = name.rsplit("-", 2)

    # Strip the optional "<Model>_" / "<NickName>_" prefix. We know the Model from the
    # device record; NickName is unknown here so we fall back to the last "_" segment.
    if model and left.startswith("%s_" % model):
        cluster_type = left[len(model) + 1:]
    elif "_" in left:
        cluster_type = left.rsplit("_", 1)[1]
    else:
        cluster_type = left

    if not ep or not cluster_type:
        return None
    return cluster_type, ep


def repair_device(nwkid, device, widgets):
    """
    Rebuild missing ClusterType entries for a single device in place.

    Returns a list of human-readable change descriptions (empty if nothing to do).
    """
    changes = []

    ieee = device.get("IEEE")
    if not ieee or ieee not in widgets:
        return changes
    if "Ep" not in device or not isinstance(device["Ep"], dict):
        return changes

    model = device.get("Model")
    model = model if isinstance(model, str) else None

    for idx, _unit, name in widgets[ieee]:
        parsed = parse_widget_name(name, model)
        if parsed is None:
            changes.append("  ?? %s / idx %s: cannot parse widget name '%s' - skipped" % (nwkid, idx, name))
            continue
        cluster_type, ep = parsed

        if ep not in device["Ep"]:
            changes.append("  ?? %s / idx %s: endpoint %s absent from DeviceList - skipped" % (nwkid, idx, ep))
            continue

        ep_record = device["Ep"][ep]
        existing = ep_record.get("ClusterType")
        if not isinstance(existing, dict):
            ep_record["ClusterType"] = existing = {}

        if idx in existing:
            # Healthy entry, leave it untouched.
            continue

        existing[idx] = cluster_type
        changes.append("  ++ %s ep %s: ClusterType['%s'] = '%s'  (from widget '%s')" % (nwkid, ep, idx, cluster_type, name))

    return changes


def write_devicelist_txt(path: Path, devices):
    """Write the DeviceList back in the original one-device-per-line format."""
    with open(path, "w") as handle:
        for nwkid, device in devices:
            handle.write("%s : %s\n" % (nwkid, str(device)))


def main():
    parser = argparse.ArgumentParser(description="Repair empty per-endpoint ClusterType from Domoticz widgets (issue #1987)")
    parser.add_argument("--db", required=True, help="Path to the Domoticz database (domoticz.db)")
    parser.add_argument("--hwid", required=True, type=int, help="Domoticz Hardware ID of the Zigbee plugin")
    parser.add_argument("--devicelist", required=True, help="Path to the plugin DeviceList-<hwid>.txt to repair")
    parser.add_argument("--apply", action="store_true", help="Write the repaired DeviceList (a .bak copy is made first)")
    args = parser.parse_args()

    db_path = Path(args.db)
    devicelist_path = Path(args.devicelist)
    if not db_path.exists():
        print("Database file not found: %s" % db_path)
        return
    if not devicelist_path.exists():
        print("DeviceList file not found: %s" % devicelist_path)
        return

    widgets = load_widgets(db_path, args.hwid)
    if not widgets:
        print("No widget found for Hardware ID %s - nothing to repair." % args.hwid)
        return

    devices = load_devicelist_txt(devicelist_path)

    all_changes = []
    for nwkid, device in devices:
        all_changes.extend(repair_device(nwkid, device, widgets))

    additions = [c for c in all_changes if c.lstrip().startswith("++")]
    if not all_changes:
        print("Nothing to repair: every device with widgets already has its ClusterType.")
        return

    print("Proposed ClusterType repairs:")
    for change in all_changes:
        print(change)
    print("\n%d ClusterType entry(ies) to restore." % len(additions))

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to write the changes.")
        return

    if not additions:
        print("\nNo actual additions to write.")
        return

    backup = devicelist_path.with_suffix(devicelist_path.suffix + ".bak-%s" % datetime.now().strftime("%Y%m%d%H%M%S"))
    shutil.copy2(devicelist_path, backup)
    write_devicelist_txt(devicelist_path, devices)
    print("\nBackup written to %s" % backup)
    print("Repaired DeviceList written to %s" % devicelist_path)
    print("Restart the plugin to reload the repaired DeviceList.")


if __name__ == "__main__":
    main()
