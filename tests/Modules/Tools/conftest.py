"""
Conftest for tests/Modules/Tools.

Stubs heavy cross-module dependencies that tools_device_lookup imports
lazily (inside function bodies). These are installed with setdefault() so
they never override a real module already loaded.
"""

import sys
import types
from unittest.mock import MagicMock
import pytest


def _make_stub(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# Stub modules imported inside function bodies of tools_device_lookup / tools_mac_capa
# to avoid pulling in unrelated heavy dependencies during test collection.
_STUBS = {
    "Modules.zigateConsts": dict(HEARTBEAT=1),
}

for _name, _attrs in _STUBS.items():
    sys.modules.setdefault(_name, _make_stub(_name, **_attrs))
