#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2024
#
# Initial authors: zaraki673 & pipiche38
#
# SPDX-License-Identifier:    GPL-3.0 license

"""
supervisor.py — HA-grade asyncio supervisor for the Zigbee stack.

Runs entirely inside the event loop created by zigpy_thread_function.
Nothing here touches Domoticz directly — all cross-thread communication
goes through ZigpyTransport attributes (queues, plain bools, monotonic
timestamps) which are safe under the GIL.

Public symbols consumed by the rest of the package:
  _supervisor             — long-lived asyncio task, lifecycle owner
  zigpy_heartbeat_activity — called from AppGeneric.packet_received()
  _cleanup                — called from zigpy_thread_function finally-block

Internal symbols (single-underscore):
  _prepare_for_restart    — state reset between cycles
  _run_zigbee_stack       — one-cycle run (start + watchdog + shutdown gate)
  _watchdog               — health monitor / startup-timeout detector
  _maybe_reset_radio      — last-resort adapter power-cycle helper
"""

import asyncio
import contextlib
import queue
import time

from Classes.ZigpyTransport.radioStart import start_zigpy_task

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEAD_STACK_THRESHOLD       = 240   # seconds without heartbeat → stack DEAD
STARTUP_TIMEOUT            = 120   # seconds to receive the first heartbeat
WATCH_DG_HEARTBEAT_INTERVAL = 30   # poll interval inside _watchdog
MAX_RESTARTS_PER_HOUR      = 5     # circuit-breaker threshold


# ---------------------------------------------------------------------------
# Heartbeat (called from AppGeneric, outside the supervisor)
# ---------------------------------------------------------------------------

def zigpy_heartbeat_activity(self):
    """
    Records Zigbee traffic to indicate the stack is alive.

    Called from AppGeneric.packet_received() via the zigpy_running_ref
    back-reference.  Updates both _last_activity and _last_heartbeat so
    the watchdog can measure liveness without a separate timer task.

    Note: self here is the ZigpyTransport instance, NOT the App object.
    """
    if self.zigpy_loop is None:
        return
    now = self.zigpy_loop.time()
    self._last_activity  = now
    self._last_heartbeat = now


# ---------------------------------------------------------------------------
# Supervisor
# ---------------------------------------------------------------------------

async def _supervisor(self):
    """
    High-level lifecycle supervisor for the Zigbee stack.

    Implements a resilient restart strategy similar to Home Assistant / ZHA.

    Responsibilities:
        - Start and monitor the Zigbee stack lifecycle
        - Detect crash or abnormal exit conditions
        - Apply exponential backoff between restarts
        - Track stack health state transitions
        - Trigger optional radio recovery after repeated failures
        - Escalate to a full plugin restart if the circuit breaker trips

    State transitions:
        STARTING → RUNNING → (EXIT | CRASHED) → RESTARTING

    Restart policy:
        - Exponential backoff: 2 s → 4 s → … → 60 s (capped)
        - Radio recovery hook after every 5th consecutive restart
        - Circuit breaker: escalate to plugin restart after MAX_RESTARTS_PER_HOUR
          restarts within a rolling 1-hour window

    Exit conditions:
        - _zigpy_stop_requested is True  (external stop via stop_zigpy_thread)
        - Circuit breaker tripped and plugin restart was requested

    Design note — why _zigpy_stop_requested instead of _shutdown_event:
        _run_zigbee_stack() *always* calls _shutdown_event.set() before it
        returns, so that all intra-cycle tasks cancel cleanly.  If the
        supervisor tested _shutdown_event it would exit after the very first
        run and never restart.  _zigpy_stop_requested is a plain bool set
        only by stop_zigpy_thread(), allowing the supervisor to distinguish
        a genuine external shutdown from an internal restart trigger.
        A fresh asyncio.Event is created at the start of every cycle so
        a stale set() from a previous run cannot bleed through.
    """
    self.log.logging("TransportZigpy", "Debug", "Supervisor started")

    restart_delay = 2

    while not self._zigpy_stop_requested:

        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"Supervisor: starting cycle #{self._restart_count} "
            f"(consecutive_failures={self._consecutive_failures}, "
            f"restart_delay={restart_delay}s, stop_requested={self._zigpy_stop_requested})"
        )

        # Fresh event for this cycle — prevents a stale set() from a previous
        # cycle prematurely ending the next run.
        self._shutdown_event = asyncio.Event()

        # Reset liveness so the watchdog startup window is accurate.
        self._last_heartbeat = None

        await _prepare_for_restart(self)

        run_start = self.zigpy_loop.time()
        self.log.logging("TransportZigpyStack", "Debug",
                         f"Supervisor: entering _run_zigbee_stack (cycle #{self._restart_count})")

        try:
            self._stack_health = "STARTING"
            await _run_zigbee_stack(self)
            self.log.logging("TransportZigpy", "Debug", "Zigbee stack exited")

        except Exception as e:
            self.log.logging("TransportZigpy", "Error", f"Zigbee crash: {e}")
            self._stack_health = "CRASHED"

        run_duration = self.zigpy_loop.time() - run_start
        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"Supervisor: _run_zigbee_stack returned after {run_duration:.1f}s, "
            f"health={self._stack_health}, stop_requested={self._zigpy_stop_requested}"
        )

        if self._zigpy_stop_requested:
            self.log.logging("TransportZigpy", "Debug",
                             "Supervisor: stop requested — not restarting")
            break

        # --- restart / recovery logic ----------------------------------------

        self._restart_count += 1
        self._consecutive_failures += 1

        # Stability reset: a run > 5 min is considered a transient event.
        if run_duration > 300:
            self.log.logging(
                "TransportZigpy", "Debug",
                f"Supervisor: stack was stable for {run_duration:.0f}s "
                f"— resetting backoff and failure counter"
            )
            restart_delay = 2
            self._consecutive_failures = 0

        # Circuit breaker: rolling 1-hour restart count.
        now = time.monotonic()
        self._restart_timestamps = [ts for ts in self._restart_timestamps
                                    if now - ts < 3600]
        self._restart_timestamps.append(now)

        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"Supervisor: circuit-breaker count="
            f"{len(self._restart_timestamps)}/{MAX_RESTARTS_PER_HOUR} in last hour"
        )

        if len(self._restart_timestamps) >= MAX_RESTARTS_PER_HOUR:
            self.log.logging(
                "TransportZigpy", "Error",
                f"Supervisor: {MAX_RESTARTS_PER_HOUR} restarts in 1 h "
                f"— escalating to plugin restart"
            )
            if callable(getattr(self, "restart_plugin", None)):
                self.restart_plugin()
            break

        # Radio recovery after repeated consecutive failures.
        if self._consecutive_failures > 0 and self._consecutive_failures % 5 == 0:
            self.log.logging(
                "TransportZigpy", "Error",
                f"Supervisor: {self._consecutive_failures} consecutive failures "
                f"— attempting radio recovery"
            )
            await _maybe_reset_radio(self)

        self.log.logging(
            "TransportZigpy", "Debug",
            f"Supervisor: restarting in {restart_delay}s "
            f"(attempt #{self._restart_count}, consecutive={self._consecutive_failures})"
        )
        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"Supervisor: sleeping {restart_delay}s before next cycle "
            f"(next restart_delay will be {min(restart_delay * 2, 60)}s)"
        )
        await asyncio.sleep(restart_delay)
        restart_delay = min(restart_delay * 2, 60)

    self.log.logging("TransportZigpy", "Debug", "Supervisor exiting — stopping event loop")
    asyncio.get_running_loop().stop()


# ---------------------------------------------------------------------------
# Pre-restart state cleanup
# ---------------------------------------------------------------------------

async def _prepare_for_restart(self):
    """
    Reset volatile state before a supervised restart.

    Called by _supervisor at the start of every cycle.  Ensures that a
    crash or timeout in the previous run does not leave dangling resources
    (open serial port, stale commands, locked semaphores) visible to the
    next start_zigpy_task invocation.

    Safe to call on the very first cycle (all attributes are None / empty).
    """
    if self.app is not None:
        self.log.logging("TransportZigpyStack", "Debug",
                         "_prepare_for_restart: app still set — force-disconnecting")
        with contextlib.suppress(Exception):
            await asyncio.wait_for(self.app.disconnect(), timeout=5.0)
        self.app = None
        self.log.logging("TransportZigpyStack", "Debug",
                         "_prepare_for_restart: force-disconnect done")
    else:
        self.log.logging("TransportZigpyStack", "Debug",
                         "_prepare_for_restart: app is None, no disconnect needed")

    # Fresh queue — stale pre-crash commands must not be replayed.
    self.writer_queue = queue.Queue()
    self.log.logging("TransportZigpyStack", "Debug",
                     "_prepare_for_restart: fresh writer_queue created")

    # Semaphores from the previous run are invalid after a restart.
    self._concurrent_requests_semaphores_list.clear()
    self._currently_waiting_requests_list.clear()
    self._currently_not_reachable.clear()

    self.zigpy_running = False
    self.log.logging("TransportZigpyStack", "Debug",
                     "_prepare_for_restart: state reset complete")


# ---------------------------------------------------------------------------
# One-cycle stack runner
# ---------------------------------------------------------------------------

async def _run_zigbee_stack(self):
    """
    Run the Zigbee stack as a set of concurrent tasks for one lifecycle.

    Starts three tasks in parallel:
        zigbee_task   — the main radio loop (start_zigpy_task)
        watchdog_task — health monitor and hard-failure detector
        shutdown_task — waits for the external _shutdown_event signal

    Returns as soon as *any* of them finishes (FIRST_COMPLETED), then
    sets _shutdown_event, cancels the remaining lifecycle tasks, and
    cancels any stray application tasks (unicast-send, topology-scan, …).

    The supervisor treats any return from this coroutine as a signal to
    restart, unless _zigpy_stop_requested is set.

    Safety note on stray task cleanup:
        asyncio.current_task() inside this coroutine is the _supervisor task
        itself (coroutines share their enclosing task), so it is
        automatically excluded from the cancel sweep.
    """
    self.log.logging("TransportZigpy", "Debug", "_run_zigbee_stack starting")

    zigbee_task   = asyncio.create_task(start_zigpy_task(self, channel=0, extended_pan_id=0))
    shutdown_task = asyncio.create_task(self._shutdown_event.wait())
    watchdog_task = asyncio.create_task(_watchdog(self))

    done, pending = await asyncio.wait(
        {zigbee_task, shutdown_task, watchdog_task},
        return_when=asyncio.FIRST_COMPLETED,
    )

    self.log.logging("TransportZigpyStack", "Debug",
                     "_run_zigbee_stack - one task completed, initiating shutdown sequence")

    task_names = {
        zigbee_task:   "zigbee_task",
        shutdown_task: "shutdown_task",
        watchdog_task: "watchdog_task",
    }
    for _t in done:
        exc = None
        with contextlib.suppress(Exception):
            exc = _t.exception()
        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"_run_zigbee_stack: '{task_names.get(_t, _t.get_name())}' completed "
            f"(cancelled={_t.cancelled()}, exception={exc!r})"
        )

    self._shutdown_event.set()

    for task in pending:
        task.cancel()
    await asyncio.gather(*pending, return_exceptions=True)

    # Cancel any stray application tasks spawned during this cycle.
    # asyncio.current_task() == supervisor task → excluded automatically.
    lifecycle_tasks = {zigbee_task, shutdown_task, watchdog_task}
    stray = [
        t for t in asyncio.all_tasks()
        if t is not asyncio.current_task() and t not in lifecycle_tasks
    ]
    if stray:
        self.log.logging(
            "TransportZigpyStack", "Debug",
            f"_run_zigbee_stack: cancelling {len(stray)} stray task(s): "
            f"{[t.get_name() for t in stray]}"
        )
        for t in stray:
            t.cancel()
        await asyncio.gather(*stray, return_exceptions=True)

    self.log.logging("TransportZigpyStack", "Debug", "_run_zigbee_stack ending")


# ---------------------------------------------------------------------------
# Watchdog
# ---------------------------------------------------------------------------

async def _watchdog(self):
    """
    Combined health monitor and startup-timeout detector.

    Health states (updates self._stack_health):
        ALIVE   — last heartbeat < 30 s ago
        IDLE    — last heartbeat 30–120 s ago
        SUSPECT — last heartbeat 120 s – DEAD_STACK_THRESHOLD ago
        DEAD    — last heartbeat > DEAD_STACK_THRESHOLD s ago

    Restart triggers:
        1. No heartbeat within STARTUP_TIMEOUT seconds of cycle start.
        2. Heartbeat gap exceeds DEAD_STACK_THRESHOLD (hard failure).

    Logging: state transitions only — no per-tick log spam.
    Poll interval: WATCH_DG_HEARTBEAT_INTERVAL seconds.
    """
    self.log.logging("TransportZigpy", "Debug", "Watchdog started")

    loop = self.zigpy_loop
    startup_deadline = loop.time() + STARTUP_TIMEOUT
    _prev_health = self._stack_health

    while not self._shutdown_event.is_set():
        await asyncio.sleep(WATCH_DG_HEARTBEAT_INTERVAL)

        self.log.logging(
            "TransportZigpy", "Debug",
            f"Watchdog tick: now: {loop.time()}, last_heartbeat={self._last_heartbeat}, "
            f"startup_deadline={startup_deadline}, current_health={self._stack_health}"
        )

        now = loop.time()

        if self._last_heartbeat is None:
            if now > startup_deadline:
                self.log.logging(
                    "TransportZigpyStack", "Error",
                    f"Watchdog: no heartbeat within {STARTUP_TIMEOUT}s startup window "
                    f"— triggering supervised restart"
                )
                self._stack_health = "DEAD"
                self._shutdown_event.set()
                return
            self.log.logging(
                "TransportZigpyStack", "Debug",
                f"Watchdog: waiting for first heartbeat, "
                f"{max(0, startup_deadline - now):.0f}s remaining in startup window"
            )
            continue

        delta = now - self._last_heartbeat

        if delta < 30:
            new_health = "ALIVE"
        elif delta < 120:
            new_health = "IDLE"
        elif delta < DEAD_STACK_THRESHOLD:
            new_health = "SUSPECT"
        else:
            new_health = "DEAD"

        if new_health != _prev_health:
            self.log.logging(
                "TransportZigpyStack", "Debug",
                f"Watchdog: stack health {_prev_health} → {new_health} "
                f"({delta:.0f}s since last heartbeat)"
            )
            _prev_health = new_health
            self._stack_health = new_health

        if new_health == "DEAD":
            self.log.logging(
                "TransportZigpyStack", "Error",
                f"Watchdog: heartbeat lost for {delta:.0f}s "
                f"— triggering supervised restart"
            )
            self._shutdown_event.set()
            return


# ---------------------------------------------------------------------------
# Radio recovery
# ---------------------------------------------------------------------------

async def _maybe_reset_radio(self):
    """
    Last-resort radio recovery: force-disconnect and wait for the OS to
    release the serial/USB port before the next restart cycle.

    Invoked by the supervisor after every 5th consecutive failure.
    The actual reconnect is performed by the next cycle's radio_start call.
    """
    self.log.logging(
        "TransportZigpy", "Error",
        f"Radio recovery: forcing adapter disconnect "
        f"(consecutive failures: {self._consecutive_failures})"
    )
    try:
        if self.app is not None:
            with contextlib.suppress(Exception):
                await asyncio.wait_for(self.app.disconnect(), timeout=10.0)
            self.app = None

        self.log.logging(
            "TransportZigpy", "Status",
            "Radio recovery: adapter disconnected — waiting 5s for OS to release port"
        )
        await asyncio.sleep(5)
        self.log.logging(
            "TransportZigpy", "Status",
            "Radio recovery: ready — next supervisor cycle will reconnect"
        )
    except Exception as e:
        self.log.logging("TransportZigpy", "Error", f"Radio reset error: {e}")


# ---------------------------------------------------------------------------
# Event-loop cleanup (called from the OS-thread finally block)
# ---------------------------------------------------------------------------

def _cleanup(self, loop):
    """
    Cancels all remaining asyncio tasks and closes the event loop.

    Called from the finally block in zigpy_thread_function after
    loop.run_forever() returns.  Prevents task leakage and
    "coroutine was never awaited" warnings.
    """
    self.log.logging("TransportZigpy", "Debug", "Cleaning up loop")

    for task in asyncio.all_tasks(loop):
        task.cancel()

    try:
        loop.run_until_complete(
            asyncio.gather(*asyncio.all_tasks(loop), return_exceptions=True)
        )
    except Exception:
        pass  # nosec B110

    loop.close()
