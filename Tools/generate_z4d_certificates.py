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
Script to generate a self-signed SSL/TLS certificate and demonstrate usage in an SSL context.

Requirements:
- Python 3.x
- OpenSSL command-line tool (`openssl`) accessible in the system path.

Functions:
- create_self_signed_cert(cert_dir):
    Generates a self-signed SSL certificate and key pair if not already present.

Usage:
1. Run the script to generate or retrieve the SSL certificate and key.
2. Use the generated certificate and key paths in an SSL context for secure communication.

Example:
    python3 generate_z4d_certificates.py

Note:
- Modify the `-subj` parameter in the `openssl` command to customize certificate details.
- For production use, consider obtaining certificates from a trusted certificate authority (CA).
"""

import os
import ssl
import subprocess


def create_self_signed_cert(cert_dir):
    """
    Generate a self-signed SSL certificate and key pair if not already present.

    Args:
    - cert_dir (str): Directory path where the certificate and key will be stored.

    Returns:
    - cert_path (str): Path to the generated certificate file.
    - key_path (str): Path to the generated private key file.
    """

    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    # Paths for the certificate and key files
    cert_path = os.path.join(cert_dir, "server.crt")
    key_path = os.path.join(cert_dir, "server.key")

    # Check if the certificate already exists
    if os.path.exists(cert_path) and os.path.exists(key_path):
        print("Certificate and key already exist.")
        return cert_path, key_path

    # Generate a self-signed certificate
    subprocess.check_call([
        "openssl", "req", "-x509", "-nodes", "-days", "365",
        "-newkey", "rsa:4096", "-keyout", key_path,
        "-out", cert_path,
        "-subj", "/C=FR/ST=California/L=Paris/O=Z4D/OU=Org/CN=localhost"
    ])

    print(f"Certificate and key generated: {cert_path}, {key_path}")
    return cert_path, key_path

# Directory to store the certificate and key
cert_dir = "./certs"

# Create self-signed certificate
cert_path, key_path = create_self_signed_cert(cert_dir)

# Example usage of the certificate in an SSL context
context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
context.load_cert_chain(certfile=cert_path, keyfile=key_path)

print("SSL context created with the generated certificate.")
