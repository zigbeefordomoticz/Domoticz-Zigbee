#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unit tests for Classes.TransportStats trend points (sent by /plugin-stat as "Trend").

Rxps / Txps are averages since the plugin started, rounded to 0.01 message/s, so no
real rate can be derived from them: after two hours the rounding alone is worth about
36 messages per point. Each point therefore also carries RxCount / TxCount, the
messages received / sent since the previous point, and Time, its epoch, so that the
WebUI can draw messages per minute. TREND_REST_FIELDS is what rest_plugin_stat copies.
"""

from unittest.mock import MagicMock

import pytest

import Classes.TransportStats as transport_stats
from Classes.TransportStats import (MAX_TREND_STAT_TABLE, TREND_REST_FIELDS,
                                    TransportStatistics)

START = 1_000_000.0


@pytest.fixture
def clock(monkeypatch):
    """A controllable time.time() for Classes.TransportStats."""
    now = {"t": START}
    monkeypatch.setattr(transport_stats.time, "time", lambda: now["t"])
    return now


@pytest.fixture
def stats(clock):
    return TransportStatistics(pluginconf=MagicMock(), log=MagicMock(), zigbee_communication="zigpy")


def _tick(stats, clock, seconds=5, received=0, sent=0, timestamp=1):
    clock["t"] += seconds
    stats._received += received
    stats._sent += sent
    stats.addPointforTrendStats(timestamp)
    return stats.TrendStats[-1]


class TestIntervalCounts:
    def test_first_point_counts_since_start(self, stats, clock):
        point = _tick(stats, clock, received=12, sent=3)
        assert point["RxCount"] == 12
        assert point["TxCount"] == 3

    def test_each_point_counts_only_its_own_interval(self, stats, clock):
        _tick(stats, clock, received=12, sent=3)
        point = _tick(stats, clock, received=7, sent=1, timestamp=2)
        assert point["RxCount"] == 7
        assert point["TxCount"] == 1

    def test_quiet_interval_is_zero(self, stats, clock):
        _tick(stats, clock, received=5, sent=5)
        point = _tick(stats, clock, timestamp=2)
        assert (point["RxCount"], point["TxCount"]) == (0, 0)

    def test_counter_going_backwards_is_not_a_negative_rate(self, stats, clock):
        _tick(stats, clock, received=50, sent=20)
        stats._received, stats._sent = 10, 5
        point = _tick(stats, clock, timestamp=2)
        assert (point["RxCount"], point["TxCount"]) == (0, 0)

    def test_two_points_in_the_same_heartbeat_do_not_count_twice(self, stats, clock):
        """checkHealth's busy check and the pairing-mode flag can both add a point."""
        _tick(stats, clock, received=8, sent=2)
        point = _tick(stats, clock, seconds=0, timestamp=1)
        assert (point["RxCount"], point["TxCount"]) == (0, 0)


class TestTime:
    def test_time_is_the_epoch_of_the_point(self, stats, clock):
        point = _tick(stats, clock, seconds=5)
        assert point["Time"] == START + 5

    def test_time_follows_the_real_interval(self, stats, clock):
        first = _tick(stats, clock, seconds=5)
        second = _tick(stats, clock, seconds=7, timestamp=2)
        assert second["Time"] - first["Time"] == 7


class TestBackwardCompatibility:
    def test_existing_fields_unchanged(self, stats, clock):
        stats._Load = 3
        point = _tick(stats, clock, seconds=10, received=20, sent=5, timestamp=42)
        assert point["_TS"] == 42
        assert point["Rxps"] == 2.0
        assert point["Txps"] == 0.5
        assert point["Load"] == 3

    def test_table_still_holds_the_last_120_points(self, stats, clock):
        for i in range(MAX_TREND_STAT_TABLE + 10):
            _tick(stats, clock, received=1, timestamp=i)
        assert len(stats.TrendStats) == MAX_TREND_STAT_TABLE
        assert all(point["RxCount"] == 1 for point in stats.TrendStats)


class TestRestFields:
    def test_every_rest_field_is_on_the_point(self, stats, clock):
        point = _tick(stats, clock)
        assert all(field in point for field in TREND_REST_FIELDS)

    def test_rest_fields_include_the_interval_counts_and_time(self):
        assert {"Rxps", "Txps", "Load", "Time", "RxCount", "TxCount"} <= set(TREND_REST_FIELDS)
