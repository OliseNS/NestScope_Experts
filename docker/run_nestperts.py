#!/usr/bin/env python3
"""Run Nestperts (Flask) under Waitress for Docker / production."""
from __future__ import annotations

import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO not in sys.path:
    sys.path.insert(0, REPO)

from waitress import serve

from labeller.app import app, ensure_directories

ensure_directories()

port = int(os.environ.get("NESTPERTS_PORT", "5000"))
threads = int(os.environ.get("NESTPERTS_THREADS", "4"))
channel_timeout = int(os.environ.get("NESTPERTS_CHANNEL_TIMEOUT", "7200"))
max_body = int(os.environ.get("NESTPERTS_MAX_BODY_BYTES", "107374182400"))

serve(
    app,
    host="0.0.0.0",
    port=port,
    threads=threads,
    channel_timeout=channel_timeout,
    recv_bytes=1048576,
    send_bytes=1048576,
    max_request_body_size=max_body,
)
