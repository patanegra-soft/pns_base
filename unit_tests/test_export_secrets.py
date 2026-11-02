# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Every export asks for secrets (off by default); an import never blanks one."""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STACKS = ['owl1', 'owl2']


def _portable(stack):
    path = ROOT / 'stacks' / stack / 'pns_base' / 'utils' / 'portable_io.py'
    spec = importlib.util.spec_from_file_location('portable_io_%s' % stack, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Rec:
    _pns_secret_fields = ('api_key', 'env_vars')

    def __init__(self, values=None):
        self._values = values

    def __getitem__(self, key):
        if isinstance(key, slice):
            return self
        return self._values[key]

    def __bool__(self):
        return self._values is not None

    def sudo(self):
        return self


@pytest.mark.parametrize('stack', STACKS)
def test_empty_secret_never_blanks_a_stored_one(stack):
    keep = _portable(stack).keep_existing_secrets
    rec = _Rec({'api_key': 'sk-old', 'env_vars': '{"K": "v"}'})
    vals = keep(rec, {'name': 'p', 'api_key': '', 'env_vars': '{}'})
    assert vals == {'name': 'p'}


@pytest.mark.parametrize('stack', STACKS)
def test_a_file_with_secrets_overwrites(stack):
    keep = _portable(stack).keep_existing_secrets
    rec = _Rec({'api_key': 'sk-old', 'env_vars': '{}'})
    vals = keep(rec, {'api_key': 'sk-new', 'env_vars': '{"K": "v"}'})
    assert vals == {'api_key': 'sk-new', 'env_vars': '{"K": "v"}'}


@pytest.mark.parametrize('stack', STACKS)
def test_new_record_takes_what_comes(stack):
    keep = _portable(stack).keep_existing_secrets
    assert keep(_Rec(), {'api_key': ''}) == {'api_key': ''}


class _Field:
    def __init__(self, ftype='char'):
        self.type = ftype


class _Row:
    _pns_secret_fields = ('api_key',)
    _fields = {'name': _Field(), 'api_key': _Field()}

    def __getitem__(self, key):
        return {'name': 'p', 'api_key': 'sk-1'}[key]


@pytest.mark.parametrize('stack', STACKS)
def test_record_export_leaves_secrets_out_unless_asked(stack):
    export = _portable(stack).export_record_dict
    assert export(_Row()) == {'name': 'p'}
    assert export(_Row(), include_secrets=True) == {'name': 'p', 'api_key': 'sk-1'}


def _settings(stack):
    path = ROOT / 'stacks' / stack / 'pns_base' / 'utils' / 'settings_io.py'
    spec = importlib.util.spec_from_file_location('settings_io_%s' % stack, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Setting:
    type = 'char'
    config_parameter = 'mod.api_key'


@pytest.mark.parametrize('stack', STACKS)
def test_empty_secret_setting_never_blanks_a_stored_one(stack):
    sio = _settings(stack)
    catalog = [('api_key', _Setting())]
    overlay, _w, skipped, _e = sio.resolve_import_overlay(
        {'mod.api_key': ''}, catalog, {'api_key': 'sk-old'}, icp_prefix='mod.',
    )
    assert overlay == {} and skipped == 1
    overlay, _w, _s, _e = sio.resolve_import_overlay(
        {'mod.api_key': 'sk-new'}, catalog, {'api_key': 'sk-old'}, icp_prefix='mod.',
    )
    assert overlay == {'api_key': 'sk-new'}


@pytest.mark.parametrize('stack', STACKS)
def test_question_starts_unticked(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'models' / 'export_secrets_wizard.py').read_text(encoding='utf-8')
    field = src.split('include_secrets = fields.Boolean(', 1)[1].split(')', 1)[0]
    assert 'default=False' in field
    assert "method.startswith(_METHOD_PREFIX)" in src.split('def action_export', 1)[1]
