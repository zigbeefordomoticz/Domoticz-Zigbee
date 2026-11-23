#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DomoticzAPIClient: the JSON API URL built from the hardware "API base url" (Mode5).

The path of the base url is kept, so that a Domoticz started with -webroot is
reached. What a user leaves around the url by mistake must not end up in it: an
extra space makes urllib raise InvalidURL, which _do_request() does not catch, and
a double slash asks Domoticz for a page it does not have.
"""

import types
import unittest
import urllib.request
from unittest import mock

from Classes.DomoticzDB import DomoticzAPIClient

QUERY = "type=command&param=gethardware"


class _Response:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b'{"status": "OK"}'


class TestApiBaseUrl(unittest.TestCase):

    def _client(self, base_url):
        pluginconf = types.SimpleNamespace(pluginConf={})
        client = DomoticzAPIClient(base_url, pluginconf, mock.Mock(), 14)
        self.addCleanup(client.stop)
        return client

    def _assert_url_ready(self, cases):
        for base_url, expected in cases.items():
            with self.subTest(base_url=base_url):
                self.assertEqual(self._client(base_url).url_ready, expected)

    def test_without_path(self):
        self._assert_url_ready({
            "http://127.0.0.1:8080": "http://127.0.0.1:8080/json.htm?",
            "http://127.0.0.1:8080/": "http://127.0.0.1:8080/json.htm?",
            "http://127.0.0.1:8080//": "http://127.0.0.1:8080/json.htm?",
            "https://domoticz.local": "https://domoticz.local/json.htm?",
        })

    def test_web_root_is_kept(self):
        self._assert_url_ready({
            "http://127.0.0.1:8080/domoticz": "http://127.0.0.1:8080/domoticz/json.htm?",
            "http://127.0.0.1:8080/domoticz/": "http://127.0.0.1:8080/domoticz/json.htm?",
            "https://domoticz.local/a/b": "https://domoticz.local/a/b/json.htm?",
        })

    def test_surrounding_spaces_are_dropped(self):
        self._assert_url_ready({
            " http://127.0.0.1:8080": "http://127.0.0.1:8080/json.htm?",
            "http://127.0.0.1:8080/ ": "http://127.0.0.1:8080/json.htm?",
            "http://127.0.0.1:8080/domoticz/ \t": "http://127.0.0.1:8080/domoticz/json.htm?",
        })

    def test_url_copied_from_the_browser(self):
        self._assert_url_ready({
            "http://127.0.0.1:8080/#/Dashboard": "http://127.0.0.1:8080/json.htm?",
            "http://127.0.0.1:8080/domoticz/#/Dashboard": "http://127.0.0.1:8080/domoticz/json.htm?",
        })

    def test_credentials_go_to_the_header_only(self):
        client = self._client("http://user:pass@127.0.0.1:8080/domoticz/")
        self.assertEqual(client.url_ready, "http://127.0.0.1:8080/domoticz/json.htm?")
        self.assertEqual((client.username, client.password), ("user", "pass"))
        self.assertEqual(client.auth_header, "dXNlcjpwYXNz")

    def test_request_is_sent_to_the_web_root(self):
        client = self._client("http://127.0.0.1:8080/domoticz/ ")
        with mock.patch.object(urllib.request, "urlopen", return_value=_Response()) as urlopen:
            self.assertEqual(client.get_blocking(QUERY), {"status": "OK"})
        self.assertEqual(urlopen.call_args[0][0].full_url, f"http://127.0.0.1:8080/domoticz/json.htm?{QUERY}")


if __name__ == "__main__":
    unittest.main()
