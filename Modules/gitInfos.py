#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2025
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""Resolve the git revision a folder has been checked out at.

Used to report, along with the plugin version and the certified devices database version,
which exact commit is running. Issue reports then carry the revision and not only the
release number, which matters when a user runs a branch, a dirty checkout, or a commit
pushed after the release tag was cut.

The revision is read straight from the git plumbing files (HEAD, refs, packed-refs) rather
than by running the git binary: no subprocess, no git executable required, and nothing that
could block for an unpredictable amount of time.

A folder which is not a git checkout (the regular case for the certified devices database,
installed as a pip package) is not an error: both keys are then returned as None.
"""

from pathlib import Path

GIT_INFOS_UNKNOWN = {"Commit": None, "Branch": None}

# A git object name is 40 hexadecimal characters (sha-1), or 64 with sha-256 repositories.
SHA_LENGTHS = (40, 64)


def get_git_infos(folder):
    """Return {"Commit": <full hash>, "Branch": <branch name>} for the checkout holding folder.

    Parameters:
        folder (str | Path | None): any folder of the checkout, usually its root.

    Returns:
        dict: "Commit" is the full object name of HEAD, "Branch" the checked out branch, or
              None for a detached HEAD. Both are None when the revision cannot be resolved.
    """
    if not folder:
        return dict(GIT_INFOS_UNKNOWN)

    try:
        git_dir = _locate_git_dir(Path(folder))
        if git_dir is None:
            return dict(GIT_INFOS_UNKNOWN)

        head = _read_text(git_dir / "HEAD")
        if head is None:
            return dict(GIT_INFOS_UNKNOWN)

        if not head.startswith("ref:"):
            # Detached HEAD, holding the object name itself
            return {"Commit": _valid_sha(head), "Branch": None}

        reference = head[len("ref:"):].strip()
        return {"Commit": _resolve_reference(git_dir, reference), "Branch": _branch_name(reference)}

    except OSError:
        return dict(GIT_INFOS_UNKNOWN)


def _locate_git_dir(folder):
    """Return the git dir of the checkout holding folder, or None if there is none."""
    for candidate in (folder, *folder.parents):
        git_path = candidate / ".git"
        if git_path.is_dir():
            return git_path

        if git_path.is_file():
            # Worktree or submodule: the .git file points to the real git dir
            content = _read_text(git_path) or ""
            if content.startswith("gitdir:"):
                git_dir = Path(content[len("gitdir:"):].strip())
                return git_dir if git_dir.is_absolute() else (candidate / git_dir).resolve()

    return None


def _resolve_reference(git_dir, reference):
    """Return the object name a reference points to, looking at loose then packed refs."""
    loose_reference = _read_text(git_dir / reference)
    if loose_reference is not None:
        return _valid_sha(loose_reference)

    # A linked worktree keeps the branch refs in the common git dir of the repository
    common_dir = _read_text(git_dir / "commondir")
    if common_dir:
        common_path = Path(common_dir)
        if not common_path.is_absolute():
            common_path = (git_dir / common_path).resolve()
        loose_reference = _read_text(common_path / reference)
        if loose_reference is not None:
            return _valid_sha(loose_reference)
        return _packed_reference(common_path, reference)

    return _packed_reference(git_dir, reference)


def _packed_reference(git_dir, reference):
    """Return the object name reference has in packed-refs, or None if not listed."""
    packed_refs = _read_text(git_dir / "packed-refs")
    if packed_refs is None:
        return None

    for line in packed_refs.splitlines():
        if not line or line[0] in "#^":
            continue
        sha, _, packed_name = line.partition(" ")
        if packed_name.strip() == reference:
            return _valid_sha(sha)

    return None


def _branch_name(reference):
    """Return the branch name of a refs/heads/ reference, or the reference itself."""
    prefix = "refs/heads/"
    return reference[len(prefix):] if reference.startswith(prefix) else reference or None


def _valid_sha(candidate):
    """Return candidate when it looks like a git object name, None otherwise."""
    sha = (candidate or "").strip()
    if len(sha) in SHA_LENGTHS:
        try:
            int(sha, 16)
        except ValueError:
            return None
        return sha

    return None


def _read_text(filename):
    """Return the stripped content of filename, or None when it cannot be read."""
    try:
        return filename.read_text(encoding="utf-8", errors="replace").strip()
    except (OSError, ValueError):
        return None
