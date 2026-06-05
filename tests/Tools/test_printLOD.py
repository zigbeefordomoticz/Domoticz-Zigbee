#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for Tools/printLOD.py

Coverage:
  - process_file – basic device entry, Ep sub-dict rendering, empty lines skipped
"""

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).parents[2] / "Tools" / "printLOD.py"

spec = importlib.util.spec_from_file_location("printLOD", SCRIPT_PATH)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

process_file = mod.process_file


class TestProcessFile:
    def _write_device_list(self, tmp_path, content: str) -> Path:
        p = tmp_path / "DeviceList.txt"
        p.write_text(content)
        return p

    def test_simple_entry_printed(self, tmp_path, capsys):
        content = " '1234' : {'IEEE': 'aabbccdd', 'Model': 'TS0001'}\n"
        f = self._write_device_list(tmp_path, content)
        process_file(str(f))
        out = capsys.readouterr().out
        assert "1234" in out
        assert "IEEE" in out

    def test_ep_dict_rendered(self, tmp_path, capsys):
        ep = "{'01': {'0006': '00', 'ClusterType': {'1': 'Switch'}}}"
        content = f" '5678' : {{'Ep': {ep}, 'Model': 'test'}}\n"
        f = self._write_device_list(tmp_path, content)
        process_file(str(f))
        out = capsys.readouterr().out
        assert "Ep" in out
        assert "01" in out

    def test_empty_lines_skipped(self, tmp_path, capsys):
        content = "\n\n '9999' : {'IEEE': 'ff'}\n\n"
        f = self._write_device_list(tmp_path, content)
        process_file(str(f))
        out = capsys.readouterr().out
        assert "9999" in out

    def test_separator_printed(self, tmp_path, capsys):
        content = " '0001' : {'IEEE': '11'}\n"
        f = self._write_device_list(tmp_path, content)
        process_file(str(f))
        out = capsys.readouterr().out
        assert "======" in out

    def test_multiple_entries(self, tmp_path, capsys):
        content = (
            " '0001' : {'IEEE': 'aa'}\n"
            " '0002' : {'IEEE': 'bb'}\n"
        )
        f = self._write_device_list(tmp_path, content)
        process_file(str(f))
        out = capsys.readouterr().out
        assert "0001" in out
        assert "0002" in out
