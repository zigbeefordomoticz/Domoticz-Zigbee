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


def retrieve_configuration(db_path, decode_devices, timestamps_only, hw_id):
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

            print("\nTimestamps:")
            print(f"  ListOfDevices TimeStamp : {ts_to_human(lod_ts) if lod_ts else '<missing>'}")
            print(f"  PluginConf    TimeStamp : {ts_to_human(pc_ts) if pc_ts else '<missing>'}")
            print("--------------------------------------------")
            continue

        # -----------------------------------------------------
        # NORMAL MODE: FULL CONFIG (with optional b64-decoding)
        # -----------------------------------------------------
        config_copy = dict(config)

        # Handle base64 devices
        lod = config_copy.get("ListOfDevices", {})
        encoded_devices = lod.get("Devices")

        if encoded_devices is not None:
            if decode_devices:
                decoded_devices = decode_devices_field(encoded_devices)
                lod["Devices"] = "<decoded>"
                lod["Devices_decoded"] = decoded_devices
            else:
                # Keep base64 untouched
                lod["Devices_decoded"] = "<not decoded>"

        print("\nConfiguration:")
        pprint(config_copy, width=120)

        # Show decoded Devices clearly
        if decode_devices and encoded_devices:
            print("\nDecoded ListOfDevices['Devices']:")
            pprint(decoded_devices, width=120)

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
        "--decode-devices",
        action="store_true",
        help="Enable base64 decoding of ListOfDevices.Devices"
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

    retrieve_configuration(args.db, args.decode_devices, args.timestamps_only, args.hw_id)


if __name__ == "__main__":
    main()
