# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""One picture full screen: the viewer both stacks load."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VIEWER = ROOT / 'common' / 'static' / 'src' / 'js' / 'pns_image_viewer.js'


def test_both_stacks_load_the_viewer():
    owl1 = (ROOT / 'stacks' / 'owl1' / 'pns_base' / 'views' / 'assets.xml').read_text(encoding='utf-8')
    owl2 = (ROOT / 'stacks' / 'owl2' / 'pns_base' / '__manifest__.py').read_text(encoding='utf-8')
    assert 'src="/pns_base/static/src/js/pns_image_viewer.js"' in owl1
    assert 'href="/pns_base/static/src/css/pns_image_viewer.css"' in owl1
    assert "'pns_base/static/src/js/pns_image_viewer.js'," in owl2
    assert "'pns_base/static/src/css/pns_image_viewer.css'," in owl2
    text = VIEWER.read_text(encoding='utf-8')
    assert 'odoo.define' not in text and '@odoo-module' not in text


_SCRIPT = r"""
global.window = { location: { href: 'https://odoo.example/web', origin: 'https://odoo.example' } };
global.document = {};
require(process.argv[2]);
function img(src, link) {
  return {
    tagName: 'IMG', currentSrc: src, getAttribute: function (n) { return n === 'alt' ? 'pic' : src; },
    closest: function () { return link || null; },
  };
}
function link(href, words, pictures) {
  return { href: href, textContent: words || '', querySelectorAll: function () { return new Array(pictures || 1); } };
}
var v = window.pnsImageViewer;
console.log(JSON.stringify({
  odoo: v.optionsFor(img('https://odoo.example/web/image/hr.employee/9/image_128',
                         link('https://odoo.example/web/image/hr.employee/9/image_1920'))),
  other: v.optionsFor(img('https://odoo.example/pns_ai_mcp/remote_image?url=x',
                          link('https://cdn.example/p.png'))),
  bytes: v.optionsFor(img('data:image/png;base64,iVBO')),
  card: v.optionsFor(img('https://odoo.example/a.png', link('https://odoo.example/map', 'Open the map'))),
  words: v.optionsFor({ tagName: 'SPAN' }),
}));
"""


@pytest.mark.skipif(not shutil.which('node'), reason='no node here')
def test_what_a_picture_on_the_page_offers(tmp_path):
    script = tmp_path / 'run.js'
    script.write_text(_SCRIPT, encoding='utf-8')
    out = json.loads(subprocess.run(
        ['node', str(script), str(VIEWER)], capture_output=True, text=True, check=True,
    ).stdout)
    # This site's picture: the link is the larger copy, and the tab.
    assert out['odoo']['full'].endswith('/image_1920')
    assert out['odoo']['tab'].endswith('/image_1920')
    # Another site's: shown as the server brought it; only the tab goes there.
    assert out['other']['full'] == ''
    assert out['other']['tab'] == 'https://cdn.example/p.png'
    # Bytes in the page: no link, the tab opens those same bytes.
    assert out['bytes']['tab'].startswith('data:image/png')
    # A picture inside a link with words belongs to that link.
    assert out['card'] is None
    assert out['words'] is None


_LARGER = r"""
function el() {
  return {
    style: {}, className: '', hidden: true, draggable: false, src: '', alt: '', textContent: '',
    addEventListener: function () {},
    appendChild: function () {},
    setAttribute: function () {},
    removeAttribute: function (name) { if (name === 'src') this.src = ''; },
    classList: { toggle: function () {} },
  };
}
var picture = null;
global.document = {
  createElement: function (tag) {
    var node = el();
    if (tag === 'img' && !picture) picture = node;
    return node;
  },
  body: { appendChild: function () {} },
  addEventListener: function () {},
  removeEventListener: function () {},
};
global.URL = {
  createObjectURL: function () { return 'blob:full'; },
  revokeObjectURL: function () {},
};
global.window = {
  location: { href: 'https://odoo.example/web', origin: 'https://odoo.example' },
  open: function () {},
};
var empty = Uint8Array.from([1, 2, 3]).buffer;
var photo = Uint8Array.from([9, 9, 9, 9]).buffer;
global.fetch = function (url) {
  url = String(url);
  if (url.indexOf('placeholder.png') !== -1) {
    return Promise.resolve({
      ok: true, url: url,
      arrayBuffer: function () { return Promise.resolve(empty); },
    });
  }
  if (url.indexOf('/missing') !== -1) {
    return Promise.resolve({
      ok: true, url: url,
      arrayBuffer: function () { return Promise.resolve(empty.slice(0)); },
    });
  }
  if (url.indexOf('/gone') !== -1) {
    return Promise.resolve({ ok: false, url: url });
  }
  return Promise.resolve({
    ok: true, url: url,
    arrayBuffer: function () { return Promise.resolve(photo); },
  });
};
require(process.argv[2]);
var viewer = window.pnsImageViewer;
var thumb = 'https://odoo.example/web/image/pic.record/4/image_128';
function shot(full) {
  viewer.close();
  return viewer.open({ src: thumb, full: full, tab: full, alt: 'pic' }).then(function () {
    return picture.src;
  });
}
shot('https://odoo.example/web/image/pic.record/4/missing').then(function (missing) {
  return shot('https://odoo.example/web/image/pic.record/4/image_1920').then(function (big) {
    return shot('https://odoo.example/web/image/pic.record/4/gone').then(function (gone) {
      console.log(JSON.stringify({ missing: missing, photo: big, gone: gone }));
    });
  });
}).catch(function (err) {
  console.error(err);
  process.exit(1);
});
"""


@pytest.mark.skipif(not shutil.which('node'), reason='no node here')
def test_the_empty_icon_does_not_replace_the_picture(tmp_path):
    """A missing size comes back as the camera icon with a success status.
    The picture already on screen stays. A real larger file still replaces it."""
    script = tmp_path / 'larger.js'
    script.write_text(_LARGER, encoding='utf-8')
    out = json.loads(subprocess.run(
        ['node', str(script), str(VIEWER)], capture_output=True, text=True, check=True,
    ).stdout)
    assert out['missing'].endswith('/image_128')
    assert out['gone'].endswith('/image_128')
    assert out['photo'] == 'blob:full'
