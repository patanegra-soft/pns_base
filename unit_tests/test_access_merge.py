# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests: old access rows as Odoo 20 ir.access rows (no Odoo runtime)."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'access_merge.py'
    )
    spec = importlib.util.spec_from_file_location('access_merge', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


merge = _load()

USER, WRITER, ADMIN, PORTAL = 1, 2, 3, 4
IMPLIED = {
    USER: {USER},
    WRITER: {WRITER, USER},
    ADMIN: {ADMIN, WRITER, USER},
    PORTAL: {PORTAL},
}
OWN = "[('user_id', '=', user.id)]"
ALL = "[(1, '=', 1)]"


def _acl(group, *ops):
    return {'name': 'acl %s' % group, 'group': group, 'ops': set(ops)}


def _rule(groups, domain, *ops):
    return {'name': 'rule %s' % (groups,), 'groups': list(groups), 'domain': domain, 'ops': set(ops)}


def _rows(acls, rules):
    rows, warnings = merge.merge_model_access(acls, rules, IMPLIED)
    return {(row['group'], row['operation'], row['domain']) for row in rows}, warnings


def test_operation_code_keeps_crud_order():
    assert merge.operation_code({'unlink', 'read', 'create'}) == 'crd'
    assert merge.operation_code(set()) == ''


def test_access_without_rules_grants_the_group():
    rows, warnings = _rows([_acl(USER, 'read', 'write')], [])
    assert rows == {(USER, 'ru', '')}
    assert warnings == []


def test_global_rule_cuts_for_everyone():
    rows, _ = _rows([_acl(USER, 'read')], [_rule((), OWN, 'read', 'write')])
    assert rows == {(None, 'ru', OWN), (USER, 'r', '')}


def test_own_rule_does_not_add_full_access_back():
    rows, warnings = _rows(
        [_acl(USER, 'read'), _acl(ADMIN, 'read', 'unlink')],
        [_rule((USER,), OWN, 'read'), _rule((ADMIN,), ALL, 'read', 'unlink')],
    )
    assert rows == {(USER, 'r', OWN), (ADMIN, 'rd', ALL)}
    assert (USER, 'r', '') not in rows
    assert warnings == []


def test_rule_on_an_operation_without_access_gives_nothing():
    rows, warnings = _rows([_acl(USER, 'read')], [_rule((USER,), OWN, 'read', 'write', 'create', 'unlink')])
    assert rows == {(USER, 'r', OWN)}
    # Where Odoo grants write itself, this rule no longer cuts it: say so.
    assert len(warnings) == 3
    for op in ('create', 'write', 'unlink'):
        assert sum('a %s rule but no access row' % op in w for w in warnings) == 1


def test_rule_on_a_model_without_own_access_is_named():
    rows, warnings = _rows([], [_rule((WRITER,), OWN, 'read')])
    assert rows == set()
    assert len(warnings) == 1 and '[2]' in warnings[0] and 'read' in warnings[0]


def test_uncovered_access_group_is_left_out_and_named():
    rows, warnings = _rows(
        [_acl(USER, 'read'), _acl(PORTAL, 'read')],
        [_rule((USER,), OWN, 'read')],
    )
    assert rows == {(USER, 'r', OWN)}
    assert len(warnings) == 1 and 'group 4' in warnings[0]


def test_rule_group_without_access_is_left_out_and_named():
    rows, warnings = _rows(
        [_acl(WRITER, 'write')],
        [_rule((WRITER,), OWN, 'write'), _rule((PORTAL,), ALL, 'write')],
    )
    assert rows == {(WRITER, 'u', OWN)}
    assert len(warnings) == 1 and 'group 4' in warnings[0]
