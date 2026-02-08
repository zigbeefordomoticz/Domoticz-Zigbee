#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tools.check_python_and_branch

Small helper that displays the system's Python 3 version and prints a
clear bilingual (English/French) message about branch support and the
requirement for the `stable8` branch.

The script will try to call the external `python3` executable (if
available) to show what version `python3` points to on the system. It
also inspects the interpreter running the script as a fallback.

Usage:

    python Tools/check_python_and_branch.py

The printed message (English then French) explains that the current
branch is not supported and instructs the user to switch to
`stable8` when their Python is 3.11 or above. If the requirement is
fulfilled the script prints the tip to run
`Tools/plugin-switch-stable8.sh` to perform the switch.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from typing import Optional, Tuple


def _parse_version_from_string(version_output: str) -> Optional[Tuple[int, int, int]]:
    """Parse a Python version string and return (major, minor, patch).

    Accepts strings like "Python 3.11.4" or full sys.version lines. If
    parsing fails returns None.
    """
    if not version_output:
        return None
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", version_output)
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3) or 0)
    return (major, minor, patch)


def get_system_python3_version() -> Optional[Tuple[int, int, int]]:
    """Return the version tuple for the external `python3` executable if found.

    Uses `python3 --version`. If the executable is not available or the
    call fails, returns None.
    """
    try:
        completed = subprocess.run(["python3", "--version"], capture_output=True, text=True, check=False)
        output = completed.stdout.strip() or completed.stderr.strip()
        return _parse_version_from_string(output)
    except (FileNotFoundError, OSError):
        return None


def get_running_python_version() -> Tuple[int, int, int]:
    """Return the running interpreter version as a (major, minor, patch) tuple."""
    vi = sys.version_info
    return (vi.major, vi.minor, vi.micro)


def display_version_and_message(min_major: int = 3, min_minor: int = 11, simulate: bool = True) -> bool:
    """Display python3 versions and a bilingual message about branch support.

    Prints the external `python3` version (if available) and the version
    of the interpreter running this script. Then prints an English and
    French text informing the user that the branch is no longer
    supported and that `stable8` requires Python 3.11 or newer. If the
    requirement is satisfied the function also prints the command to
    run the tool script to switch.
    simulate: if True the function will only suggest the switch command
        and will not attempt to run any destructive action. Defaults to True.
    Returns:
        bool: True when the minimum requirement is met by either the
        external `python3` or the running interpreter.
    """
    external = get_system_python3_version()
    running = get_running_python_version()

    print("System python3:", external if external is not None else "(no external python3 detected)")
    print("Running interpreter:", running)
    print()

    english = (
        "This branch is no longer supported. If you want to benefit from "
        "plugin evolution, you must switch to the 'stable8' branch.\n"
        "The 'stable8' branch requires Python 3.11 or above."
    )

    french = (
        "Cette branche n'est plus supportée. Si vous souhaitez bénéficier "
        "de l'évolution du plugin, vous devez passer à la branche 'stable8'.\n"
        "La branche 'stable8' nécessite Python 3.11 ou une version supérieure."
    )
    
    dutch = (
        "Deze branch wordt niet langer ondersteund. Als u wilt profiteren van "
        "de evolutie van de plugin, moet u overschakelen naar de 'stable8' branch.\n"
        "De 'stable8' branch vereist Python 3.11 of hoger."
    )
    
    spanish = (
        "Esta rama ya no es compatible. Si desea beneficiarse de la evolución "
        "del complemento, debe cambiar a la rama 'stable8'.\n"
        "La rama 'stable8' requiere Python 3.11 o superior."
    )

    print("English:\n" + english + "\n")
    print("Français:\n" + french + "\n")
    print("Nederlands:\n" + dutch + "\n")
    print("Español:\n" + spanish + "\n")

    # Decide whether requirement is met by either external python3 or running interpreter
    requirement_met = False
    for v in (external, running):
        if v is None:
            continue
        maj, minv, _ = v
        if maj > min_major or (maj == min_major and minv >= min_minor):
            requirement_met = True
            break

    if requirement_met:
        print("Requirement satisfied.")
        if simulate:
            print("Dry-run: to switch to the supported branch run (manual):")
        else:
            print("You may run the following command to switch to the supported branch:")
        print("    Tools/plugin-switch-stable8.sh")
    else:
        print("Requirement not satisfied: you need Python %s.%s or newer to switch to 'stable8'." % (min_major, min_minor))

    return requirement_met


def main() -> None:
    """CLI entry point for the module.

    Adds two command-line options:
    --min-version MAJOR.MINOR   : override the minimum required Python version
    --simulate                   : perform a safe dry-run (default)
    --no-simulate                : allow the tool to indicate non-dry suggestions
    """
    parser = argparse.ArgumentParser(description="Check python3 version and branch support for stable8")
    parser.add_argument("--min-version", type=str, default="3.11", help="Minimum required Python version, e.g. 3.11")
    parser.add_argument("--simulate", dest="simulate", action="store_true", help="Do not perform any destructive action (default)")
    parser.add_argument("--no-simulate", dest="simulate", action="store_false", help="Allow non-dry suggestions")
    parser.add_argument("--yes", "-y", dest="yes", action="store_true", help="Assume yes for confirmation prompts")
    parser.set_defaults(simulate=True)
    args = parser.parse_args()

    # parse min-version
    mv = args.min_version.split(".")
    try:
        maj = int(mv[0])
        minv = int(mv[1]) if len(mv) > 1 else 0
    except Exception:
        print("Invalid --min-version value. Use MAJOR.MINOR (e.g. 3.11).")
        raise

    req_met = display_version_and_message(min_major=maj, min_minor=minv, simulate=args.simulate)

    # If requirement is met and we're not in simulate mode, offer to run the switch
    if req_met and not args.simulate:
        switch_script = "Tools/plugin-switch-stable8.sh"
        if not args.yes:
            try:
                answer = input(f"Do you want to run '{switch_script}' now to switch branches? [y/N]: ")
            except EOFError:
                answer = ""
            if answer.strip().lower() not in ("y", "yes"):
                print("Aborted by user. No changes made.")
                return

        # Run the switch script
        try:
            print(f"Running {switch_script} ...")
            completed = subprocess.run(["bash", switch_script], check=False)
            if completed.returncode == 0:
                print("Branch switch script completed successfully.")
            else:
                print(f"Branch switch script exited with code {completed.returncode}.")
        except FileNotFoundError:
            print(f"Switch script not found: {switch_script}")
        except Exception as e:
            print(f"Error while running switch script: {e}")


if __name__ == "__main__":
    main()
