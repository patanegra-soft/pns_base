# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""One full-screen panel at a time: the coordinator both stacks load."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAYER = ROOT / 'common' / 'static' / 'src' / 'js' / 'pns_layer.js'


def test_both_stacks_load_the_layer():
    owl1 = (ROOT / 'stacks' / 'owl1' / 'pns_base' / 'views' / 'assets.xml').read_text(encoding='utf-8')
    owl2 = (ROOT / 'stacks' / 'owl2' / 'pns_base' / '__manifest__.py').read_text(encoding='utf-8')
    assert 'src="/pns_base/static/src/js/pns_layer.js"' in owl1
    assert "'pns_base/static/src/js/pns_layer.js'," in owl2
    # A plain script: the same file has to run on Odoo 14 and 17+.
    text = LAYER.read_text(encoding='utf-8')
    assert 'odoo.define' not in text and '@odoo-module' not in text


_SCRIPT = r"""
var listeners = [];
global.window = {};
global.document = { addEventListener: function (n, fn) { listeners.push(fn); } };
require(process.argv[2]);
var layer = window.pnsLayer, hidden = [];
function el(inNavbar, toggle) {
  return { closest: function (sel) {
    if (sel === '.o_main_navbar') return inNavbar;
    if (sel === '[data-pns-layer-toggle]') return toggle;
    return null;
  } };
}
function click(target) { listeners.forEach(function (fn) { fn({ target: target }); }); }
function hide(key) { return function () { hidden.push(key); }; }
layer.claim('a', hide('a'));
layer.claim('b', hide('b'));
click(el(true, true));
click(el(false, false));
click(el(true, false));
var afterNavbar = hidden.join(',');
hidden = [];
layer.claim('a', hide('a'));
layer.release('b');
layer.claim('c', hide('c'));
var stranger = hidden.join(',');
hidden = [];
layer.release('c');
layer.claim('d', hide('d'));
console.log([afterNavbar, stranger, hidden.join(',') || '-'].join('|'));
"""


@pytest.mark.skipif(not shutil.which('node'), reason='no node here')
def test_one_panel_at_a_time(tmp_path):
    script = tmp_path / 'run.js'
    script.write_text(_SCRIPT, encoding='utf-8')
    out = subprocess.run(
        ['node', str(script), str(LAYER)], capture_output=True, text=True, check=True,
    ).stdout.strip()
    # b hides a; its own toggle and a click outside the navbar leave b;
    # a navbar click hides b. Releasing someone else's key leaves the
    # panel that is showing. Releasing the one showing leaves the next claim alone.
    assert out == 'a,b|a|-'
