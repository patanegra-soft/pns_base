# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Report HTML written by a user over RPC is sanitized; platform code writes it under sudo."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_mixin_sanitizes_non_sudo_writes(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'models' / 'operation_report_wizard.py').read_text(encoding='utf-8')
    assert 'from odoo.tools import html_sanitize' in src
    assert src.count('if not self.env.su') == 2
    assert "html_sanitize(vals['result_html'])" in src


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_export_wizards_are_created_under_sudo(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'utils' / 'portable_io.py').read_text(encoding='utf-8')
    assert "env[wizard_model].create(" not in src
    assert src.count('env[wizard_model].sudo().create(') == 2
