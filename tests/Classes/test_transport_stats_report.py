#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.TransportStats.writeReport, called by onStop.

pluginReports is built by Classes/PluginConf.py with pathlib, so it has no trailing
separator: the report must be joined as a path, not concatenated as a string, or it
lands next to the Reports folder as ReportsTransport-stats.json.
"""

import json
from unittest.mock import MagicMock

from Classes.TransportStats import TransportStatistics


def _stats(reports_dir):
    pluginconf = MagicMock()
    pluginconf.pluginConf = {"pluginReports": str(reports_dir)}
    return TransportStatistics(pluginconf=pluginconf, log=MagicMock(), zigbee_communication="zigpy")


def test_report_is_written_inside_the_reports_folder(tmp_path):
    reports = tmp_path / "Reports"
    reports.mkdir()

    _stats(reports).writeReport()

    assert (reports / "Transport-stats.json").is_file()
    assert not (tmp_path / "ReportsTransport-stats.json").exists()


def test_each_stop_appends_one_report(tmp_path):
    stats = _stats(tmp_path)
    stats._sent, stats._received = 4, 9

    stats.writeReport()
    stats.writeReport()

    lines = [line for line in (tmp_path / "Transport-stats.json").read_text().splitlines() if line]
    assert len(lines) == 2
    report = next(iter(json.loads(lines[-1]).values()))
    assert (report["sent"], report["received"]) == (4, 9)
