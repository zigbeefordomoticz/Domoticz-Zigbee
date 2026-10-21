#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Modules.gitInfos.get_git_infos, which reports the revision the plugin (and,
when installed from a clone, the certified devices database) is running at.

The checkouts are hand-built here as plain files instead of being created with the git
binary: the resolution logic reads the git plumbing files directly, so the tests cover
the exact layouts it has to cope with on a user installation, and need no git at all.

Coverage:
  - a branch checked out with a loose ref
  - a ref only listed in packed-refs (a repository that has been `git gc`-ed)
  - a detached HEAD, holding the object name itself
  - a sha-256 repository (64 character object names)
  - a linked worktree / submodule, whose .git is a file pointing at the real git dir
  - a sub folder of a checkout, resolved from the parent directories
  - a folder which is no checkout at all, a missing folder, and None
  - truncated, empty or non-hexadecimal plumbing files
"""

import pytest

from Modules.gitInfos import get_git_infos

SHA = "9546837da6a0205d139413df1ba7f9d26ca8abfa"
OTHER_SHA = "071ae0758a1e8cbf0e9b37b4d6bb2b8a9c4f1d2e"
SHA256 = "a" * 64


def _make_checkout(root, head, refs=None, packed_refs=None):
    """Create a .git directory holding HEAD, loose refs and an optional packed-refs."""
    git_dir = root / ".git"
    git_dir.mkdir(parents=True)
    (git_dir / "HEAD").write_text(head)

    for name, sha in (refs or {}).items():
        ref_file = git_dir / name
        ref_file.parent.mkdir(parents=True, exist_ok=True)
        ref_file.write_text(sha + "\n")

    if packed_refs is not None:
        (git_dir / "packed-refs").write_text(packed_refs)

    return git_dir


def test_loose_ref_on_a_branch(tmp_path):
    _make_checkout(tmp_path, "ref: refs/heads/stable9\n", refs={"refs/heads/stable9": SHA})
    assert get_git_infos(tmp_path) == {"Commit": SHA, "Branch": "stable9"}


def test_branch_name_keeps_its_slashes(tmp_path):
    _make_checkout(
        tmp_path,
        "ref: refs/heads/fix/legrand-remote-group-endpoint\n",
        refs={"refs/heads/fix/legrand-remote-group-endpoint": SHA},
    )
    assert get_git_infos(tmp_path) == {
        "Commit": SHA,
        "Branch": "fix/legrand-remote-group-endpoint",
    }


def test_packed_ref_when_no_loose_ref_is_left(tmp_path):
    _make_checkout(
        tmp_path,
        "ref: refs/heads/stable9\n",
        packed_refs=(
            "# pack-refs with: peeled fully-peeled sorted \n"
            f"{OTHER_SHA} refs/heads/master\n"
            f"{SHA} refs/heads/stable9\n"
            f"{OTHER_SHA} refs/tags/stable9-9.1.007\n"
            f"^{SHA}\n"
        ),
    )
    assert get_git_infos(tmp_path) == {"Commit": SHA, "Branch": "stable9"}


def test_loose_ref_wins_over_the_packed_one(tmp_path):
    _make_checkout(
        tmp_path,
        "ref: refs/heads/stable9\n",
        refs={"refs/heads/stable9": SHA},
        packed_refs=f"{OTHER_SHA} refs/heads/stable9\n",
    )
    assert get_git_infos(tmp_path)["Commit"] == SHA


def test_detached_head_reports_no_branch(tmp_path):
    _make_checkout(tmp_path, SHA + "\n")
    assert get_git_infos(tmp_path) == {"Commit": SHA, "Branch": None}


def test_sha256_object_name(tmp_path):
    _make_checkout(tmp_path, "ref: refs/heads/main\n", refs={"refs/heads/main": SHA256})
    assert get_git_infos(tmp_path) == {"Commit": SHA256, "Branch": "main"}


@pytest.mark.parametrize("gitdir_is_absolute", [True, False])
def test_worktree_git_file_points_to_the_real_git_dir(tmp_path, gitdir_is_absolute):
    # The repository keeps the branch refs, the worktree only its own HEAD
    repository = tmp_path / "repository"
    git_dir = _make_checkout(repository, "ref: refs/heads/main\n", refs={"refs/heads/main": SHA})

    worktree_git_dir = git_dir / "worktrees" / "wt"
    worktree_git_dir.mkdir(parents=True)
    (worktree_git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (worktree_git_dir / "commondir").write_text("../..\n")

    worktree = tmp_path / "wt"
    worktree.mkdir()
    pointer = str(worktree_git_dir) if gitdir_is_absolute else "../repository/.git/worktrees/wt"
    (worktree / ".git").write_text("gitdir: %s\n" % pointer)

    assert get_git_infos(worktree) == {"Commit": SHA, "Branch": "main"}


def test_worktree_falls_back_on_the_common_packed_refs(tmp_path):
    repository = tmp_path / "repository"
    git_dir = _make_checkout(
        repository, "ref: refs/heads/main\n", packed_refs=f"{SHA} refs/heads/main\n"
    )

    worktree_git_dir = git_dir / "worktrees" / "wt"
    worktree_git_dir.mkdir(parents=True)
    (worktree_git_dir / "HEAD").write_text("ref: refs/heads/main\n")
    (worktree_git_dir / "commondir").write_text("../..\n")

    worktree = tmp_path / "wt"
    worktree.mkdir()
    (worktree / ".git").write_text("gitdir: %s\n" % worktree_git_dir)

    assert get_git_infos(worktree) == {"Commit": SHA, "Branch": "main"}


def test_sub_folder_of_a_checkout_is_resolved(tmp_path):
    _make_checkout(tmp_path, "ref: refs/heads/stable9\n", refs={"refs/heads/stable9": SHA})
    sub_folder = tmp_path / "Modules" / "deeper"
    sub_folder.mkdir(parents=True)
    assert get_git_infos(sub_folder) == {"Commit": SHA, "Branch": "stable9"}


def test_folder_is_accepted_as_a_string(tmp_path):
    _make_checkout(tmp_path, "ref: refs/heads/stable9\n", refs={"refs/heads/stable9": SHA})
    assert get_git_infos(str(tmp_path))["Commit"] == SHA


@pytest.mark.parametrize("folder", [None, ""])
def test_no_folder_given(folder):
    assert get_git_infos(folder) == {"Commit": None, "Branch": None}


def test_folder_which_is_not_a_checkout(tmp_path):
    # The pip installed certified devices database: a plain folder, which is no error
    plain_folder = tmp_path / "site-packages" / "z4d_certified_devices"
    plain_folder.mkdir(parents=True)
    assert get_git_infos(plain_folder) == {"Commit": None, "Branch": None}


def test_missing_folder(tmp_path):
    assert get_git_infos(tmp_path / "gone") == {"Commit": None, "Branch": None}


def test_missing_head(tmp_path):
    (tmp_path / ".git").mkdir()
    assert get_git_infos(tmp_path) == {"Commit": None, "Branch": None}


def test_unresolvable_ref(tmp_path):
    _make_checkout(tmp_path, "ref: refs/heads/stable9\n", packed_refs=f"{SHA} refs/heads/master\n")
    assert get_git_infos(tmp_path) == {"Commit": None, "Branch": "stable9"}


@pytest.mark.parametrize("content", ["", "\n", "abcdef\n", ("z" * 40) + "\n"])
def test_ref_content_which_is_no_object_name(tmp_path, content):
    git_dir = _make_checkout(tmp_path, "ref: refs/heads/stable9\n")
    ref_file = git_dir / "refs" / "heads"
    ref_file.mkdir(parents=True)
    (ref_file / "stable9").write_text(content)
    assert get_git_infos(tmp_path) == {"Commit": None, "Branch": "stable9"}


def test_returned_dict_is_never_the_shared_default(tmp_path):
    # The caller stores the result in pluginParameters, mutating it must not leak
    infos = get_git_infos(tmp_path)
    infos["Commit"] = "mutated"
    assert get_git_infos(tmp_path) == {"Commit": None, "Branch": None}
