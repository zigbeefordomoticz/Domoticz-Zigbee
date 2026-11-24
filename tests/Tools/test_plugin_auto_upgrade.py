#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
Tests of Tools/plugin-auto-upgrade-v1.sh and -v2.sh, run for real in a temporary git checkout.

git is the real one. python3, sudo and apt-get are stubs placed first in PATH, so that nothing
is installed on the machine running the tests: the python3 stub records how it was called.

Covered: the outcome of the upgrade when git pull works, fails, or does not apply (no .git).
"""

import os
import shutil
import subprocess  # nosec B404 - runs the scripts under test
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[2] / "Tools"
SCRIPTS = ["plugin-auto-upgrade-v1.sh", "plugin-auto-upgrade-v2.sh"]
NOT_UPDATED = "the plugin code was NOT updated"
COMPLETED = "Plugin upgrade process completed"

pytestmark = pytest.mark.skipif(
    not (shutil.which("bash") and shutil.which("git")), reason="bash and git are required"
)


def _stub(path, body):
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(0o755)


class Sandbox:
    def __init__(self, tmp_path):
        self.tmp = tmp_path
        self.plugin = tmp_path / "plugin"
        self.python_calls = tmp_path / "python-calls.txt"
        home, stubs = tmp_path / "home", tmp_path / "stubs"
        home.mkdir()
        stubs.mkdir()
        _stub(stubs / "python3", 'echo "$*" >> "%s"\nexit 0\n' % self.python_calls)
        _stub(stubs / "sudo", 'exec "$@"\n')
        _stub(stubs / "apt-get", "exit 0\n")

        self.env = {
            "PATH": "%s:%s" % (stubs, os.environ["PATH"]),
            "HOME": str(home),
            "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1",
        }
        for who in ("AUTHOR", "COMMITTER"):
            self.env["GIT_%s_NAME" % who] = "test"
            self.env["GIT_%s_EMAIL" % who] = "test@example.invalid"

        self.upstream = tmp_path / "upstream"
        self.upstream.mkdir()
        self.git(self.upstream, "init", "-q", "-b", "stable9")
        (self.upstream / "Tools").mkdir()
        for script in SCRIPTS:
            shutil.copy(TOOLS / script, self.upstream / "Tools" / script)
        (self.upstream / "requirements.txt").write_text("# none\n")
        self.publish("version 1")
        self.git(tmp_path, "clone", "-q", "-b", "stable9", str(self.upstream), str(self.plugin))

    def git(self, cwd, *args):
        subprocess.run(["git", "-C", str(cwd), *args], env=self.env, check=True, capture_output=True)  # nosec B603 B607

    def publish(self, content):
        (self.upstream / "plugin.py").write_text(content)
        self.git(self.upstream, "add", "-A")
        self.git(self.upstream, "commit", "-q", "-m", content)

    def upgrade(self, script, **extra_env):
        return subprocess.run(  # nosec B603 B607
            ["bash", "Tools/" + script], cwd=self.plugin, env={**self.env, **extra_env},
            capture_output=True, text=True,
        )

    @property
    def code(self):
        return (self.plugin / "plugin.py").read_text()

    @property
    def modules_upgraded(self):
        return "install -r requirements.txt" in self.python_calls.read_text()


@pytest.fixture
def sandbox(tmp_path):
    return Sandbox(tmp_path)


@pytest.fixture
def failing_pull(sandbox):
    """A new version changes plugin.py, which was also edited locally: git refuses the pull."""
    sandbox.publish("version 2")
    (sandbox.plugin / "plugin.py").write_text("local change")
    return sandbox


@pytest.mark.parametrize("script", SCRIPTS)
class TestGitPullOutcome:
    @pytest.mark.parametrize("strict", ["", "1"])
    def test_pull_ok_is_a_success(self, sandbox, script, strict):
        sandbox.publish("version 2")
        result = sandbox.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL=strict)

        assert result.returncode == 0
        assert COMPLETED.lower() in result.stdout.lower()
        assert NOT_UPDATED not in result.stdout
        assert sandbox.code == "version 2"
        assert sandbox.modules_upgraded

    def test_failed_pull_is_reported_and_fails_for_the_webui(self, failing_pull, script):
        result = failing_pull.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL="1")

        assert result.returncode == 10
        assert COMPLETED.lower() not in result.stdout.lower()
        # The reason given by git comes after the message, at the end of the output
        assert "would be overwritten by merge" in result.stdout.split(NOT_UPDATED)[1]

    def test_failed_pull_keeps_exit_code_0_by_default(self, failing_pull, script):
        # customstart.sh runs the upgrade again, three times, on any other exit code
        result = failing_pull.upgrade(script)

        assert result.returncode == 0
        assert NOT_UPDATED in result.stdout
        assert COMPLETED.lower() not in result.stdout.lower()

    def test_failed_pull_still_upgrades_the_modules_and_keeps_local_changes(self, failing_pull, script):
        failing_pull.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL="1")

        assert failing_pull.modules_upgraded
        assert failing_pull.code == "local change"

    def test_missing_pack_files_are_a_failed_pull(self, sandbox, script):
        # What is left when the user deletes .git/objects/pack/*
        sandbox.git(sandbox.plugin, "gc", "-q")
        for pack in (sandbox.plugin / ".git" / "objects" / "pack").iterdir():
            pack.unlink()
        sandbox.publish("version 2")

        result = sandbox.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL="1")

        assert result.returncode == 10
        assert NOT_UPDATED in result.stdout
        assert sandbox.modules_upgraded

    def test_folder_without_git_is_a_success(self, sandbox, script):
        # Installed from a release (PyPluginStore, zip): there is nothing to pull
        (sandbox.plugin / ".git").rename(sandbox.tmp / "no-git")

        result = sandbox.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL="1")

        assert result.returncode == 0
        assert "not a git checkout" in result.stdout
        assert NOT_UPDATED not in result.stdout
        assert sandbox.modules_upgraded


@pytest.mark.parametrize("script", SCRIPTS)
@pytest.mark.parametrize("in_docker", [True, False])
def test_pull_rebase_is_set_in_docker_only(sandbox, script, in_docker):
    # Replace what is_docker() looks for by a file the test controls
    marker = sandbox.tmp / "dockerenv"
    if in_docker:
        marker.touch()
    path = sandbox.plugin / "Tools" / script
    content = path.read_text()
    assert "/.dockerenv" in content and "/.dockerinit" in content
    path.write_text(content.replace("/.dockerenv", str(marker)).replace("/.dockerinit", str(marker)))

    sandbox.upgrade(script)

    gitconfig = (Path(sandbox.env["HOME"]) / ".gitconfig").read_text()
    assert ("rebase = false" in gitconfig) is in_docker


@pytest.mark.parametrize("script", SCRIPTS)
def test_branch_deleted_upstream_does_not_block_the_pull(tmp_path, script):
    sandbox = Sandbox(tmp_path)
    sandbox.git(sandbox.upstream, "branch", "topic")
    sandbox.git(sandbox.plugin, "fetch", "-q")
    sandbox.git(sandbox.upstream, "branch", "-D", "topic")
    sandbox.git(sandbox.upstream, "branch", "topic/new")
    sandbox.publish("version 2")

    result = sandbox.upgrade(script, Z4D_UPGRADE_FAIL_ON_GIT_PULL="1")

    assert result.returncode == 0
    assert sandbox.code == "version 2"
    remotes = sandbox.plugin / ".git" / "refs" / "remotes" / "origin"
    assert not (remotes / "topic").is_file()


@pytest.mark.parametrize("script", SCRIPTS)
def test_local_branches_and_tags_are_kept(sandbox, script):
    sandbox.git(sandbox.plugin, "branch", "my-branch")
    sandbox.git(sandbox.plugin, "tag", "my-tag")

    sandbox.upgrade(script)

    sandbox.git(sandbox.plugin, "rev-parse", "--verify", "refs/heads/my-branch")
    sandbox.git(sandbox.plugin, "rev-parse", "--verify", "refs/tags/my-tag")
