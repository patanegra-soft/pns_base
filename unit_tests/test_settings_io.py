# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests: suite settings_io (no Odoo runtime)."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'settings_io.py'
    )
    spec = importlib.util.spec_from_file_location('settings_io', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sio = _load()
MODULE = 'demo_mod'
PREFIX = 'demo.'


class FakeField:
    def __init__(
        self,
        type='char',
        config_parameter=None,
        _module=MODULE,
        default=None,
        selection=None,
        related=None,
        automatic=False,
        _modules=None,
    ):
        self.type = type
        self.config_parameter = config_parameter
        self._module = _module
        self._modules = _modules if _modules is not None else (
            (_module,) if _module else ()
        )
        self.default = default
        self.selection = selection
        self.related = related
        self.automatic = automatic


class FakeModel:
    def __init__(self, fields_map):
        self._fields = fields_map


def _catalog():
    return FakeModel({
        'id': FakeField(type='integer', _module='base'),
        'company_id': FakeField(type='many2one', _module='base'),
        'api_key': FakeField(
            type='char', config_parameter='demo.api_key', default='',
        ),
        'max_items': FakeField(
            type='integer', config_parameter='demo.max_items', default=10,
        ),
        'enabled': FakeField(
            type='boolean', config_parameter='demo.enabled', default=False,
        ),
        'other_app_flag': FakeField(
            type='boolean', config_parameter='other.flag', _module='other_app',
        ),
    })


def test_discover_only_module_or_prefix_fields():
    names = [
        n for n, _f in sio.iter_settings_fields(
            _catalog(), module=MODULE, icp_prefix=PREFIX,
        )
    ]
    assert 'api_key' in names
    assert 'max_items' in names
    assert 'enabled' in names
    assert 'id' not in names
    assert 'company_id' not in names
    assert 'other_app_flag' not in names


def test_discover_by_module_without_config_parameter():
    model = FakeModel({
        'new_knob': FakeField(type='integer', _module=MODULE, default=1),
        'unrelated': FakeField(type='char', _module='mail', default=''),
    })
    names = [
        n for n, _f in sio.iter_settings_fields(
            model, module=MODULE, icp_prefix=PREFIX,
        )
    ]
    assert names == ['new_knob']


def test_new_field_exported_without_closed_list():
    model = _catalog()
    model._fields['brand_new'] = FakeField(
        type='char', config_parameter='demo.brand_new', default='',
    )
    catalog = list(sio.iter_settings_fields(
        model, module=MODULE, icp_prefix=PREFIX,
    ))
    payload = sio.collect_settings_payload(
        {'brand_new': 'hello', 'api_key': 'secret'},
        catalog,
        include_secrets=True,
        icp_prefix=PREFIX,
    )
    assert payload['demo.brand_new'] == 'hello'
    assert payload['demo.api_key'] == 'secret'


def test_secrets_redacted_when_asked():
    catalog = list(sio.iter_settings_fields(
        _catalog(), module=MODULE, icp_prefix=PREFIX,
    ))
    values = {'api_key': 'secret', 'max_items': 4, 'enabled': False}
    redacted = sio.collect_settings_payload(
        values, catalog, include_secrets=False, icp_prefix=PREFIX,
    )
    assert 'demo.api_key' not in redacted
    assert redacted['demo.max_items'] == 4


def test_unknown_attribute_does_not_stop_import():
    catalog = list(sio.iter_settings_fields(
        _catalog(), module=MODULE, icp_prefix=PREFIX,
    ))
    overlay, warnings, skipped, errors = sio.resolve_import_overlay(
        {
            'demo.does_not_exist': 'whatever',
            'ghost_field': 1,
            'demo.max_items': 9,
            'api_key': 'keep-going',
        },
        catalog,
        {'max_items': 10, 'api_key': 'old'},
        icp_prefix=PREFIX,
    )
    assert overlay['max_items'] == 9
    assert overlay['api_key'] == 'keep-going'
    assert skipped == 2
    assert not errors
    assert any('does_not_exist' in w for w in warnings)


def test_persist_skips_failed_key_and_writes_the_rest():
    catalog = list(sio.iter_settings_fields(
        _catalog(), module=MODULE, icp_prefix=PREFIX,
    ))
    overlay = {'max_items': 11, 'api_key': 'ok'}

    class FakeICP:
        def __init__(self):
            self.params = {}

        def set_param(self, key, value):
            if key == 'demo.max_items':
                raise RuntimeError('disk full')
            self.params[key] = value

    icp = FakeICP()
    updated, skipped, warnings = sio.persist_settings_overlay(
        icp, overlay, catalog, overlay, icp_prefix=PREFIX,
    )
    assert updated == 1
    assert skipped == 1
    assert icp.params == {'demo.api_key': 'ok'}
    assert any('max_items' in w for w in warnings)


def test_callable_default_uses_the_recordset():
    seen = []

    def _default(records):
        seen.append(records)
        return 'from-record'

    field = FakeField(type='char', default=_default)
    assert sio.field_default(field, records='empty') == 'from-record'
    assert seen == ['empty']


def test_callable_default_that_needs_env_falls_back():
    def _default(records):
        return records.env['ir.config_parameter']

    field = FakeField(type='integer', default=_default)
    assert sio.field_default(field) == 0


def test_owl1_settings_io_matches_the_recordset_default():
    text = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl1' / 'pns_base' / 'utils' / 'settings_io.py'
    ).read_text(encoding='utf-8')
    assert 'def field_default(field, records=None)' in text
    assert 'return default(records)' in text
