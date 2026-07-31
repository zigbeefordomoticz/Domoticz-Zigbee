#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools.check_stable9_migration

Small helper that warns the user that the `stable8` branch is closed for
new development and that `stable9` — built exclusively on the Domoticz
Extended Framework (`DomoticzEx`) — is where updates continue.

The Extended Framework has been available in Domoticz since version
2025.1, so unlike the earlier "cannot be probed" assumption, this script
queries the running Domoticz server's own JSON API
(`/json.htm?type=command&param=getversion`) to confirm the requirement
is met, the same way any other Domoticz JSON API client (including this
plugin) would. It uses only the Python standard library (`urllib`) so
it works with the system `python3` even when the plugin's virtualenv
(and its `requests` dependency) isn't active — which is normally the
case when this script is invoked outside the plugin.

If Domoticz cannot be reached (wrong --ip/--port, not running, etc.) the
script falls back to asking the user to confirm manually rather than
silently assuming success.

This tool cannot silently decide "you're good to go" for the second,
more important fact: the move is a ONE-WAY DOOR. Once Domoticz
(re)creates widgets under the Extended Framework, the `stable8` plugin
code can no longer manage them — there is no supported path back to
stable8 for an installation that has switched. Explicit confirmation is
always required before the switch is suggested.

Usage:

    python3 Tools/check_stable9_migration.py [--ip 127.0.0.1] [--port 8080]
                                              [--yes] [--simulate|--no-simulate]

`--simulate` (default) only prints the notice and the manual command to
run. `--no-simulate` additionally requires the user to type the
confirmation phrase before pointing them at
`Tools/plugin-switch-stable9.sh`.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from typing import Optional, Tuple

MIN_DOMOTICZ_VERSION = (2025, 1)  # DomoticzEx / Extended Framework available since 2025.1
DEFAULT_IP = "127.0.0.1"
DEFAULT_PORT = "8080"
GET_TIMEOUT = 5
CONFIRMATION_PHRASE = "I UNDERSTAND"


def get_domoticz_version(ip: str, port: str, timeout: int = GET_TIMEOUT) -> Tuple[Optional[Tuple[int, int]], Optional[str]]:
    """Query the running Domoticz server's own JSON API for its version.

    Returns a (version, error) tuple: version is a (year, release) tuple,
    e.g. (2025, 1), when successfully parsed, else None. error is a
    human-readable explanation of what went wrong, or None on success.
    """
    url = f"http://{ip}:{port}/json.htm?type=command&param=getversion"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            status = response.status
            body = response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return None, f"HTTP {e.code} response from {url} (is authentication enabled on Domoticz?)"
    except urllib.error.URLError as e:
        return None, f"could not connect to {url} ({e.reason})"
    except Exception as e:
        return None, f"request to {url} failed ({e})"

    if status != 200:
        return None, f"HTTP {status} response from {url}"

    try:
        payload = json.loads(body)
    except Exception as e:
        return None, f"response from {url} was not valid JSON ({e}); got: {body[:120]!r}"

    version_str = payload.get("version", "")
    m = re.match(r"(\d+)\.(\d+)", version_str)
    if not m:
        return None, f"'version' field missing or unparseable in response from {url}: {payload}"
    return (int(m.group(1)), int(m.group(2))), None


def display_migration_notice(version_status: str) -> None:
    english = (
        "The 'stable8' branch is now closed for new features and only receives\n"
        "critical bug fixes. All new development continues on 'stable9', which is\n"
        "built exclusively on the Domoticz Extended Framework (DomoticzEx),\n"
        "available since Domoticz 2025.1.\n\n"
        f"{version_status}\n\n"
        "WARNING - THIS IS A ONE-WAY MOVE:\n"
        "  Once your devices are (re)created by Domoticz under the Extended\n"
        "  Framework, the 'stable8' plugin can no longer read or manage them.\n"
        "  There is no supported way back to 'stable8' after switching."
    )

    french = (
        "La branche 'stable8' est désormais fermée aux nouvelles fonctionnalités et\n"
        "ne reçoit plus que des correctifs critiques. Tous les nouveaux développements\n"
        "se poursuivent sur 'stable9', basée exclusivement sur le Framework Étendu de\n"
        "Domoticz (DomoticzEx), disponible depuis Domoticz 2025.1.\n\n"
        "ATTENTION - CE BASCULEMENT EST IRRÉVERSIBLE :\n"
        "  Une fois vos périphériques recréés par Domoticz sous le Framework Étendu,\n"
        "  le plugin 'stable8' ne peut plus les lire ni les gérer. Il n'existe aucun\n"
        "  chemin de retour supporté vers 'stable8' après le basculement."
    )

    print("=" * 78)
    print("English:\n" + english + "\n")
    print("Français:\n" + french)
    print("=" * 78)


def main() -> None:
    parser = argparse.ArgumentParser(description="Warn about, and optionally trigger, the stable8 -> stable9 migration")
    parser.add_argument("--ip", default=DEFAULT_IP, help=f"Domoticz server IP/host (default: {DEFAULT_IP})")
    parser.add_argument("--port", default=DEFAULT_PORT, help=f"Domoticz web server port (default: {DEFAULT_PORT})")
    parser.add_argument("--min-version", default="2025.1", help="Minimum required Domoticz version, e.g. 2025.1")
    parser.add_argument("--simulate", dest="simulate", action="store_true", help="Only display the notice (default)")
    parser.add_argument("--no-simulate", dest="simulate", action="store_false", help="Require confirmation before pointing to the switch script")
    parser.add_argument("--yes", "-y", dest="yes", action="store_true", help="Skip the interactive confirmation phrase (non-interactive use only)")
    parser.set_defaults(simulate=True)
    args = parser.parse_args()

    mv = args.min_version.split(".")
    min_version = (int(mv[0]), int(mv[1]) if len(mv) > 1 else 0)

    detected, error = get_domoticz_version(args.ip, args.port)

    if detected is None:
        version_status = (
            f"Could not automatically verify the Domoticz version: {error}\n"
            "Please confirm manually, via Setup > About in Domoticz, that your version\n"
            "is 2025.1 or newer before switching. If Domoticz runs on a different host/port,\n"
            "pass --ip/--port.\n"
            "If Domoticz runs in a Docker container and this script was run from the Docker\n"
            "HOST (not via 'docker compose exec'), 127.0.0.1 on the host only reaches Domoticz\n"
            "if that port is published to the host. Either run this script inside the\n"
            "container (e.g. 'docker compose exec <container> bash -c \"cd <plugin_dir> &&\n"
            "Tools/plugin-switch-stable9.sh\"', matching Tools/update_domoticz_docker_container.sh),\n"
            "or pass --ip/--port matching the host-published address."
        )
        requirement_met = None  # unknown
    elif detected >= min_version:
        version_status = f"Detected Domoticz {detected[0]}.{detected[1]} at http://{args.ip}:{args.port} — Extended Framework requirement satisfied."
        requirement_met = True
    else:
        version_status = (
            f"Detected Domoticz {detected[0]}.{detected[1]} at http://{args.ip}:{args.port}, which is OLDER than the "
            f"minimum required ({min_version[0]}.{min_version[1]}) for the Extended Framework.\n"
            "Upgrade Domoticz itself before switching to 'stable9' — the plugin will fail to start otherwise."
        )
        requirement_met = False

    display_migration_notice(version_status)

    if requirement_met is False:
        print("\nAborting: Domoticz version requirement not met. No changes made.")
        raise SystemExit(1)

    if args.simulate:
        print("\nDry-run: to switch to 'stable9' run (manual):")
        print("    Tools/plugin-switch-stable9.sh")
        return

    print(f'\nTo continue, type exactly: {CONFIRMATION_PHRASE}')
    if args.yes:
        confirmed = True
    else:
        try:
            answer = input("> ")
        except EOFError:
            answer = ""
        confirmed = answer.strip() == CONFIRMATION_PHRASE

    if not confirmed:
        print("Confirmation not received. Aborted, no changes made.")
        raise SystemExit(1)

    print("Confirmation received. You may now run: Tools/plugin-switch-stable9.sh")


if __name__ == "__main__":
    main()
