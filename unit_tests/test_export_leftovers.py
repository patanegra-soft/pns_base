# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Export files go away with their download wizard; settings leave secrets out unless asked."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_download_wizard_takes_its_file_with_it(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'models' / 'export_file_wizard.py').read_text(encoding='utf-8')
    body = src.split('def unlink(self):', 1)[1]
    assert "self.sudo().mapped('attachment_id')" in body
    assert 'files.unlink()' in body


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_settings_export_skips_secrets_by_default(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'utils' / 'settings_io.py').read_text(encoding='utf-8')
    head = src.split('def export_settings(', 1)[1].split(')', 1)[0]
    assert 'include_secrets=False' in head
