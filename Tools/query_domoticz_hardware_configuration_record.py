#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import sqlite3
import json
import base64
from pathlib import Path
from datetime import datetime


def safe_b64_decode(value: str):
    """Try to decode Base64, return original string if it fails."""
    try:
        # Fix missing padding if needed
        missing = len(value) % 4
        if missing:
            value += "=" * (4 - missing)

        decoded = base64.b64decode(value)
        try:
            return decoded.decode("utf-8", errors="replace")
        except Exception:
            return decoded  # Return raw bytes if not UTF-8
    except Exception:
        return value


def format_timestamps(obj):
    """Recursively convert any numeric TimeStamp fields to human-readable format."""
    if isinstance(obj, dict):
        new_dict = {}
        for k, v in obj.items():
            if isinstance(v, (int, float)) and "timestamp" in k.lower():
                try:
                    formatted = datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
                    new_dict[k] = f"{v} ({formatted})"
                except Exception:
                    new_dict[k] = v
            else:
                new_dict[k] = format_timestamps(v)
        return new_dict
    elif isinstance(obj, list):
        return [format_timestamps(i) for i in obj]
    return obj


def recursive_b64_decode(obj):
    """Recursively decode Base64 strings inside structures."""
    if isinstance(obj, dict):
        return {k: recursive_b64_decode(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [recursive_b64_decode(i) for i in obj]
    elif isinstance(obj, str):
        # Attempt Base64 decode
        return safe_b64_decode(obj)
    return obj


def extract_json_entry(data: dict, entry_path: str):
    """Extract specific JSON entry using dot-notation."""
    keys = entry_path.split(".")
    current = data
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            print(f"❌ Entry '{entry_path}' not found in configuration.")
            return None
    return current


def extract_configuration(db_path: Path, hardware_id: int, entry: str | None, decode_b64: bool):
    """Extract JSON configuration (whole or partial), with optional b64 decoding and timestamp formatting."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT Configuration FROM Hardware WHERE ID = ?",
        (hardware_id,)
    )
    row = cursor.fetchone()
    conn.close()

    if not row:
        print(f"❌ No Hardware entry with ID {hardware_id}")
        return

    config_text = row[0]
    if not config_text:
        print(f"⚠️ Hardware ID {hardware_id} has an empty Configuration field.")
        return

    # Decode JSON
    try:
        config_json = json.loads(config_text)
    except Exception:
        print("⚠️ Configuration is not valid JSON. Raw content below:\n")
        print(config_text)
        return

    # Extract a specific entry if requested
    if entry:
        result = extract_json_entry(config_json, entry)
        if result is None:
            return
    else:
        result = config_json

    # Optionally decode Base64 fields
    if decode_b64:
        result = recursive_b64_decode(result)

    # Format timestamps by default
    result = format_timestamps(result)

    print(json.dumps(result, indent=4, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Extract Domoticz Hardware Configuration")
    parser.add_argument("--db", required=True, help="Path to Domoticz database (domoticz.db)")
    parser.add_argument("--id", required=True, type=int, help="Hardware ID")
    parser.add_argument("--entry", help="Specific entry to extract (supports nested paths)")
    parser.add_argument("--decode-b64", action="store_true", help="Decode Base64-encoded values automatically")

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        return

    extract_configuration(db_path, args.id, args.entry, args.decode_b64)


if __name__ == "__main__":
    main()
