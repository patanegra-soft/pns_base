# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Report headings go through _() and the catalog has them as code terms."""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CATALOGS = {'owl1': 'es.po', 'owl2': 'es_ES.po'}
CODE_REF = '#: code:addons/pns_base/utils/ui_feedback.py:0'


def _entry(po, msgid):
    for block in po.split('\n\n'):
        if '\nmsgid "%s"\n' % msgid in '\n' + block + '\n':
            return block
    return ''


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_report_headings_are_translated(stack):
    base = ROOT / 'stacks' / stack / 'pns_base'
    src = (base / 'utils' / 'ui_feedback.py').read_text(encoding='utf-8')
    po = (base / 'i18n' / CATALOGS[stack]).read_text(encoding='utf-8').replace('\r\n', '\n')
    for msgid in ('Warnings', 'Errors', 'Errors (%s):'):
        assert "_('%s')" % msgid in src
        entry = _entry(po, msgid)
        assert CODE_REF in entry, msgid
        assert 'msgstr ""' not in entry, msgid


def test_owl2_code_terms_carry_the_loader_flag():
    """Odoo 16+ only loads a code term whose entry says odoo-python / odoo-javascript."""
    po = (ROOT / 'stacks' / 'owl2' / 'pns_base' / 'i18n' / 'es_ES.po').read_text(
        encoding='utf-8').replace('\r\n', '\n')
    missing = []
    for block in po.split('\n\n'):
        lines = block.split('\n')
        if any(re.match(r'#: code:\S+\.py', l) for l in lines):
            flag = '#. odoo-python'
        elif any(re.match(r'#: code:\S+\.(js|xml)', l) for l in lines):
            flag = '#. odoo-javascript'
        else:
            continue
        if flag not in lines:
            missing.append(next(l for l in lines if l.startswith('msgid')))
    assert not missing, missing
