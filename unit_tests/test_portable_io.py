# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Unit tests: suite portable_io (no Odoo runtime)."""
from __future__ import annotations

import importlib.util
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'portable_io.py'
    )
    spec = importlib.util.spec_from_file_location('portable_io', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


pio = _load()


class FakeField:
    def __init__(
        self,
        type='char',
        compute=None,
        store=False,
        inverse=None,
        related=None,
        selection=None,
    ):
        self.type = type
        self.compute = compute
        self.store = store
        self.inverse = inverse
        self.related = related
        self.selection = selection


class FakeRecord:
    def __init__(self, fields_map, values):
        self._fields = fields_map
        self._values = values

    def __getitem__(self, name):
        return self._values[name]


def _place_fields():
    return {
        'id': FakeField(type='integer'),
        'query_key': FakeField(),
        'lat': FakeField(type='float'),
        'notes': FakeField(),
        'corrected': FakeField(type='boolean'),
        'place_thumb': FakeField(type='binary'),
        'partner_id': FakeField(type='many2one'),
        'is_shared': FakeField(type='boolean', compute='_c', store=False),
        'ghost': FakeField(),
    }


def test_filename_geo_has_no_db():
    env = SimpleNamespace(cr=SimpleNamespace(dbname='acme-odoo14'))
    name = pio.build_export_filename(env, 'geo_places', 'json', style='geo')
    assert name.endswith('_geo_places.json')
    assert 'T' not in name.split('_')[0]
    assert 'acme' not in name


def test_filename_mcp_includes_db_and_iso_t():
    env = SimpleNamespace(cr=SimpleNamespace(dbname='acme-odoo14'))
    name = pio.build_export_filename(
        env, 'ai_config_backup', 'json', tag='piloto', style='mcp',
    )
    assert name.endswith('_piloto_ai_config_backup.json')
    assert 'acme-odoo14' in name
    assert 'T' in name.split('_')[0]


def test_filename_says_secrets_when_the_file_carries_them():
    env = SimpleNamespace(cr=SimpleNamespace(dbname='db1'))
    assert pio.build_export_filename(env, 'ai_providers', 'json', secrets=True).endswith(
        '_ai_providers_secrets.json')
    assert pio.build_export_filename(
        env, 'bundle', 'zip', style='geo', secrets=True,
    ).endswith('_bundle_secrets.zip')
    assert 'secrets' not in pio.build_export_filename(env, 'ai_providers', 'json')


def test_extract_json_list():
    raw = json.dumps([{'a': 1}]).encode('utf-8')
    data, warnings = pio.extract_json_from_upload(raw)
    assert data == [{'a': 1}]
    assert not warnings


def test_extract_wraps_single_object():
    raw = json.dumps({'a': 1}).encode('utf-8')
    data, warnings = pio.extract_json_from_upload(raw)
    assert data == [{'a': 1}]
    assert any('wrapped' in w.lower() for w in warnings)


def test_extract_zip_merges_and_skips_broken():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as zf:
        zf.writestr('maps/one.json', json.dumps({'token': 'a'}))
        zf.writestr('maps/two.json', json.dumps([{'token': 'b'}]))
        zf.writestr('maps/bad.json', b'{not json')
        zf.writestr('__manifest__.json', json.dumps({'count': 2}))
    data, warnings = pio.extract_json_from_upload(buf.getvalue())
    tokens = {row['token'] for row in data}
    assert tokens == {'a', 'b'}
    assert any('bad.json' in w for w in warnings)


def test_export_skips_binary_relation_and_computed():
    rec = FakeRecord(_place_fields(), {
        'id': 9,
        'query_key': 'madrid',
        'lat': 40.4,
        'notes': 'ok',
        'corrected': True,
        'place_thumb': b'x',
        'partner_id': 3,
        'is_shared': True,
        'ghost': 'live',
    })
    data = pio.export_record_dict(rec)
    assert data['query_key'] == 'madrid'
    assert data['ghost'] == 'live'
    assert 'id' not in data
    assert 'place_thumb' not in data
    assert 'partner_id' not in data
    assert 'is_shared' not in data


def test_export_only_fields_and_extra():
    rec = FakeRecord(_place_fields(), {
        'id': 1,
        'query_key': 'x',
        'lat': 1.0,
        'notes': 'n',
        'corrected': False,
        'place_thumb': False,
        'partner_id': False,
        'is_shared': False,
        'ghost': 'g',
    })
    data = pio.export_record_dict(
        rec, only_fields=('query_key', 'lat'), extra={'user': 'admin'},
    )
    assert set(data) == {'query_key', 'lat', 'user'}


def test_import_unknown_field_warns_and_keeps_rest():
    model = FakeRecord(_place_fields(), {})
    vals, warnings = pio.import_vals_from_dict(
        model,
        {
            'query_key': 'madrid',
            'does_not_exist': 1,
            'corrected': True,
            'requested_by_login': 'admin',
        },
        skip_fields={'requested_by_login'},
    )
    assert vals['query_key'] == 'madrid'
    assert vals['corrected'] is True
    assert any('does_not_exist' in w for w in warnings)
    assert not any('requested_by_login' in w for w in warnings)


def test_empty_selection_is_unset_not_a_warning():
    fields_map = {
        'compose': FakeField(
            type='selection',
            selection=[
                ('compose-agent', 'compose-agent'),
                ('compose-model', 'compose-model'),
            ],
        ),
    }
    model = FakeRecord(fields_map, {})
    for empty in ('', None, False):
        vals, warnings = pio.import_vals_from_dict(model, {'compose': empty})
        assert vals.get('compose') is False
        assert not warnings


def test_method_selection_rejects_a_value_outside_the_list():
    def _states(model):
        return [('draft', 'Draft'), ('done', 'Done')]

    fields_map = {
        'state': FakeField(type='selection', selection=_states),
    }
    model = FakeRecord(fields_map, {})
    vals, warnings = pio.import_vals_from_dict(
        model, {'state': 'nope'},
    )
    assert 'state' not in vals
    assert warnings


def test_owl1_portable_io_reads_method_selections():
    text = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl1' / 'pns_base' / 'utils' / 'portable_io.py'
    ).read_text(encoding='utf-8')
    assert 'def _selection_values' in text
    assert "value in (None, False, '')" in text
