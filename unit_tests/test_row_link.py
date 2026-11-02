# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""List many2one: open the row, then the linked record, and keep the row."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_both_stacks_open_the_row_before_the_link():
    owl1 = (ROOT / 'stacks' / 'owl1' / 'pns_base' / 'views' / 'assets.xml').read_text(
        encoding='utf-8',
    )
    owl2 = (ROOT / 'stacks' / 'owl2' / 'pns_base' / '__manifest__.py').read_text(
        encoding='utf-8',
    )
    assert 'src="/pns_base/static/src/js/pns_row_link_v14.js"' in owl1
    assert "'pns_base/static/src/js/pns_row_link.js'," in owl2
    assert "'pns_base/static/src/xml/pns_row_link.xml'," in owl2
    drawn = (
        ROOT / 'stacks' / 'owl1' / 'pns_base' / 'static' / 'src' / 'js'
        / 'pns_row_link_v14.js'
    ).read_text(encoding='utf-8')
    kept = (
        ROOT / 'stacks' / 'owl2' / 'pns_base' / 'static' / 'src' / 'js' / 'pns_row_link.js'
    ).read_text(encoding='utf-8')
    for text in (drawn, kept):
        assert 'get_formview_action' in text
        assert 'secretary' not in text
        assert 'account.move' not in text
    assert 'var rowModel = this.record && this.record.model' in drawn
    assert 'res_model: rowModel' in drawn
    assert 'model: relation' in drawn
    assert "this.$el.attr('href', '#')" in drawn
    assert "action.target = 'current'" in drawn
    assert 'delete action.id' in drawn
    assert 'const rowModel = this.props.record.resModel' in kept
    assert 'res_model: rowModel' in kept
    assert 'linked.target = "current"' in kept
    assert 'delete linked.id' in kept
    xml = (
        ROOT / 'stacks' / 'owl2' / 'pns_base' / 'static' / 'src' / 'xml' / 'pns_row_link.xml'
    ).read_text(encoding='utf-8')
    assert 'href="#"' in xml
