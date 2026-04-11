"""
test_thread_safe_device_dict.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Unit and concurrency tests for ThreadSafeDeviceDict.

Run with:
    python -m pytest test_thread_safe_device_dict.py -v
"""

import threading
import time
import unittest

from Classes.ThreadSafeDeviceDict import ThreadSafeDeviceDict


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_device():
    """Return a typical zigbee device sub-dict."""
    return {"battery": 100, "status": "active", "ep": {"01": {"cluster": "0006"}}}


# ---------------------------------------------------------------------------
# 1. Construction
# ---------------------------------------------------------------------------

class TestConstruction(unittest.TestCase):

    def test_empty_construction(self):
        d = ThreadSafeDeviceDict()
        self.assertEqual(len(d), 0)

    def test_construction_from_dict(self):
        d = ThreadSafeDeviceDict({"abc": {"battery": 90}})
        self.assertIn("abc", d)
        self.assertEqual(d["abc"]["battery"], 90)

    def test_construction_from_kwargs(self):
        d = ThreadSafeDeviceDict(key1="val1", key2="val2")
        self.assertEqual(d["key1"], "val1")

    def test_inner_dict_wrapped_at_construction(self):
        d = ThreadSafeDeviceDict({"abc": {"battery": 90}})
        self.assertIsInstance(d["abc"], ThreadSafeDeviceDict)

    def test_deeply_nested_dict_wrapped_at_construction(self):
        d = ThreadSafeDeviceDict({"abc": {"ep": {"01": {"cluster": "0006"}}}})
        self.assertIsInstance(d["abc"], ThreadSafeDeviceDict)
        self.assertIsInstance(d["abc"]["ep"], ThreadSafeDeviceDict)
        self.assertIsInstance(d["abc"]["ep"]["01"], ThreadSafeDeviceDict)


# ---------------------------------------------------------------------------
# 2. Basic dict operations
# ---------------------------------------------------------------------------

class TestBasicOperations(unittest.TestCase):

    def setUp(self):
        self.d = ThreadSafeDeviceDict()

    def test_setitem_and_getitem(self):
        self.d["abc"] = {"battery": 80}
        self.assertEqual(self.d["abc"]["battery"], 80)

    def test_delitem(self):
        self.d["abc"] = {}
        del self.d["abc"]
        self.assertNotIn("abc", self.d)

    def test_delitem_missing_raises(self):
        with self.assertRaises(KeyError):
            del self.d["missing"]

    def test_getitem_missing_raises(self):
        with self.assertRaises(KeyError):
            _ = self.d["missing"]

    def test_contains(self):
        self.d["abc"] = {}
        self.assertIn("abc", self.d)
        self.assertNotIn("xyz", self.d)

    def test_len(self):
        self.assertEqual(len(self.d), 0)
        self.d["a"] = 1
        self.d["b"] = 2
        self.assertEqual(len(self.d), 2)

    def test_iter(self):
        self.d["a"] = 1
        self.d["b"] = 2
        self.assertEqual(set(self.d), {"a", "b"})

    def test_repr(self):
        r = repr(self.d)
        self.assertTrue(r.startswith("ThreadSafeDeviceDict("))

    def test_keys(self):
        self.d["a"] = 1
        self.assertIn("a", self.d.keys())

    def test_values(self):
        self.d["a"] = 42
        self.assertIn(42, self.d.values())

    def test_items(self):
        self.d["a"] = 1
        self.assertIn(("a", 1), self.d.items())


# ---------------------------------------------------------------------------
# 3. Auto-wrapping
# ---------------------------------------------------------------------------

class TestAutoWrapping(unittest.TestCase):

    def test_plain_dict_wrapped_on_setitem(self):
        d = ThreadSafeDeviceDict()
        d["abc"] = {"battery": 90}
        self.assertIsInstance(d["abc"], ThreadSafeDeviceDict)

    def test_already_wrapped_not_double_wrapped(self):
        d = ThreadSafeDeviceDict()
        inner = ThreadSafeDeviceDict({"battery": 90})
        d["abc"] = inner
        self.assertIs(d["abc"], inner)

    def test_non_dict_not_wrapped(self):
        d = ThreadSafeDeviceDict()
        d["key"] = 42
        self.assertIsInstance(d["key"], int)

    def test_nested_write_is_protected(self):
        d = ThreadSafeDeviceDict()
        d["abc"] = {"battery": 100}
        d["abc"]["battery"] = 50        # must not raise
        self.assertEqual(d["abc"]["battery"], 50)

    def test_update_wraps_values(self):
        d = ThreadSafeDeviceDict()
        d.update({"abc": {"battery": 70}})
        self.assertIsInstance(d["abc"], ThreadSafeDeviceDict)


# ---------------------------------------------------------------------------
# 4. Convenience methods
# ---------------------------------------------------------------------------

class TestConvenienceMethods(unittest.TestCase):

    def setUp(self):
        self.d = ThreadSafeDeviceDict({"abc": {"battery": 100}})

    def test_get_existing(self):
        self.assertEqual(self.d.get("abc")["battery"], 100)

    def test_get_missing_returns_default(self):
        self.assertIsNone(self.d.get("missing"))
        self.assertEqual(self.d.get("missing", "fallback"), "fallback")

    def test_setdefault_existing_unchanged(self):
        original = self.d["abc"]
        result = self.d.setdefault("abc", {"battery": 0})
        self.assertIs(result, original)

    def test_setdefault_missing_inserts(self):
        result = self.d.setdefault("new_nwkid", {"battery": 50})
        self.assertIsInstance(result, ThreadSafeDeviceDict)
        self.assertEqual(result["battery"], 50)
        self.assertIn("new_nwkid", self.d)

    def test_setdefault_wraps_default(self):
        self.d.setdefault("x", {"battery": 10})
        self.assertIsInstance(self.d["x"], ThreadSafeDeviceDict)

    def test_pop_existing(self):
        val = self.d.pop("abc")
        self.assertNotIn("abc", self.d)
        self.assertEqual(val["battery"], 100)

    def test_pop_missing_with_default(self):
        self.assertEqual(self.d.pop("missing", "default"), "default")

    def test_pop_missing_no_default_raises(self):
        with self.assertRaises(KeyError):
            self.d.pop("missing")

    def test_snapshot_returns_plain_dict(self):
        snap = self.d.snapshot()
        self.assertIsInstance(snap, dict)
        self.assertNotIsInstance(snap, ThreadSafeDeviceDict)
        self.assertIn("abc", snap)

    def test_snapshot_is_independent(self):
        snap = self.d.snapshot()
        self.d["abc"]["battery"] = 0
        # snapshot still holds the ThreadSafeDeviceDict reference, but is a
        # separate top-level dict
        self.assertIn("abc", snap)


# ---------------------------------------------------------------------------
# 5. lock() context manager
# ---------------------------------------------------------------------------

class TestLockContextManager(unittest.TestCase):

    def test_lock_allows_compound_operation(self):
        d = ThreadSafeDeviceDict()
        with d.lock():
            if "abc" not in d:
                d["abc"] = {"status": "new"}
            d["abc"]["battery"] = 99
        self.assertEqual(d["abc"]["battery"], 99)

    def test_lock_is_reentrant(self):
        """Calling methods inside lock() must not deadlock."""
        d = ThreadSafeDeviceDict({"abc": {}})
        with d.lock():
            d["abc"]["battery"] = 42    # re-enters _lock on inner dict
            _ = d["abc"]["battery"]     # re-enters outer _lock via __getitem__
        self.assertEqual(d["abc"]["battery"], 42)

    def test_each_instance_has_independent_lock(self):
        d1 = ThreadSafeDeviceDict()
        d2 = ThreadSafeDeviceDict()
        self.assertIsNot(d1._lock, d2._lock)


# ---------------------------------------------------------------------------
# 6. Thread-safety (concurrency stress tests)
# ---------------------------------------------------------------------------

class TestThreadSafety(unittest.TestCase):

    def test_concurrent_writes_no_data_loss(self):
        """100 threads each writing a unique key → all 100 keys present."""
        d = ThreadSafeDeviceDict()
        num_threads = 100

        def writer(i):
            d[f"device_{i}"] = {"battery": i}

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(num_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(d), num_threads)

    def test_concurrent_nested_writes(self):
        """Multiple threads updating nested keys on the same device."""
        d = ThreadSafeDeviceDict()
        d["abc"] = {"battery": 0, "counter": 0}
        iterations = 1000

        def increment():
            for _ in range(iterations):
                with d.lock():
                    current = d["abc"]["counter"]
                    d["abc"]["counter"] = current + 1

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(d["abc"]["counter"], 5 * iterations)

    def test_concurrent_reads_and_writes(self):
        """Readers and writers run simultaneously without raising exceptions."""
        d = ThreadSafeDeviceDict({"abc": {"battery": 100}})
        errors = []

        def reader():
            for _ in range(500):
                try:
                    _ = d.get("abc", {})
                    _ = d.items()
                except Exception as e:
                    errors.append(e)

        def writer():
            for i in range(500):
                try:
                    d["abc"] = {"battery": i % 101}
                except Exception as e:
                    errors.append(e)

        threads = (
            [threading.Thread(target=reader) for _ in range(4)]
            + [threading.Thread(target=writer) for _ in range(2)]
        )
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(errors, [], f"Exceptions raised: {errors}")

    def test_iteration_snapshot_safe_during_mutation(self):
        """Iterating while another thread adds keys must not raise RuntimeError."""
        d = ThreadSafeDeviceDict({str(i): {} for i in range(50)})
        errors = []

        def mutator():
            for i in range(50, 100):
                d[str(i)] = {}
                time.sleep(0)

        def iterator():
            try:
                for _ in d:
                    time.sleep(0)
            except RuntimeError as e:
                errors.append(e)

        t1 = threading.Thread(target=mutator)
        t2 = threading.Thread(target=iterator)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [], "RuntimeError raised during concurrent iteration")

    def test_setdefault_no_double_insertion(self):
        """Only one thread should win the setdefault race."""
        d = ThreadSafeDeviceDict()
        results = []

        def inserter():
            val = d.setdefault("shared_key", {"inserted_by": threading.get_ident()})
            results.append(val["inserted_by"])

        threads = [threading.Thread(target=inserter) for _ in range(50)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All threads must see the same winner
        self.assertEqual(len(set(results)), 1, "setdefault returned different objects")
        self.assertEqual(len(d), 1)


# ---------------------------------------------------------------------------
# 7. Zigbee-specific usage patterns
# ---------------------------------------------------------------------------

class TestZigbeePatterns(unittest.TestCase):
    """Realistic patterns as used in zigbeefordomoticz."""

    def test_list_of_devices_typical_workflow(self):
        ListOfDevices = ThreadSafeDeviceDict()

        nwkid = "1234"
        ListOfDevices[nwkid] = make_device()
        ListOfDevices[nwkid]["battery"] = 85
        ListOfDevices[nwkid]["ep"]["01"]["cluster"] = "0008"

        self.assertEqual(ListOfDevices[nwkid]["battery"], 85)
        self.assertEqual(ListOfDevices[nwkid]["ep"]["01"]["cluster"], "0008")

    def test_ieee2nwk_lookup(self):
        IEEE2NWK = ThreadSafeDeviceDict()
        IEEE2NWK["00:11:22:33:44:55:66:77"] = "1234"
        self.assertEqual(IEEE2NWK["00:11:22:33:44:55:66:77"], "1234")

    def test_multiple_independent_dicts(self):
        IEEE2NWK             = ThreadSafeDeviceDict()
        ListOfDomoticzWidget = ThreadSafeDeviceDict()
        ListOfDevices        = ThreadSafeDeviceDict()

        # Each has its own lock
        self.assertIsNot(IEEE2NWK._lock, ListOfDomoticzWidget._lock)
        self.assertIsNot(IEEE2NWK._lock, ListOfDevices._lock)
        self.assertIsNot(ListOfDomoticzWidget._lock, ListOfDevices._lock)

    def test_compound_check_and_create(self):
        """Simulate safe initialisation of a new device entry."""
        ListOfDevices = ThreadSafeDeviceDict()
        nwkid = "abcd"

        with ListOfDevices.lock():
            if nwkid not in ListOfDevices:
                ListOfDevices[nwkid] = {"status": "new", "battery": 255}

        self.assertIn(nwkid, ListOfDevices)
        self.assertEqual(ListOfDevices[nwkid]["status"], "new")


if __name__ == "__main__":
    unittest.main(verbosity=2)
