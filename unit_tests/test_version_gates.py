# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Unit tests: version gates (no Odoo runtime)."""
from __future__ import annotations

import importlib.util
from pathlib import Path


def _load():
    path = (
        Path(__file__).resolve().parents[1]
        / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'version_gates.py'
    )
    spec = importlib.util.spec_from_file_location('version_gates', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gates = _load()


def test_thresholds():
    assert gates.ATTRS_CONVERT_FROM == 17
    assert gates.TREE_TO_LIST_FROM == 18
    assert gates.GROUP_PRIVILEGE_FROM == 19


def test_tree_to_list_starts_at_18():
    assert not gates.applies_tree_to_list(17)
    assert gates.applies_tree_to_list(18)
    assert gates.applies_tree_to_list(19)
    assert gates.applies_attrs_convert(17)


def test_privilege_only_on_19():
    vals17 = {'name': 'Writer', 'category_id': 5}
    gates.rewrite_group_vals(vals17, 17, {'category_id': True, 'users': True})
    assert vals17['category_id'] == 5
    assert 'privilege_id' not in vals17

    vals19 = {'name': 'Writer', 'category_id': 5, 'users': [(4, 1)]}
    gates.rewrite_group_vals(
        vals19, 19,
        {'privilege_id': True, 'user_ids': True},
        privilege_id=9,
    )
    assert 'category_id' not in vals19
    assert vals19['privilege_id'] == 9
    assert 'users' not in vals19
    assert vals19['user_ids'] == [(4, 1)]
