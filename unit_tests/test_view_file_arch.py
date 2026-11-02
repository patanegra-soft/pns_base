# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Odoo 19 validates the file arch. The converter has to run on that read."""
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_file_arch_is_converted_before_the_odoo19_check():
    for rel in (
        'stacks/owl1/pns_base/models/ir_ui_view_patch.py',
        'stacks/owl2/pns_base/models/ir_ui_view_patch.py',
    ):
        text = (_ROOT / rel).read_text(encoding='utf-8')
        body = text.split('def _compute_arch')[1].split('\n    def ')[0]
        assert '_auto_convert_attrs' in body
        assert 'applies_attrs_convert' in body
