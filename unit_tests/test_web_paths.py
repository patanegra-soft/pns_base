# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""The Odoo 16 web paths shim adds no dependency on Odoo 17+.

Odoo 17+ wraps every static/src file in odoo.define and lists each
require("quoted name") as a dependency. A 16-only name there is a missing
module, and Odoo shows its red banner on every page.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# The same pattern Odoo's js_transpiler uses to collect dependencies.
_REQUIRE = re.compile(r"""^[^/*\n]*require\((["'`])([^"'`]+)\1\)""", re.M)


@pytest.mark.parametrize('stack', ('owl2', 'owl3'))
def test_the_shim_requires_no_quoted_name(stack):
    path = ROOT / 'stacks' / stack / 'pns_base' / 'static' / 'src' / 'js' / 'pns_web_paths.js'
    text = path.read_text(encoding='utf-8')
    # Odoo 16 must still load it as a plain script (its own marker check).
    assert not re.match(r'\s*/(\*|/).*\s*@odoo-module', text)
    assert _REQUIRE.findall(text) == []
