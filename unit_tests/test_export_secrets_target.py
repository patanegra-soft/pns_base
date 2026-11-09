# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Only ask() says which _pns_export_* method the secrets question calls.

Over RPC an internal user could otherwise create or edit the wizard with any
model and private method, and run it with action_export. The wizard is
loaded on a stand-in ``odoo`` package: no Odoo runtime.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
import types
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STACKS = ['owl1', 'owl2', 'owl3']


class _UserError(Exception):
    pass


class _Env:
    def __init__(self, uid, su=False):
        self.uid = uid
        self.su = su


class _Base:
    """Stand-in for models.TransientModel: create and write record what they get."""

    created = []

    def __init__(self, env, vals=None):
        self.env = env
        self.vals = dict(vals or {})
        self.id = 7

    def sudo(self):
        return type(self)(_Env(self.env.uid, su=True), self.vals)

    def create(self, vals):
        record = type(self)(self.env, vals)
        record.create_uid = self.env.uid
        _Base.created.append(record)
        return record

    def write(self, vals):
        self.vals.update(vals)
        return True


def _field(*_args, **_kwargs):
    return None


def _load_wizard(stack, monkeypatch):
    odoo = types.ModuleType('odoo')
    odoo.api = types.SimpleNamespace(model=lambda fn: fn)
    odoo.fields = types.SimpleNamespace(Char=_field, Boolean=_field)
    odoo.models = types.SimpleNamespace(TransientModel=_Base)
    odoo._ = lambda text: text
    exceptions = types.ModuleType('odoo.exceptions')
    exceptions.UserError = _UserError
    odoo.exceptions = exceptions
    monkeypatch.setitem(sys.modules, 'odoo', odoo)
    monkeypatch.setitem(sys.modules, 'odoo.exceptions', exceptions)
    path = ROOT / 'stacks' / stack / 'pns_base' / 'models' / 'export_secrets_wizard.py'
    spec = importlib.util.spec_from_file_location('export_secrets_wizard_%s' % stack, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.PnsExportSecretsWizard


class _Records:
    _name = 'acme.thing'
    ids = [3, 5]


@pytest.mark.parametrize('stack', STACKS)
def test_ask_creates_as_system_and_the_caller_keeps_the_row(stack, monkeypatch):
    Wizard = _load_wizard(stack, monkeypatch)
    _Base.created = []
    action = Wizard(_Env(uid=42)).ask(_Records(), '_pns_export_acme')
    (row,) = _Base.created
    assert row.env.su is True
    assert row.create_uid == 42
    assert row.vals == {'res_model': 'acme.thing', 'res_ids': '[3, 5]', 'method': '_pns_export_acme'}
    assert action['res_id'] == row.id


@pytest.mark.parametrize('stack', STACKS)
@pytest.mark.parametrize('name', ['res_model', 'res_ids', 'method'])
def test_a_user_cannot_change_what_the_answer_calls(stack, name, monkeypatch):
    Wizard = _load_wizard(stack, monkeypatch)
    wizard = Wizard(_Env(uid=42))
    with pytest.raises(_UserError):
        wizard.write({name: '_pns_export_acme', 'include_secrets': True})
    assert wizard.vals == {}


@pytest.mark.parametrize('stack', STACKS)
def test_a_user_can_tick_the_question(stack, monkeypatch):
    Wizard = _load_wizard(stack, monkeypatch)
    wizard = Wizard(_Env(uid=42))
    wizard.write({'include_secrets': True})
    assert wizard.vals == {'include_secrets': True}


@pytest.mark.parametrize('stack', STACKS)
def test_the_system_can_still_set_the_target(stack, monkeypatch):
    Wizard = _load_wizard(stack, monkeypatch)
    wizard = Wizard(_Env(uid=42, su=True))
    wizard.write({'method': '_pns_export_acme'})
    assert wizard.vals == {'method': '_pns_export_acme'}


@pytest.mark.parametrize('stack', STACKS)
def test_internal_users_cannot_create_the_wizard(stack):
    path = ROOT / 'stacks' / stack / 'pns_base' / 'security' / 'ir.model.access.csv'
    with path.open(encoding='utf-8', newline='') as fh:
        rows = {row['id']: row for row in csv.DictReader(fh)}
    row = rows['access_pns_export_secrets_wizard']
    assert row['group_id:id'] == 'base.group_user'
    assert (row['perm_read'], row['perm_write'], row['perm_create'], row['perm_unlink']) == ('1', '1', '0', '1')
