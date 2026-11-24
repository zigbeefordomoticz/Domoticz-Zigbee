#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compressed copies of the WebUI files (Classes/WebServer/compressedFiles.py).

Each file is compressed once and kept in memory. The WebUI can be updated while
the plugin is running: whatever way the file is replaced, the next request must
get the new content.
"""

import gzip
import os
import shutil
import threading
import zlib

import pytest

from Classes.WebServer import compressedFiles
from Classes.WebServer.compressedFiles import CompressedFiles, is_compressible
from tests.Classes.WebServer.test_webserver_http import (HASHED_BUNDLE,
                                                         FakeWebServer, get,
                                                         home)

__all__ = ["home"]

BUNDLE = "/z4d/" + HASHED_BUNDLE
GZIP = {"Accept-Encoding": "gzip, deflate"}
OLD = 1_700_000_000


@pytest.fixture
def compressions(monkeypatch):
    """The contents compressed, in order."""
    done = []
    real = compressedFiles.compress

    def spy(body, encoding):
        done.append(body)
        return real(body, encoding)

    monkeypatch.setattr(compressedFiles, "compress", spy)
    return done


@pytest.fixture
def ws(home):
    return FakeWebServer(home, enableGzip=1, enableDeflate=1)


@pytest.fixture
def bundle(home):
    return home / "www" / "z4d" / HASHED_BUNDLE


def served(ws, path=BUNDLE):
    reply = get(ws, path, GZIP)
    assert reply.status == 200
    assert reply.headers["Content-Encoding"] == "gzip"
    return gzip.decompress(reply.body)


# ─── Compressed once ──────────────────────────────────────────────────────────

def test_an_unchanged_file_is_compressed_once(ws, compressions):
    assert [served(ws) for _ in range(3)] == [b"console.log(1)"] * 3
    assert compressions == [b"console.log(1)"]


def test_an_unchanged_file_is_not_read_again(ws, bundle, monkeypatch):
    served(ws)
    monkeypatch.setattr("builtins.open", lambda *a, **k: pytest.fail("the file is read again"))
    assert served(ws) == b"console.log(1)"


def test_every_angular_route_shares_the_index_html_copy(ws, compressions):
    for path in ("/z4d/", "/z4d/index.html", "/z4d/dashboard", "/z4d/device"):
        assert served(ws, path) == b"<html>index</html>"
    assert len(compressions) == 1


# ─── The WebUI is updated while the plugin is running ─────────────────────────

def test_a_newer_file_is_compressed_again(ws, bundle, compressions):
    served(ws)
    bundle.write_bytes(b"console.log('new WebUI')")
    assert served(ws) == b"console.log('new WebUI')"
    assert served(ws) == b"console.log('new WebUI')"
    assert compressions == [b"console.log(1)", b"console.log('new WebUI')"]


def test_a_file_replaced_by_one_with_an_older_date_is_compressed_again(ws, home, bundle):
    served(ws)
    previous = home / "previous.js"
    previous.write_bytes(b"console.log('restored')")
    os.utime(previous, (OLD, OLD))
    shutil.move(str(previous), str(bundle))
    assert os.stat(bundle).st_mtime == OLD
    assert served(ws) == b"console.log('restored')"


def test_same_size_and_same_date_is_still_seen_as_another_file(ws, home):
    """index.html keeps its size from one build to the next; an archive can restore the same date."""
    index = home / "www" / "z4d" / "index.html"
    stat = os.stat(index)
    assert served(ws, "/z4d/index.html") == b"<html>index</html>"

    other = home / "other.html"
    other.write_bytes(b"<html>INDEX</html>")
    os.utime(other, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    os.replace(other, index)

    assert (os.stat(index).st_size, os.stat(index).st_mtime_ns) == (stat.st_size, stat.st_mtime_ns)
    assert served(ws, "/z4d/index.html") == b"<html>INDEX</html>"


def test_a_removed_file_is_not_served_from_memory(ws, bundle):
    served(ws)
    bundle.unlink()
    assert served(ws) == b"<html>index</html>"   # as any missing file


def test_a_file_being_written_is_answered_but_not_kept(tmp_path, monkeypatch):
    page = tmp_path / "page.html"
    page.write_bytes(b"half")
    cache = CompressedFiles()
    real = os.fstat
    calls = []

    def fstat(fd):
        calls.append(fd)
        if len(calls) == 2:   # between the read and the second check, the copy goes on
            page.write_bytes(b"half and the rest")
        return real(fd)

    monkeypatch.setattr(compressedFiles.os, "fstat", fstat)
    cache.get(page, "gzip")
    assert cache.size == 0
    assert gzip.decompress(cache.get(page, "gzip")) == b"half and the rest"


# ─── What is compressed, and how it is sent ───────────────────────────────────

def test_gzip_first_then_deflate_then_nothing(ws):
    assert get(ws, BUNDLE, GZIP).headers["Content-Encoding"] == "gzip"
    deflated = get(ws, BUNDLE, {"Accept-Encoding": "deflate"})
    assert deflated.headers["Content-Encoding"] == "deflate"
    assert zlib.decompress(deflated.body, -zlib.MAX_WBITS) == b"console.log(1)"
    plain = get(ws, BUNDLE)
    assert "Content-Encoding" not in plain.headers
    assert plain.body == b"console.log(1)"


def test_the_caches_between_are_told_that_the_body_depends_on_the_encoding(ws):
    for headers in (GZIP, {}):
        assert get(ws, BUNDLE, headers).headers["Vary"] == "Accept-Encoding"


def test_content_length_is_the_compressed_length(ws):
    reply = get(ws, BUNDLE, GZIP)
    assert int(reply.headers["Content-Length"]) == len(reply.body)


def test_a_large_file_is_sent_in_chunks(home, bundle):
    content = os.urandom(50_000)
    bundle.write_bytes(content)
    reply = get(FakeWebServer(home, enableGzip=1, enableChunk=1), BUNDLE, GZIP)
    assert reply.headers["Transfer-Encoding"] == "chunked"
    assert "Content-Length" not in reply.headers
    body, rest = b"", reply.body
    while True:
        size, _, rest = rest.partition(b"\r\n")
        if int(size, 16) == 0:
            break
        body, rest = body + rest[:int(size, 16)], rest[int(size, 16) + 2:]
    assert gzip.decompress(body) == content


def test_an_already_compressed_format_is_sent_as_it_is(ws, compressions):
    reply = get(ws, "/z4d/assets/z4d_logo.png", GZIP)
    assert "Content-Encoding" not in reply.headers
    assert reply.body == b"\x89PNG"
    assert compressions == []


@pytest.mark.parametrize("name, expected", [
    ("main.js", True), ("styles.css", True), ("primeicons.ttf", True), ("primeicons.svg", True), ("favicon.ico", True),
    ("fa-solid-900.woff2", False), ("flag_uk.PNG", False), ("primeicons.woff", False),
])
def test_is_compressible(name, expected):
    assert is_compressible(name) is expected


def test_an_empty_file_can_be_served(ws, bundle):
    bundle.write_bytes(b"")
    assert served(ws) == b""


# ─── What is not kept ─────────────────────────────────────────────────────────

def test_a_log_download_is_compressed_but_never_kept(ws, home):
    reply = get(ws, f"/download{home / 'Logs' / 'PluginZigbee_01.log'}", GZIP)
    assert gzip.decompress(reply.body) == b"plugin log line"
    assert ws.compressed_files.size == 0


def test_nothing_is_kept_when_the_cache_is_disabled(home):
    ws = FakeWebServer(home, enableGzip=1, enableCache=0)
    assert served(ws) == b"console.log(1)"
    assert ws.compressed_files.size == 0


def test_the_memory_used_is_bounded_least_recently_used_out_first(tmp_path):
    files = []
    for i in range(4):
        files.append(tmp_path / f"{i}.js")
        files[-1].write_bytes(os.urandom(1000))   # about 1 kB once "compressed"
    cache = CompressedFiles(max_size=3500)

    for i in (0, 1, 2, 0, 3):   # 1 is the least recently used when 3 comes
        cache.get(files[i], "gzip")

    assert cache.size <= 3500
    assert [os.path.basename(name) for name, _ in cache._entries] == ["2.js", "0.js", "3.js"]


def test_a_file_larger_than_the_cache_is_served_and_evicts_nothing(tmp_path):
    small, large = tmp_path / "small.js", tmp_path / "large.js"
    small.write_bytes(os.urandom(500))
    large.write_bytes(os.urandom(5000))
    cache = CompressedFiles(max_size=1000)
    cache.get(small, "gzip")
    assert gzip.decompress(cache.get(large, "gzip")) == large.read_bytes()
    assert [os.path.basename(name) for name, _ in cache._entries] == ["small.js"]


def test_the_accounted_size_is_right_after_concurrent_requests_and_updates(tmp_path):
    page = tmp_path / "page.js"
    page.write_bytes(b"0" * 1000)
    cache = CompressedFiles()
    errors = []

    def client():
        try:
            for _ in range(50):
                gzip.decompress(cache.get(page, "gzip"))
        except Exception as error:   # reported by the main thread
            errors.append(error)

    threads = [threading.Thread(target=client) for _ in range(8)]
    for thread in threads:
        thread.start()
    for i in range(20):
        other = tmp_path / f"page.{i}"
        other.write_bytes(b"%d" % i * 1000)
        os.replace(other, page)
    for thread in threads:
        thread.join()

    assert errors == []
    assert cache.size == sum(len(body) for _, body in cache._entries.values())
    assert gzip.decompress(cache.get(page, "gzip")) == b"19" * 1000
