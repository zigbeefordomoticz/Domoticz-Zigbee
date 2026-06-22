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
Replace a physical Zigbee device by a new one while keeping the Domoticz history.

Use case
--------
A device dies and you replace it with a new (physical) one. Once the new device is
paired, the plugin created brand new Domoticz widgets for it (with a fresh IEEE and
fresh, empty history). You would rather keep the *old* widgets, because all the
historical data (Temperature, Meter, ...) is attached to them.

What "keeping the history" really means
---------------------------------------
In Domoticz, every sample table (``Temperature``, ``Meter``, ``MultiMeter``,
``Percentage`` ...) references a widget by ``DeviceRowID`` == ``DeviceStatus.ID``
(the Domoticz *Idx*). The history therefore follows the **old Idx**, not the IEEE.

Two things must point at the right place for the new device to drive the old widgets:

  1. Domoticz side (``DomoticzEx``): a widget is grouped under a device by
     ``DeviceStatus.DeviceID`` == the Zigbee IEEE. The old widgets must be
     re-pointed from the *old* IEEE to the *new* IEEE so the framework associates
     them with the new device.

  2. Plugin side (``Data/DeviceList-<hwid>.txt``): the plugin pushes an update to a
     widget through ``ListOfDevices[nwk]["Ep"][ep]["ClusterType"] = {str(Idx): type}``.
     The new device entry must therefore reference the **old Idx** values.

What this tool does
-------------------
Given the old IEEE and the new IEEE (both already known to the plugin):

  * Domoticz database (Domoticz MUST be stopped):
      - re-points every old widget ``DeviceID`` : old IEEE -> new IEEE
        (and rewrites the IEEE embedded in the widget ``Name``),
      - deletes the freshly created new widgets that have a same-type old
        counterpart, together with their (empty) history rows.
  * Plugin DeviceList:
      - rewrites the new device's per-endpoint ``ClusterType`` so each widget type
        now references the matching *old* Idx,
      - removes the old device entry (its NwkId no longer exists on the network).

Matching is done by widget type, endpoint by endpoint first, then across endpoints
as a fallback. This is meant for replacing a device by one of the same (or very
similar) kind. Anything that cannot be matched 1:1 is reported and left untouched
so nothing is silently lost.

Safety
------
- Dry-run by default: prints the full plan and writes nothing.
- ``--apply`` is required to write. Timestamped backups of both the Domoticz
  database and the DeviceList are made first.
- Stop Domoticz before running with ``--apply`` (the database is modified directly).
  Before writing, the tool checks that no process still has the database open and
  refuses to proceed otherwise (override with ``--force``, not recommended).

Usage
-----
    # inspect the plan (dry-run)
    python3 Tools/replace_device.py --db /path/to/domoticz.db --hwid 3 \
        --devicelist /path/to/Data/DeviceList-3.txt \
        --old-ieee 00124b00aaaaaaaa --new-ieee 00124b00bbbbbbbb

    # actually perform the replacement (Domoticz stopped, backups made first)
    python3 Tools/replace_device.py --db /path/to/domoticz.db --hwid 3 \
        --devicelist /path/to/Data/DeviceList-3.txt \
        --old-ieee 00124b00aaaaaaaa --new-ieee 00124b00bbbbbbbb --apply
"""

import argparse
import ast
import os
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


# --------------------------------------------------------------------------- #
# "Is Domoticz still using the database?" guard
# --------------------------------------------------------------------------- #
def check_database_in_use(db_path):
    """
    Find out whether the Domoticz database is still in use, Docker included.

    Modifying a SQLite database while Domoticz has it open corrupts both the file
    and the running instance, so we refuse to apply unless we are confident nothing
    is using it.

    Two complementary signals (a SQLite lock probe is deliberately not used: SQLite
    releases its locks between transactions, so it would report "all clear" while
    Domoticz merely sits idle):

      1. Open file descriptors on the database (or its ``-wal`` / ``-shm`` /
         ``-journal`` siblings). We match by **inode**, not by path: the kernel
         resolves ``/proc/<pid>/fd/N`` to the real open file, so ``os.stat`` returns
         the true device/inode even when the holder is a container that sees the
         file under a different mount-namespace path (bind-mounted Docker volume).

      2. A running ``domoticz`` process. The host ``/proc`` lists container
         processes too, so this catches the Dockerised case even when the
         container runs as root and we cannot read its ``/proc/<pid>/fd``.

    Returns a dict:
        available  : False when there is no /proc (non-Linux) -> cannot determine
        holders    : {pid: name} confirmed to have the db file open
        domoticz   : {pid: name} that look like a running Domoticz
        incomplete : True if some processes could not be inspected (permissions),
                     i.e. a holder might exist that we were not allowed to see
    """
    proc = Path("/proc")
    result = {"available": True, "holders": {}, "domoticz": {}, "incomplete": False}
    if not proc.is_dir():
        result["available"] = False
        return result

    # Target inodes: the db and any SQLite side files that currently exist.
    target_inodes = set()
    base = str(db_path.resolve())
    for suffix in ("", "-wal", "-shm", "-journal"):
        try:
            st = os.stat(base + suffix)
            target_inodes.add((st.st_dev, st.st_ino))
        except OSError:
            continue

    self_pid = os.getpid()
    for pid_dir in proc.iterdir():
        if not pid_dir.name.isdigit():
            continue
        pid = int(pid_dir.name)
        if pid == self_pid:
            continue

        name = _process_name(pid_dir)
        if name.lower() == "domoticz":
            result["domoticz"][pid] = name

        fd_dir = pid_dir / "fd"
        try:
            fds = os.listdir(fd_dir)
        except (PermissionError, FileNotFoundError, ProcessLookupError, NotADirectoryError):
            # A process we are not allowed to inspect (often a root-owned
            # container). It could be holding the db without us knowing.
            result["incomplete"] = True
            continue
        for fd in fds:
            try:
                st = os.stat(fd_dir / fd)  # follows the magic symlink -> real inode
            except OSError:
                continue
            if (st.st_dev, st.st_ino) in target_inodes:
                result["holders"][pid] = name
                break
    return result


def _process_name(pid_dir):
    """Best-effort human-readable name for a /proc/<pid> directory."""
    try:
        return (pid_dir / "comm").read_text().strip()
    except OSError:
        return "?"


# --------------------------------------------------------------------------- #
# Domoticz database helpers
# --------------------------------------------------------------------------- #
def load_widgets(conn, hwid):
    """Return {ieee: [(idx, unit, name), ...]} for every widget of the given hardware."""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT ID, DeviceID, Unit, Name FROM DeviceStatus WHERE HardwareID = ?",
        (hwid,),
    )
    widgets = {}
    for idx, device_id, unit, name in cursor.fetchall():
        widgets.setdefault(str(device_id), []).append((int(idx), unit, name))
    return widgets


def history_tables(conn):
    """Return the list of tables that reference a widget through a DeviceRowID column."""
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    tables = []
    for (table,) in cursor.fetchall():
        cursor.execute("PRAGMA table_info('%s')" % table)
        columns = [row[1] for row in cursor.fetchall()]
        if "DeviceRowID" in columns:
            tables.append(table)
    return tables


def delete_widget(conn, idx, tables):
    """Delete a widget and all its history rows. Returns rows deleted per table."""
    cursor = conn.cursor()
    deleted = {}
    for table in tables:
        cursor.execute("DELETE FROM %s WHERE DeviceRowID = ?" % table, (idx,))  # nosec B608 - table from sqlite_master
        if cursor.rowcount:
            deleted[table] = cursor.rowcount
    cursor.execute("DELETE FROM DeviceStatus WHERE ID = ?", (idx,))
    deleted["DeviceStatus"] = cursor.rowcount
    return deleted


def repoint_widget(conn, idx, old_ieee, new_ieee):
    """Move a widget to the new IEEE and rewrite the IEEE embedded in its Name."""
    cursor = conn.cursor()
    cursor.execute("SELECT Name FROM DeviceStatus WHERE ID = ?", (idx,))
    row = cursor.fetchone()
    new_name = row[0].replace(old_ieee, new_ieee) if row and row[0] else row[0] if row else None
    cursor.execute(
        "UPDATE DeviceStatus SET DeviceID = ?, Name = ? WHERE ID = ?",
        (new_ieee, new_name, idx),
    )
    return new_name


# --------------------------------------------------------------------------- #
# DeviceList.txt helpers (same format as Tools/printLOD.py and repair_clustertype.py)
# --------------------------------------------------------------------------- #
def load_devicelist_txt(path):
    """Load a DeviceList.txt into an ordered list of (nwkid, device_dict)."""
    devices = []
    with open(path, "r") as handle:
        for line in handle:
            if not line.strip():
                continue
            nwkid, raw = line.split(":", 1)
            nwkid = nwkid.replace(" ", "").replace("'", "")
            devices.append((nwkid, ast.literal_eval(raw)))  # nosec B307 - trusted local plugin data
    return devices


def write_devicelist_txt(path, devices):
    """Write the DeviceList back in the original one-device-per-line format."""
    with open(path, "w") as handle:
        for nwkid, device in devices:
            handle.write("%s : %s\n" % (nwkid, str(device)))


def find_device_by_ieee(devices, ieee):
    """Return (nwkid, device_dict) whose IEEE matches, or None."""
    for nwkid, device in devices:
        dev_ieee = device.get("IEEE")
        if isinstance(dev_ieee, str) and dev_ieee.lower() == ieee.lower():
            return nwkid, device
    return None


def iter_cluster_types(device):
    """
    Yield (container, ep) for every place a ClusterType dict lives on a device.

    ``container`` is the dict that *holds* the ``ClusterType`` key, so callers can
    read/replace ``container["ClusterType"]`` in place. ``ep`` is the endpoint label
    ("00" for the legacy top-level/global ClusterType).
    """
    if isinstance(device.get("ClusterType"), dict) and device["ClusterType"]:
        yield device, "00"
    for ep, ep_record in device.get("Ep", {}).items():
        if isinstance(ep_record, dict) and isinstance(ep_record.get("ClusterType"), dict) and ep_record["ClusterType"]:
            yield ep_record, ep


def collect_widget_types(device):
    """Return a list of (ep, idx_str, wtype) for every ClusterType entry of a device."""
    entries = []
    for container, ep in iter_cluster_types(device):
        for idx_str, wtype in container["ClusterType"].items():
            entries.append((ep, str(idx_str), wtype))
    return entries


# --------------------------------------------------------------------------- #
# Matching: new widget Idx -> old widget Idx, by type (per endpoint, then global)
# --------------------------------------------------------------------------- #
def build_remap(old_device, new_device):
    """
    Map each new ClusterType Idx to an old ClusterType Idx of the same widget type.

    Matching is greedy: same endpoint and same type first, then same type on any
    endpoint. Returns (remap, matched_old, unmatched_new, unmatched_old, notes):

      - remap          : {new_idx: old_idx}
      - matched_old    : set(old_idx) consumed by the mapping
      - unmatched_new  : list of (ep, new_idx, wtype) with no old counterpart
      - unmatched_old  : list of (ep, old_idx, wtype) never consumed
      - notes          : human-readable remarks (e.g. cross-endpoint fallbacks)
    """
    old_entries = collect_widget_types(old_device)
    new_entries = collect_widget_types(new_device)

    available_old = list(old_entries)  # entries we can still consume
    remap = {}
    matched_old = set()
    unmatched_new = []
    notes = []

    def take(predicate):
        for i, entry in enumerate(available_old):
            if predicate(entry):
                return available_old.pop(i)
        return None

    for ep, new_idx, wtype in new_entries:
        match = take(lambda e, ep=ep, wtype=wtype: e[0] == ep and e[2] == wtype)
        if match is None:
            match = take(lambda e, wtype=wtype: e[2] == wtype)
            if match is not None:
                notes.append(
                    "  ~~ type '%s': new ep %s matched to old ep %s (endpoints differ)"
                    % (wtype, ep, match[0])
                )
        if match is None:
            unmatched_new.append((ep, new_idx, wtype))
            continue
        old_ep, old_idx, _ = match
        remap[new_idx] = old_idx
        matched_old.add(old_idx)

    unmatched_old = [(ep, idx, wtype) for ep, idx, wtype in available_old]
    return remap, matched_old, unmatched_new, unmatched_old, notes


def apply_remap_to_new_device(new_device, remap):
    """Rewrite the new device's ClusterType dicts so matched Idx become the old Idx."""
    for container, _ep in iter_cluster_types(new_device):
        old_ct = container["ClusterType"]
        new_ct = {}
        for idx_str, wtype in old_ct.items():
            new_ct[str(remap.get(str(idx_str), idx_str))] = wtype
        container["ClusterType"] = new_ct


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    parser = argparse.ArgumentParser(
        description="Replace a Zigbee device by a new one while keeping the Domoticz history."
    )
    parser.add_argument("--db", required=True, help="Path to the Domoticz database (domoticz.db)")
    parser.add_argument("--hwid", required=True, type=int, help="Domoticz Hardware ID of the Zigbee plugin")
    parser.add_argument("--devicelist", required=True, help="Path to the plugin DeviceList-<hwid>.txt")
    parser.add_argument("--old-ieee", required=True, help="IEEE of the device being replaced (history source)")
    parser.add_argument("--new-ieee", required=True, help="IEEE of the new (already paired) device")
    parser.add_argument("--apply", action="store_true", help="Perform the changes (backups are made first). Stop Domoticz before using this.")
    parser.add_argument("--yes", action="store_true", help="Do not ask for interactive confirmation when applying")
    parser.add_argument("--force", action="store_true", help="Apply even if the database appears to be open by another process (NOT recommended)")
    args = parser.parse_args()

    old_ieee = args.old_ieee.lower()
    new_ieee = args.new_ieee.lower()

    db_path = Path(args.db)
    devicelist_path = Path(args.devicelist)
    if old_ieee == new_ieee:
        print("Old and new IEEE are identical - nothing to do.")
        return
    if not db_path.exists():
        print("Database file not found: %s" % db_path)
        return
    if not devicelist_path.exists():
        print("DeviceList file not found: %s" % devicelist_path)
        return

    # ----- Load DeviceList and locate both devices -----
    devices = load_devicelist_txt(devicelist_path)
    old_found = find_device_by_ieee(devices, old_ieee)
    new_found = find_device_by_ieee(devices, new_ieee)
    if old_found is None:
        print("Old IEEE %s not found in %s" % (old_ieee, devicelist_path))
        return
    if new_found is None:
        print("New IEEE %s not found in %s - is the new device paired?" % (new_ieee, devicelist_path))
        return
    old_nwk, old_device = old_found
    new_nwk, new_device = new_found
    print("Old device : NwkId %s  IEEE %s  Model %s" % (old_nwk, old_ieee, old_device.get("Model")))
    print("New device : NwkId %s  IEEE %s  Model %s" % (new_nwk, new_ieee, new_device.get("Model")))
    print()

    # ----- Read widgets from the Domoticz database -----
    conn = sqlite3.connect(db_path)
    try:
        widgets = load_widgets(conn, args.hwid)
        hist_tables = history_tables(conn)
    finally:
        conn.close()

    old_widgets = widgets.get(old_ieee, [])
    new_widgets = widgets.get(new_ieee, [])
    if not old_widgets:
        print("No Domoticz widget found for the old IEEE %s (hwid %s) - nothing to preserve." % (old_ieee, args.hwid))
        return

    # ----- Compute the type-based remap from the DeviceList ClusterType -----
    remap, matched_old, unmatched_new, unmatched_old, notes = build_remap(old_device, new_device)

    # Idx coming from the DB, to cross-check the ClusterType references.
    old_db_idx = {idx for idx, _u, _n in old_widgets}
    new_db_idx = {idx for idx, _u, _n in new_widgets}

    # New widgets that we are going to delete (those whose Idx is being superseded).
    new_idx_to_delete = sorted({int(n) for n in remap if int(n) in new_db_idx})
    # Old widgets to re-point: every old widget moves to the new device so they stay grouped.
    old_idx_to_repoint = sorted(old_db_idx)

    # ----- Report the plan -----
    print("=== Plan ===")
    print("Domoticz database (%s):" % db_path)
    print("  Re-point old widgets to the new IEEE (history preserved):")
    for idx in old_idx_to_repoint:
        name = next((n for i, _u, n in old_widgets if i == idx), "")
        consumed = "" if str(idx) in matched_old else "   [no new counterpart - will keep but stay frozen]"
        print("    Idx %-6s %s%s" % (idx, name, consumed))
    if new_idx_to_delete:
        print("  Delete superseded new widgets (and their empty history):")
        for idx in new_idx_to_delete:
            name = next((n for i, _u, n in new_widgets if i == idx), "")
            print("    Idx %-6s %s" % (idx, name))
    else:
        print("  No new widget to delete.")

    print()
    print("Plugin DeviceList (%s):" % devicelist_path)
    print("  Rewrite new device (NwkId %s) ClusterType -> old Idx:" % new_nwk)
    for new_idx, old_idx in sorted(remap.items(), key=lambda kv: int(kv[0])):
        print("    %s -> %s" % (new_idx, old_idx))
    print("  Remove old device entry NwkId %s (no longer on the network)." % old_nwk)

    for note in notes:
        print(note)
    for ep, idx, wtype in unmatched_new:
        print("  !! new widget type '%s' (ep %s, idx %s) has no old counterpart - kept as new widget" % (wtype, ep, idx))
    for ep, idx, wtype in unmatched_old:
        print("  !! old widget type '%s' (ep %s, idx %s) not produced by the new device - re-pointed but frozen" % (wtype, ep, idx))

    # Sanity warnings about ClusterType <-> DB consistency.
    stale_old = {int(i) for _e, i, _t in collect_widget_types(old_device) if int(i) not in old_db_idx}
    if stale_old:
        print("  ?? old ClusterType references Idx not present in the DB: %s" % sorted(stale_old))
    stale_new = {int(i) for _e, i, _t in collect_widget_types(new_device) if int(i) not in new_db_idx}
    if stale_new:
        print("  ?? new ClusterType references Idx not present in the DB: %s" % sorted(stale_new))

    if not remap:
        print("\nNo widget type could be matched between the two devices - aborting.")
        return

    if not args.apply:
        print("\nDry-run only. Re-run with --apply to perform the replacement.")
        return

    # ----- Apply -----
    # Refuse to touch a database that Domoticz (host or container) still uses:
    # concurrent writes would corrupt both the file and the running instance.
    usage = check_database_in_use(db_path)
    blocking = dict(usage["holders"])
    blocking.update(usage["domoticz"])
    if blocking:
        print("\nDomoticz appears to be running / the database is in use - refusing to modify it:")
        for pid, name in sorted(blocking.items()):
            kind = "holds the db open" if pid in usage["holders"] else "domoticz process"
            print("    pid %s (%s) - %s" % (pid, name, kind))
        print("Stop Domoticz (or its Docker container) first, then re-run.")
        if not args.force:
            return
        print("--force given: proceeding anyway. This is dangerous.")
    elif not usage["available"]:
        print("\nCould not verify whether the database is in use (no /proc on this system).")
        print("Make absolutely sure Domoticz is stopped before continuing.")
    elif usage["incomplete"]:
        print("\nNo running Domoticz detected, but some processes could not be inspected")
        print("(e.g. root-owned containers). If Domoticz runs in Docker, confirm the")
        print("container is stopped - run this tool as root for a fully reliable check.")

    if not args.yes:
        print("\nMake sure Domoticz is STOPPED before continuing (the database is modified directly).")
        answer = input("Type 'yes' to proceed: ")  # nosec B322
        if answer.strip().lower() != "yes":
            print("Aborted.")
            return

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    db_backup = db_path.with_suffix(db_path.suffix + ".bak-%s" % stamp).resolve()
    dl_backup = devicelist_path.with_suffix(devicelist_path.suffix + ".bak-%s" % stamp).resolve()
    shutil.copy2(db_path, db_backup)
    shutil.copy2(devicelist_path, dl_backup)
    print("\nBackups created (keep these to restore if anything goes wrong):")
    print("  Domoticz database backed up:")
    print("    folder   : %s" % db_backup.parent)
    print("    filename : %s" % db_backup.name)
    print("    size     : %d bytes" % db_backup.stat().st_size)
    print("  DeviceList backed up:")
    print("    folder   : %s" % dl_backup.parent)
    print("    filename : %s" % dl_backup.name)
    print("    size     : %d bytes" % dl_backup.stat().st_size)

    # Database changes in a single transaction.
    conn = sqlite3.connect(db_path)
    try:
        for idx in new_idx_to_delete:
            deleted = delete_widget(conn, idx, hist_tables)
            print("  deleted widget Idx %s: %s" % (idx, deleted))
        for idx in old_idx_to_repoint:
            new_name = repoint_widget(conn, idx, old_ieee, new_ieee)
            print("  re-pointed widget Idx %s -> %s (Name: %s)" % (idx, new_ieee, new_name))
        conn.commit()
    except Exception:
        conn.rollback()
        conn.close()
        print("\nDatabase update failed and was rolled back. DeviceList left untouched.")
        raise
    finally:
        conn.close()

    # DeviceList changes.
    apply_remap_to_new_device(new_device, remap)
    devices = [(nwk, dev) for nwk, dev in devices if nwk != old_nwk]
    write_devicelist_txt(devicelist_path, devices)

    print("\nDeviceList updated: new device ClusterType re-pointed, old entry removed.")
    print("Restart Domoticz (and the plugin) to load the updated database and DeviceList.")


if __name__ == "__main__":
    main()
