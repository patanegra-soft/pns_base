# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2025-2026 Patanegra Soft <https://patanegra.com>
"""Odoo loaders do ast.literal_eval of the whole __manifest__.py."""
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _manifests():
    return (
        ROOT / 'stacks' / 'owl1' / 'pns_base' / '__manifest__.py',
        ROOT / 'stacks' / 'owl2' / 'pns_base' / '__manifest__.py',
    )


def test_manifests_are_literals():
    for path in _manifests():
        info = ast.literal_eval(path.read_text(encoding='utf-8'))
        assert isinstance(info, dict)
        assert info.get('name')
        assert info.get('version')
