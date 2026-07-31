#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools.check_stable9_migration

Small helper that warns the user that the `stable8` branch is closed for
new development and that `stable9` — built exclusively on the Domoticz
Extended Framework (`DomoticzEx`) — is where updates continue.

Unlike the earlier stable7 -> stable8 check, this is NOT a Python-version
gate: `DomoticzEx` is a capability of the running Domoticz server itself
and cannot be reliably probed from a standalone script outside of it.
This tool therefore cannot silently decide "you're good to go" the way
the old Python-version check could. Its job is to make sure the user has
explicitly acknowledged the two facts that matter before anything is
touched:

  1. `stable9` requires a Domoticz build with the Extended Framework
     available and enabled for this hardware instance.
  2. The move is a ONE-WAY DOOR. Once Domoticz (re)creates widgets under
     the Extended Framework, the `stable8` plugin code can no longer
     manage them — there is no supported path back to stable8 for an
     installation that has switched.

Usage:

    python3 Tools/check_stable9_migration.py [--yes] [--simulate|--no-simulate]

`--simulate` (default) only prints the warning and the manual command to
run. `--no-simulate` additionally offers to invoke
`Tools/plugin-switch-stable9.sh` once the user has typed the
confirmation phrase.
"""

from __future__ import annotations

import argparse

CONFIRMATION_PHRASE = "I UNDERSTAND"


def display_migration_notice() -> None:
    english = (
        "The 'stable8' branch is now closed for new features and only receives\n"
        "critical bug fixes. All new development continues on 'stable9', which is\n"
        "built exclusively on the Domoticz Extended Framework (DomoticzEx).\n\n"
        "Before switching, make sure that:\n"
        "  - Your Domoticz server exposes the Extended Framework (check your\n"
        "    Domoticz version and Settings) — the plugin will fail to start\n"
        "    otherwise, as 'stable9' no longer supports the legacy widget model.\n\n"
        "WARNING - THIS IS A ONE-WAY MOVE:\n"
        "  Once your devices are (re)created by Domoticz under the Extended\n"
        "  Framework, the 'stable8' plugin can no longer read or manage them.\n"
        "  There is no supported way back to 'stable8' after switching."
    )

    french = (
        "La branche 'stable8' est désormais fermée aux nouvelles fonctionnalités et\n"
        "ne reçoit plus que des correctifs critiques. Tous les nouveaux développements\n"
        "se poursuivent sur 'stable9', basée exclusivement sur le Framework Étendu de\n"
        "Domoticz (DomoticzEx).\n\n"
        "Avant de basculer, assurez-vous que :\n"
        "  - Votre serveur Domoticz expose le Framework Étendu (vérifiez la version\n"
        "    de Domoticz et ses paramètres) — sans cela, le plugin ne démarrera pas,\n"
        "    car 'stable9' ne supporte plus l'ancien modèle de widgets.\n\n"
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
    parser.add_argument("--simulate", dest="simulate", action="store_true", help="Only display the notice (default)")
    parser.add_argument("--no-simulate", dest="simulate", action="store_false", help="Offer to run the switch script after explicit confirmation")
    parser.add_argument("--yes", "-y", dest="yes", action="store_true", help="Skip the interactive confirmation phrase (non-interactive use only)")
    parser.set_defaults(simulate=True)
    args = parser.parse_args()

    display_migration_notice()

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
