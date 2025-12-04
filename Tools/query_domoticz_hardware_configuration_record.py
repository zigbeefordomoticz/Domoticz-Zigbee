#!/usr/bin/env python3
import sqlite3
import json
import base64
import ast
import argparse
from pprint import pprint
from datetime import datetime


def decode_devices_field(encoded_str):
    """Decode the base64-encoded Devices field into a Python dict."""
    try:
        raw = base64.b64decode(encoded_str).decode("utf-8", errors="replace")
        return ast.literal_eval(raw)
    except Exception as e:
        print(f"❌ Error decoding Devices: {e}")
        return None


def ts_to_human(ts):
    """Convert timestamp float → human readable."""
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return f"<invalid: {ts}>"


def retrieve_configuration(db_path, b64_decoding, timestamps_only, hw_id):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # If hw_id is specified, filter query
    if hw_id is not None:
        cursor.execute("SELECT ID, Name, Configuration FROM Hardware WHERE ID=?", (hw_id,))
    else:
        cursor.execute("SELECT ID, Name, Configuration FROM Hardware;")

    rows = cursor.fetchall()

    if not rows:
        print("No hardware record found matching the criteria.")
        conn.close()
        return

    for hw_id, name, config_raw in rows:
        print(f"\n=== Hardware ID {hw_id} — {name} ===")

        if not config_raw:
            print("Configuration: <empty>")
            continue

        try:
            config = json.loads(config_raw)
        except json.JSONDecodeError:
            print("❌ ERROR: Configuration is not valid JSON:")
            print(config_raw)
            continue

        # -----------------------------------------------------
        # MODE: TIMESTAMP-ONLY
        # -----------------------------------------------------
        if timestamps_only:
            lod_ts = config.get("ListOfDevices", {}).get("TimeStamp")
            pc_ts  = config.get("PluginConf", {}).get("TimeStamp")
            log_ts = config.get("ListOfGroups", {}).get("TimeStamp")

            print("\nTimestamps:")
            print(f"  ListOfDevices TimeStamp : {ts_to_human(lod_ts) if lod_ts else '<missing>'}")
            print(f"  PluginConf    TimeStamp : {ts_to_human(pc_ts) if pc_ts else '<missing>'}")
            print(f"  ListOfGroups  TimeStamp : {ts_to_human(log_ts) if log_ts else '<missing>'}")
            print("--------------------------------------------")
            continue

        # -----------------------------------------------------
        # NORMAL MODE: FULL CONFIG (with optional b64-decoding)
        # -----------------------------------------------------
        config_copy = dict(config)

        # Handle ListOfDevices
        lod = config_copy.get("ListOfDevices", {})
        encoded_devices = lod.get("Devices")

        if encoded_devices is not None:
            if b64_decoding:
                decoded_devices = decode_devices_field(encoded_devices)
                lod["Devices"] = "<decoded>"
                lod["Devices_decoded"] = decoded_devices
            else:
                lod["Devices_decoded"] = "<not decoded>"

        # Handle ListOfGroups
        log = config_copy.get("ListOfGroups", {})
        b64_groups = log.get("b64Groups")
        if b64_groups is not None:
            if b64_decoding:
                # In most cases, Devices inside groups are already decoded lists
                for gid, group in b64_groups.items():
                    devices = group.get("Devices")
                    if isinstance(devices, str):
                        # decode if actually base64
                        group["Devices_decoded"] = decode_devices_field(devices)
                        group["Devices"] = "<decoded>"
                    else:
                        group["Devices_decoded"] = devices
                log["b64Groups"] = b64_groups
            else:
                for gid, group in b64_groups.items():
                    group["Devices_decoded"] = "<not decoded>"

        print("\nConfiguration:")
        pprint(config_copy, width=120)

        # Show decoded Devices clearly
        if b64_decoding:
            if encoded_devices:
                print("\nDecoded ListOfDevices['Devices']:")
                pprint(decoded_devices, width=120)
            if b64_groups:
                print("\nDecoded ListOfGroups['b64Groups'] Devices:")
                pprint(b64_groups, width=120)

        print("--------------------------------------------")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Read Domoticz Hardware.Configuration field")
    parser.add_argument(
        "--db",
        help="Path to domoticz.db (default: ./domoticz.db)",
        default="domoticz.db"
    )
    parser.add_argument(
        "--b64-decoding",
        action="store_true",
        help="Enable base64 decoding of ListOfDevices.Devices and ListOfGroups"
    )
    parser.add_argument(
        "--timestamps-only",
        action="store_true",
        help="Show only timestamps, converted to human-readable format"
    )
    parser.add_argument(
        "--hw-id",
        type=int,
        help="Display only the hardware record with this ID"
    )

    args = parser.parse_args()

    retrieve_configuration(args.db, args.b64_decoding, args.timestamps_only, args.hw_id)


if __name__ == "__main__":
    main()
