# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests: Binary field bytes on every series (no Odoo runtime)."""
from __future__ import annotations

import base64
import importlib.util
import sys
import types
from pathlib import Path

_UTILS = Path(__file__).resolve().parents[1] / 'stacks' / 'owl2' / 'pns_base' / 'utils'


def _load_compat(major):
    odoo = types.ModuleType('odoo')
    odoo.release = types.SimpleNamespace(version_info=(major, 0))
    http = types.ModuleType('odoo.http')
    stream = types.ModuleType('odoo.http.stream')
    http.content_disposition = stream.content_disposition = lambda name: name
    saved = {k: sys.modules.get(k) for k in ('odoo', 'odoo.http', 'odoo.http.stream')}
    sys.modules.update({'odoo': odoo, 'odoo.http': http, 'odoo.http.stream': stream})
    try:
        spec = importlib.util.spec_from_file_location('compat_%s' % major, _UTILS / 'compat.py')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        for key, value in saved.items():
            if value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = value


class BinaryValue:
    """Odoo 20 shape: a buffer over the decoded content."""

    def __init__(self, content):
        self.content = content

    def __bool__(self):
        return bool(self.content)

    def __bytes__(self):
        return self.content


def test_up_to_19_the_field_reads_as_base64():
    compat = _load_compat(19)
    payload = b'[{"name": "ACME"}]'
    assert compat.binary_bytes(base64.b64encode(payload)) == payload
    assert compat.binary_bytes(base64.b64encode(payload).decode()) == payload


def test_20_the_field_already_holds_the_bytes():
    compat = _load_compat(20)
    payload = b'[{"name": "ACME"}]'
    assert compat.binary_bytes(BinaryValue(payload)) == payload


def test_empty_is_empty_bytes():
    for major in (14, 19, 20):
        compat = _load_compat(major)
        assert compat.binary_bytes(False) == b''
        assert compat.binary_bytes(None) == b''
    assert _load_compat(20).binary_bytes(BinaryValue(b'')) == b''


def test_export_attachment_stores_raw_bytes():
    spec = importlib.util.spec_from_file_location('portable_io_raw', _UTILS / 'portable_io.py')
    pio = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pio)
    created = []

    class Attachment:
        def create(self, vals):
            created.append(vals)
            return vals

    pio.write_export_attachment({'ir.attachment': Attachment()}, 'x.json', b'{}')
    assert created[0]['raw'] == b'{}'
    assert 'datas' not in created[0]
