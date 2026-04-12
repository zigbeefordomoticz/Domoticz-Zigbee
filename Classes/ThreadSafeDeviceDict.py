#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Implementation of Zigbee for Domoticz plugin.
#
# This file is part of Zigbee for Domoticz plugin. https://github.com/zigbeefordomoticz/Domoticz-Zigbee
# (C) 2015-2026
#
# Initial authors: pipiche38
#


"""
ThreadSafeDeviceDict.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides ThreadSafeDeviceDict, a thread-safe dict-like container intended
for use as a drop-in replacement for plain dicts such as ListOfDevices,
IEEE2NWK, and ListOfDomoticzWidget in zigbeefordomoticz.

Each instance owns its own RLock.  Inner dicts are auto-wrapped on
assignment, so nested writes like::

    self.ListOfDevices[nwkid]["battery"] = 90

are protected without any extra effort from the caller.

Debugging
---------
Set the module-level flag ``TSDD_DEBUG = True`` (or call
``ThreadSafeDeviceDict.set_debug(True)`` at runtime) to enable per-call
trace logging on every method.  Each log line includes:
 
* timestamp
* thread name + id
* instance id (so you can distinguish ListOfDevices from IEEE2NWK)
* method name, arguments, and return value (or exception)
* wall-clock duration in microseconds
 
When ``TSDD_DEBUG`` is ``False`` (the default) the decorator adds no
measurable overhead — the check is a single boolean read.
"""

import functools
import logging
import threading
import time
import traceback
from collections.abc import MutableMapping
from contextlib import contextmanager

# ---------------------------------------------------------------------------
# Debug flag — flip to True to enable trace logging, or call
# ThreadSafeDeviceDict.set_debug(True) at runtime.
# ---------------------------------------------------------------------------
TSDD_DEBUG: bool = False
 
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Debug decorator
# ---------------------------------------------------------------------------
 
def _tsdd_trace(method):
    """Wrap *method* with optional debug-trace logging.
 
    The wrapper checks the module-level ``TSDD_DEBUG`` flag on **every
    call**.  When the flag is ``False`` the check is a single boolean read
    and control falls through to the real method immediately — no string
    formatting, no logging, negligible overhead.
 
    When ``TSDD_DEBUG`` is ``True`` each call emits one ``DEBUG`` line via
    the module logger (``logging.getLogger(__name__)``), e.g.::
 
        [TSDD] 2024-01-15 12:00:01.042 | Thread-3(140234) | id=0x7f3a |
               __setitem__('1234', {'battery': 90}) -> None  [38.4 µs]
 
    Exceptions are logged (with full traceback) then re-raised unchanged so
    normal error handling is unaffected.
 
    Args:
        method: Any instance method of :class:`ThreadSafeDeviceDict`.
 
    Returns:
        A :func:`functools.wraps`-preserving wrapper around *method*.
    """
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        if not TSDD_DEBUG:
            # Fast path — zero extra work in production.
            return method(self, *args, **kwargs)
 
        thread = threading.current_thread()
        name = method.__name__
        id_str = hex(id(self))
 
        def _repr(v, limit=80):
            """Truncate long reprs so log lines stay readable."""
            r = repr(v)
            return r if len(r) <= limit else r[:limit] + "…"
 
        arg_str = ", ".join(
            [*(f"{_repr(a)}" for a in args),
             *(f"{k}={_repr(v)}" for k, v in kwargs.items())]
        )
 
        t0 = time.perf_counter()
        try:
            result = method(self, *args, **kwargs)
            elapsed = (time.perf_counter() - t0) * 1_000_000
            logger.debug(
                "[TSDD] %s | %s(%d) | id=%s | %s(%s) -> %s  [%.1f µs]",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                thread.name, thread.ident,
                id_str,
                name, arg_str,
                _repr(result),
                elapsed,
            )
            return result
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1_000_000
            logger.debug(
                "[TSDD] %s | %s(%d) | id=%s | %s(%s) !! %s: %s  [%.1f µs]\n%s",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                thread.name, thread.ident,
                id_str,
                name, arg_str,
                type(exc).__name__, exc,
                elapsed,
                traceback.format_exc(),
            )
            raise
 
    return wrapper
 
# ---------------------------------------------------------------------------
# Main class
# ---------------------------------------------------------------------------

class ThreadSafeDeviceDict(MutableMapping):
    """A thread-safe, dict-like mapping whose values are also thread-safe.

    Wraps an internal ``dict`` and protects every read and write with a
    :class:`threading.RLock`.  Using an *reentrant* lock means the same
    thread can call multiple methods in sequence (or nest a
    ``with self.lock():`` block around several operations) without
    deadlocking.

    **Auto-wrapping of inner dicts**

    Whenever a plain :class:`dict` is stored as a value – whether via
    ``__setitem__``, ``update``, ``setdefault``, or the constructor – it is
    silently converted to a :class:`ThreadSafeDeviceDict`.  This means
    nested access such as::

        device = self.ListOfDevices[nwkid]   # returns ThreadSafeDeviceDict
        device["battery"] = 90               # protected by device's own lock

    is safe without any extra locking by the caller.

    **Compound operations**

    Individual method calls are atomic, but check-then-act patterns are
    not.  Use the :meth:`lock` context manager to make a block of
    operations atomic::

        with self.ListOfDevices.lock():
            if nwkid not in self.ListOfDevices:
                self.ListOfDevices[nwkid] = {"status": "new"}

    **Multiple instances**

    Every instance creates its own independent ``RLock``::

        self.IEEE2NWK             = ThreadSafeDeviceDict()  # lock #1
        self.ListOfDomoticzWidget = ThreadSafeDeviceDict()  # lock #2
        self.ListOfDevices        = ThreadSafeDeviceDict()  # lock #3

    Nesting locks from *different* instances in inconsistent orders across
    threads will cause a deadlock.  Always acquire them in the same order.
    
    **Debug tracing**
 
    Enable per-call trace logging globally::
 
        import ThreadSafeDeviceDict as tsdd
        tsdd.TSDD_DEBUG = True              # module-level flag (takes effect immediately)
 
        # or via the class helper:
        ThreadSafeDeviceDict.set_debug(True)
 
    Configure the standard logger to see the output::
 
        import logging
        logging.basicConfig(level=logging.DEBUG)
 
    Each log line contains timestamp, thread name/id, instance id (hex),
    method name with arguments, return value, and duration in microseconds.
    Set the flag back to ``False`` at any time to silence tracing instantly.
    """

    @classmethod
    def set_debug(cls, enabled: bool) -> None:
        """Enable or disable debug tracing at runtime without a restart.
 
        Flips the module-level ``TSDD_DEBUG`` flag so the change takes
        effect on the very next method call across **all** instances.
 
        Args:
            enabled: ``True`` to turn tracing on, ``False`` to turn it off.
 
        Example::
 
            ThreadSafeDeviceDict.set_debug(True)
            # … reproduce the bug …
            ThreadSafeDeviceDict.set_debug(False)
        """
        global TSDD_DEBUG
        TSDD_DEBUG = enabled
        logger.info("[TSDD] debug tracing %s", "ENABLED" if enabled else "DISABLED")
 
    @_tsdd_trace
    def __init__(self, *args, **kwargs):
        """Initialise the mapping, optionally from an existing dict or iterable.

        Accepts the same arguments as the built-in :class:`dict` constructor.
        All plain dict values are auto-wrapped during initialisation.

        Examples::

            d = ThreadSafeDeviceDict()
            d = ThreadSafeDeviceDict({"abc": {"battery": 100}})
            d = ThreadSafeDeviceDict(abc={"battery": 100})
        """
        self._lock = threading.RLock()
        self._data = {}
        # Route through update() so every value is wrapped via __setitem__.
        self.update(dict(*args, **kwargs))

    # ------------------------------------------------------------------
    # Auto-wrap helper
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap(value):
        """Return *value* wrapped in a :class:`ThreadSafeDeviceDict` if needed.

        Only plain :class:`dict` instances are wrapped; values that are
        already a :class:`ThreadSafeDeviceDict` (or any other type) are
        returned unchanged.  The wrapping is recursive: nested plain dicts
        inside *value* are also wrapped by the :class:`ThreadSafeDeviceDict`
        constructor.

        Args:
            value: The value to (potentially) wrap.

        Returns:
            A :class:`ThreadSafeDeviceDict` when *value* is a plain
            :class:`dict`, otherwise *value* unmodified.
        """
        if isinstance(value, dict) and not isinstance(value, ThreadSafeDeviceDict):
            return ThreadSafeDeviceDict(value)
        return value

    # ------------------------------------------------------------------
    # Core MutableMapping interface
    # ------------------------------------------------------------------

    @_tsdd_trace
    def __setitem__(self, key, value):
        """Set ``self[key] = value``, auto-wrapping plain dict values.

        Thread-safe.  If *value* is a plain :class:`dict` it is converted
        to a :class:`ThreadSafeDeviceDict` before being stored.

        Args:
            key: Mapping key.
            value: Value to store; plain dicts are auto-wrapped.
        """
        with self._lock:
            self._data[key] = self._wrap(value)

    @_tsdd_trace
    def __getitem__(self, key):
        """Return ``self[key]``.

        Thread-safe.

        Args:
            key: Mapping key to look up.

        Raises:
            KeyError: If *key* is not present.
        """
        with self._lock:
            return self._data[key]

    @_tsdd_trace
    def __delitem__(self, key):
        """Delete ``self[key]``.

        Thread-safe.

        Args:
            key: Mapping key to remove.

        Raises:
            KeyError: If *key* is not present.
        """
        with self._lock:
            del self._data[key]

    def __iter__(self):
        """Return an iterator over a *snapshot* of the current keys.

        A snapshot (list copy) is taken under the lock so that another
        thread modifying the mapping while the caller iterates does not
        raise :exc:`RuntimeError`.

        Returns:
            An iterator over the keys present at the moment of the call.
        """
        with self._lock:
            return iter(list(self._data))

    def __len__(self):
        """Return the number of items in the mapping.

        Thread-safe.

        Returns:
            Integer number of stored keys.
        """
        with self._lock:
            return len(self._data)

    def __contains__(self, key):
        """Return ``True`` if *key* is present in the mapping.

        Thread-safe.

        Args:
            key: Key to test for membership.

        Returns:
            ``True`` if present, ``False`` otherwise.
        """
        with self._lock:
            return key in self._data

    def __repr__(self):
        """Return a developer-friendly string representation.

        Thread-safe.

        Returns:
            A string of the form ``ThreadSafeDeviceDict({...})``.
        """
        with self._lock:
            return f"{self.__class__.__name__}({self._data!r})"

    # ------------------------------------------------------------------
    # Convenience / safety extras
    # ------------------------------------------------------------------

    @_tsdd_trace
    def get(self, key, default=None):
        """Return the value for *key*, or *default* if absent.

        Thread-safe.

        Args:
            key: Key to look up.
            default: Value returned when *key* is missing (default ``None``).

        Returns:
            The stored value or *default*.
        """
        with self._lock:
            return self._data.get(key, default)

    @_tsdd_trace
    def setdefault(self, key, default=None):
        """Return ``self[key]``, inserting *default* (auto-wrapped) if absent.

        The check and the optional insertion are performed atomically under
        the lock, so no other thread can insert the same key between the
        test and the write.

        Args:
            key: Key to look up or insert.
            default: Value to store when *key* is absent; plain dicts are
                auto-wrapped (default ``None``).

        Returns:
            The existing or newly inserted value for *key*.
        """
        with self._lock:
            if key not in self._data:
                self._data[key] = self._wrap(default)
            return self._data[key]

    @_tsdd_trace
    def pop(self, key, *args):
        """Remove *key* and return its value, or *default* if absent.

        Thread-safe.

        Args:
            key: Key to remove.
            *args: Optional single default value.  If omitted and *key* is
                missing a :exc:`KeyError` is raised (standard dict behaviour).

        Returns:
            The value that was stored under *key*, or the default.

        Raises:
            KeyError: If *key* is missing and no default was supplied.
        """
        with self._lock:
            return self._data.pop(key, *args)

    @_tsdd_trace
    def update(self, other=None, **kwargs):
        """Update the mapping from *other* and/or keyword arguments.

        All plain dict values are auto-wrapped.  The merge of *other* and
        *kwargs* is performed atomically under the lock.

        Args:
            other: A mapping or iterable of key/value pairs (optional).
            **kwargs: Additional key/value pairs.
        """
        with self._lock:
            merged = {}
            if other is not None:
                merged.update(other)
            merged.update(kwargs)
            for k, v in merged.items():
                self._data[k] = self._wrap(v)

    @_tsdd_trace
    def keys(self):
        """Return a snapshot list of all keys.

        Thread-safe.  Returns a ``list`` rather than a view so that the
        result is stable even if the mapping is modified afterwards.

        Returns:
            A ``list`` of keys.
        """
        with self._lock:
            return list(self._data.keys())

    @_tsdd_trace
    def values(self):
        """Return a snapshot list of all values.

        Thread-safe.  Returns a ``list`` rather than a view so that the
        result is stable even if the mapping is modified afterwards.

        Returns:
            A ``list`` of values.
        """
        with self._lock:
            return list(self._data.values())

    @_tsdd_trace
    def items(self):
        """Return a snapshot list of all ``(key, value)`` pairs.

        Thread-safe.  Returns a ``list`` rather than a view so that the
        result is stable even if the mapping is modified afterwards.

        Returns:
            A ``list`` of ``(key, value)`` tuples.
        """
        with self._lock:
            return list(self._data.items())

    @_tsdd_trace
    def snapshot(self):
        """Return a plain ``dict`` shallow copy of the current state.

        Useful for serialisation, logging, or passing data to code that
        expects a plain ``dict``.  The copy is taken atomically under the
        lock, but subsequent changes to the mapping are not reflected.

        Returns:
            A plain :class:`dict` with the same keys and values as this
            mapping at the moment of the call.
        """
        with self._lock:
            return dict(self._data)

    @contextmanager
    def lock(self):
        """Context manager that holds the internal ``RLock`` for the block.

        Use this to make a sequence of operations atomic from the
        perspective of other threads::

            with self.ListOfDevices.lock():
                if nwkid not in self.ListOfDevices:
                    self.ListOfDevices[nwkid] = {"status": "new"}
                self.ListOfDevices[nwkid]["battery"] = 100

        Because the underlying lock is an ``RLock``, all normal method calls
        inside the block re-enter the lock safely without deadlocking.

        Yields:
            Nothing; control passes to the ``with`` block body.
        """
        if TSDD_DEBUG:
            thread = threading.current_thread()
            t0 = time.perf_counter()
            logger.debug(
                "[TSDD] %s | %s(%d) | id=%s | lock() ENTER",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                thread.name, thread.ident, hex(id(self)),
            )
        with self._lock:
            yield
        if TSDD_DEBUG:
            elapsed = (time.perf_counter() - t0) * 1_000_000
            logger.debug(
                "[TSDD] %s | %s(%d) | id=%s | lock() EXIT  [%.1f µs]",
                time.strftime("%Y-%m-%d %H:%M:%S"),
                thread.name, thread.ident, hex(id(self)), elapsed,
            )
 