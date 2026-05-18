#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import ast
import base64
import contextlib
import json
import sqlite3
import zlib
from datetime import datetime
from pathlib import Path


def decode_b64_payload(value: str, version: int):
    """Decode a single plugin-stored base64 attribute using the given format version."""
    try:
        raw = base64.b64decode(value)
    except Exception as e:
        raise ValueError(f"base64 decode failed: {e}") from e

    if version == 2:
        try:
            raw = zlib.decompress(raw)
        except zlib.error as e:
            raise ValueError(f"zlib decompress failed: {e}") from e
        try:
            return json.loads(raw.decode("utf-8"))
        except Exception as e:
            raise ValueError(f"JSON decode failed: {e}") from e

    # Version 1: uncompressed, stored as Python repr (str() output)
    try:
        decoded = raw.decode("utf-8")
    except Exception as e:
        raise ValueError(f"UTF-8 decode failed: {e}") from e

    with contextlib.suppress(json.JSONDecodeError):
        return json.loads(decoded)

    try:
        return ast.literal_eval(decoded)
    except Exception as e:
        raise ValueError(
            f"neither JSON nor Python literal: {e}\nDecoded content was:\n{decoded}") from e


def decode_plugin_config_entry(entry: dict) -> dict:
    """
    Decode all b64-* attributes in a single plugin config entry dict.

    A plugin config entry has the shape:
        {"Version": 1|2, "TimeStamp": ..., "b64-<attr>": "<encoded>", ...}

    Each b64-* key is decoded using the Version stored in the same dict,
    so Version 1 (uncompressed Python repr) and Version 2 (zlib + JSON) are
    both handled correctly without guessing.
    """
    if not isinstance(entry, dict) or "Version" not in entry:
        return entry

    version = entry["Version"]
    result = {}
    for key, value in entry.items():
        if key.startswith("b64-") and isinstance(value, str):
            try:
                result[key] = decode_b64_payload(value, version)
            except Exception as e:
                result[key] = f"<decode error: {e}>"
        else:
            result[key] = value
    return result


def format_timestamps(obj):
    """Recursively convert numeric TimeStamp fields to human-readable format."""
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


def extract_json_entry(data: dict, entry_path: str):
    """Extract a specific JSON entry using dot-notation."""
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

    try:
        config_json = json.loads(config_text)
    except Exception:
        print("⚠️ Configuration is not valid JSON. Raw content below:\n")
        print(config_text)
        return

    # Decode b64 attributes before entry extraction so that dot-notation paths
    # (e.g. "ListOfDevices.b64-devicelist") navigate into already-decoded data.
    # Each top-level value is an independent plugin config entry with its own Version.
    if decode_b64:
        config_json = {k: decode_plugin_config_entry(v) for k, v in config_json.items()}

    if entry:
        result = extract_json_entry(config_json, entry)
        if result is None:
            return
    else:
        result = config_json

    result = format_timestamps(result)

    print(json.dumps(result, indent=4, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description="Extract Domoticz Hardware Configuration")
    parser.add_argument("--db", required=True, help="Path to Domoticz database (domoticz.db)")
    parser.add_argument("--id", required=True, type=int, help="Hardware ID")
    parser.add_argument("--entry", help="Specific entry to extract (supports dot-notation, e.g. ListOfDevices.b64-devicelist)")
    parser.add_argument("--decode-b64", action="store_true", help="Decode Base64-encoded plugin attributes (version-aware)")

    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"❌ Database file not found: {db_path}")
        return

    extract_configuration(db_path, args.id, args.entry, args.decode_b64)


if __name__ == "__main__":
    main()
