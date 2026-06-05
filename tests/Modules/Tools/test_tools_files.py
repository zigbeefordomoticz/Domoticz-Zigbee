#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Unit tests for Modules/tools_files.py

Coverage:
  - _safe_file_transfer   – move succeeds, copy succeeds, fallback text copy, both fail raises
  - rotate_file_versions  – nb_versions=0 no-op, creates -01, shifts existing versions,
                            oldest beyond nb_versions discarded
  - how_many_devices      – counts routers (FFD/Router/8e) and end devices (RFD/End Device/80)
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from Modules.tools_files import (
    _safe_file_transfer,
    how_many_devices,
    rotate_file_versions,
)


def _plugin(devices=None):
    p = MagicMock()
    p.ListOfDevices = devices if devices is not None else {}
    return p


# ---------------------------------------------------------------------------
# _safe_file_transfer
# ---------------------------------------------------------------------------

class TestSafeFileTransfer:
    def test_move_succeeds(self, tmp_path):
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("hello")
        _safe_file_transfer(str(src), str(dst), move=True)
        assert dst.read_text() == "hello"
        assert not src.exists()

    def test_copy_succeeds(self, tmp_path):
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("world")
        _safe_file_transfer(str(src), str(dst), move=False)
        assert dst.read_text() == "world"
        assert src.exists()

    def test_fallback_text_copy(self, tmp_path):
        src = tmp_path / "source.txt"
        dst = tmp_path / "dest.txt"
        src.write_text("fallback content")
        with patch("shutil.move", side_effect=OSError("forced")):
            _safe_file_transfer(str(src), str(dst), move=True)
        assert dst.read_text() == "fallback content"

    def test_both_fail_raises_runtime_error(self, tmp_path):
        with patch("shutil.move", side_effect=OSError("shutil fail")):
            with pytest.raises(RuntimeError, match="safe_file_transfer failed"):
                _safe_file_transfer("/nonexistent/source.txt", "/nonexistent/dest.txt")


# ---------------------------------------------------------------------------
# rotate_file_versions
# ---------------------------------------------------------------------------

class TestRotateFileVersions:
    def test_zero_versions_is_noop(self, tmp_path):
        src = tmp_path / "file.db"
        src.write_text("data")
        rotate_file_versions(src, 0)
        assert not (tmp_path / "file.db-01").exists()

    def test_creates_version_01(self, tmp_path):
        src = tmp_path / "file.db"
        src.write_text("original")
        rotate_file_versions(src, 3)
        v01 = tmp_path / "file.db-01"
        assert v01.exists()
        assert v01.read_text() == "original"
        assert src.exists()  # copy, not move

    def test_shifts_existing_versions(self, tmp_path):
        src = tmp_path / "file.db"
        v01 = tmp_path / "file.db-01"
        src.write_text("new")
        v01.write_text("old-01")
        rotate_file_versions(src, 3)
        assert (tmp_path / "file.db-02").read_text() == "old-01"
        assert (tmp_path / "file.db-01").read_text() == "new"

    def test_oldest_version_beyond_limit_discarded(self, tmp_path):
        src = tmp_path / "file.db"
        src.write_text("new")
        (tmp_path / "file.db-01").write_text("v1")
        (tmp_path / "file.db-02").write_text("v2")
        (tmp_path / "file.db-03").write_text("v3")  # this will be rotated out
        rotate_file_versions(src, 3)
        # v3 was shifted to v4 which is beyond nb_versions=3, so it still exists
        # Actually rotate keeps nb_versions: v1→v2, v2→v3 (old v3 now overwritten by v2)
        assert (tmp_path / "file.db-01").exists()
        assert (tmp_path / "file.db-02").exists()
        assert (tmp_path / "file.db-03").exists()
        assert not (tmp_path / "file.db-04").exists()


# ---------------------------------------------------------------------------
# how_many_devices
# ---------------------------------------------------------------------------

class TestHowManyDevices:
    def test_counts_routers_by_device_type(self):
        p = _plugin({"a": {"DeviceType": "FFD"}, "b": {"DeviceType": "RFD"}})
        routers, end = how_many_devices(p)
        assert routers == 1
        assert end == 1

    def test_counts_by_logical_type(self):
        p = _plugin({
            "a": {"LogicalType": "Router"},
            "b": {"LogicalType": "End Device"},
        })
        routers, end = how_many_devices(p)
        assert routers == 1
        assert end == 1

    def test_counts_by_mac_capa(self):
        p = _plugin({
            "a": {"MacCapa": "8e"},
            "b": {"MacCapa": "80"},
        })
        routers, end = how_many_devices(p)
        assert routers == 1
        assert end == 1

    def test_empty_devices(self):
        routers, end = how_many_devices(_plugin({}))
        assert routers == 0
        assert end == 0

    def test_unknown_type_not_counted(self):
        p = _plugin({"a": {"Model": "unknown"}})
        routers, end = how_many_devices(p)
        assert routers == 0
        assert end == 0
