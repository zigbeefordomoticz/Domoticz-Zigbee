#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TLS context of the WebUI server.

check_cert_and_key() builds the SSLContext the WebUI socket is wrapped with
when server.crt / server.key (or the SSLCertificate / SSLPrivateKey settings)
are present. It must refuse TLS 1.0 and 1.1 on its own, whoever calls it
(CodeQL py/insecure-protocol, code-scanning alert #1).
"""

import datetime
import ssl
import types

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import NameOID

from Classes.WebServer.com import check_cert_and_key


def _fake_webserver():
    return types.SimpleNamespace(logging=lambda *args, **kwargs: None)


def _write_self_signed(tmp_path):
    key = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now)
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    cert_path = tmp_path / "server.crt"
    key_path = tmp_path / "server.key"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(
        key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        )
    )
    return str(cert_path), str(key_path)


def test_context_refuses_tls_below_1_2(tmp_path):
    cert_path, key_path = _write_self_signed(tmp_path)

    context = check_cert_and_key(_fake_webserver(), cert_path, key_path)

    assert isinstance(context, ssl.SSLContext)
    assert context.minimum_version == ssl.TLSVersion.TLSv1_2


def test_no_context_without_certificate(tmp_path):
    _, key_path = _write_self_signed(tmp_path)

    assert check_cert_and_key(_fake_webserver(), str(tmp_path / "missing.crt"), key_path) is None


def test_no_context_with_invalid_certificate(tmp_path):
    cert_path, key_path = _write_self_signed(tmp_path)
    with open(cert_path, "w") as f:
        f.write("not a certificate")

    assert check_cert_and_key(_fake_webserver(), cert_path, key_path) is None
