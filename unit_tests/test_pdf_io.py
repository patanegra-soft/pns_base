# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""PDF on bytes: text when the PDF has it, page pictures when it is scanned."""
from __future__ import annotations

import importlib.util
import io
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
STACKS = ('owl1', 'owl2')
_PATH = ROOT / 'stacks' / 'owl2' / 'pns_base' / 'utils' / 'pdf_io.py'
_spec = importlib.util.spec_from_file_location('pdf_io', _PATH)
pdf_io = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pdf_io)

_HAS_PDF = any(
    importlib.util.find_spec(name) is not None for name in ('pypdf', 'PyPDF2')
)


def _none(*args):
    return []


def _blank(*args):
    return []


def _build(objs):
    out = io.BytesIO()
    out.write(b'%PDF-1.4\n')
    offs = []
    for i, obj in enumerate(objs, 1):
        offs.append(out.tell())
        out.write(b'%d 0 obj\n' % i + obj + b'\nendobj\n')
    xref = out.tell()
    out.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objs) + 1))
    for off in offs:
        out.write(b'%010d 00000 n \n' % off)
    out.write(b'trailer<</Size %d/Root 1 0 R>>\nstartxref\n%d\n%%%%EOF' % (len(objs) + 1, xref))
    return out.getvalue()


def _text_pdf(line):
    content = b'BT /F1 12 Tf 50 800 Td (' + line + b') Tj ET'
    return _build([
        b'<</Type/Catalog/Pages 2 0 R>>',
        b'<</Type/Pages/Kids[3 0 R]/Count 1>>',
        b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]'
        b'/Resources<</Font<</F1 4 0 R>>>>/Contents 5 0 R>>',
        b'<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>',
        b'<</Length %d>>stream\n' % len(content) + content + b'\nendstream',
    ])


def test_both_stacks_ship_the_same_file():
    owl1 = (ROOT / 'stacks' / 'owl1' / 'pns_base' / 'utils' / 'pdf_io.py').read_bytes()
    assert owl1 == _PATH.read_bytes()
    text = _PATH.read_text(encoding='utf-8')
    # No Odoo and no AI: the caller hands the pictures to its own providers.
    assert 'import odoo' not in text and 'from odoo' not in text
    assert 'ai.execution' not in text and 'ai.agent' not in text


@pytest.mark.skipif(not _HAS_PDF, reason='no PDF library here')
def test_a_pdf_with_text_gives_its_text_and_no_picture(monkeypatch):
    raw = _text_pdf(b'Factura 2026-17 Total 121,00 EUR')
    assert 'Factura 2026-17' in pdf_io.pdf_text(raw)
    monkeypatch.setattr(pdf_io, '_drawn_fitz', _none)
    monkeypatch.setattr(pdf_io, '_drawn_tool', _none)
    assert pdf_io.pdf_pictures(raw) == []


def test_a_renderer_draws_the_page_before_trusting_pictures_inside(monkeypatch):
    """A logo is the only picture inside a program-made PDF. The drawn page wins."""
    monkeypatch.setattr(pdf_io, '_embedded', lambda *a: [b'\xff\xd8\xfflogo'])
    monkeypatch.setattr(pdf_io, '_drawn_fitz', lambda *a: [b'\xff\xd8\xffpage'])
    assert pdf_io.pdf_pictures(b'%PDF') == [b'\xff\xd8\xffpage']
    monkeypatch.setattr(pdf_io, '_drawn_fitz', _none)
    monkeypatch.setattr(pdf_io, '_drawn_tool', _none)
    assert pdf_io.pdf_pictures(b'%PDF') == [b'\xff\xd8\xfflogo']


def test_the_caller_says_how_many_pages_and_how_big(monkeypatch):
    seen = []
    monkeypatch.setattr(pdf_io, '_drawn_fitz', lambda *a: seen.append(a[1:]) or [b'x'])
    pdf_io.pdf_pictures(b'%PDF', pages=1, dpi=40, side=240)
    assert seen == [(1, 40, 240)]
    asked = []
    monkeypatch.setattr(pdf_io, '_text_fitz', lambda raw, pages: asked.append(pages) or [])
    monkeypatch.setattr(pdf_io, '_text_pdfminer', _blank)
    monkeypatch.setattr(pdf_io, '_text_pypdf', _blank)
    pdf_io.pdf_text(b'%PDF', pages=50)
    assert asked == [50]


@pytest.mark.skipif(not _HAS_PDF, reason='no PDF library here')
def test_a_scanned_pdf_gives_a_jpeg_and_no_text():
    from PIL import Image

    buf = io.BytesIO()
    Image.new('RGB', (1200, 1600), 'white').save(buf, format='PDF')
    raw = buf.getvalue()
    assert pdf_io.pdf_text(raw) == ''
    pictures = pdf_io.pdf_pictures(raw)
    assert len(pictures) == 1 and pictures[0][:3] == b'\xff\xd8\xff'


def test_a_photo_file_becomes_a_jpeg_and_other_bytes_do_not():
    from PIL import Image

    buf = io.BytesIO()
    Image.new('RGB', (800, 600), 'white').save(buf, format='PNG')
    jpeg = pdf_io.as_picture(buf.getvalue())
    assert jpeg[:3] == b'\xff\xd8\xff'
    assert pdf_io.as_picture(b'just some text') is None
    assert not pdf_io.is_pdf(buf.getvalue())
    assert pdf_io.is_pdf(b'  %PDF-1.4 ...')


def _picture(fmt, size=(40, 20), mode='RGB', color='white', **save):
    from PIL import Image

    out = io.BytesIO()
    Image.new(mode, size, color).save(out, format=fmt, **save)
    return out.getvalue()


def test_what_was_transparent_turns_white_not_black():
    from PIL import Image

    clear = _picture('PNG', mode='RGBA', color=(0, 0, 0, 0))
    jpeg = pdf_io.as_picture(clear)
    assert Image.open(io.BytesIO(jpeg)).getpixel((5, 5)) >= (250, 250, 250)


def test_a_photo_stays_jpeg_and_a_screenshot_stays_png():
    from PIL import Image

    photo, kind = pdf_io.shrink_picture(_picture('JPEG', size=(4000, 3000)), side=768)
    assert kind == 'image/jpeg'
    assert max(Image.open(io.BytesIO(photo)).size) == 768
    shot, kind = pdf_io.shrink_picture(_picture('PNG', mode='RGBA', color=(0, 0, 0, 0)))
    assert kind == 'image/png'
    assert Image.open(io.BytesIO(shot)).mode == 'RGBA'
    gif, kind = pdf_io.shrink_picture(_picture('GIF', mode='P', color=1))
    assert kind == 'image/png'
    assert pdf_io.shrink_picture(b'just some text') is None


def test_a_phone_photo_held_upright_comes_back_upright():
    from PIL import Image

    image = Image.new('RGB', (400, 300), 'white')
    exif = image.getexif()
    exif[0x0112] = 6  # the camera was turned: show it 90 degrees clockwise
    out = io.BytesIO()
    image.save(out, format='JPEG', exif=exif.tobytes())
    raw = out.getvalue()
    assert pdf_io.picture_size(raw) == (300, 400)
    small, _kind = pdf_io.shrink_picture(raw, side=200)
    assert Image.open(io.BytesIO(small)).size == (150, 200)


def test_a_picture_turns_in_its_own_format():
    from PIL import Image

    turned = pdf_io.turn_picture(_picture('PNG', size=(400, 300)), 90)
    image = Image.open(io.BytesIO(turned))
    assert image.format == 'PNG' and image.size == (300, 400)
    assert pdf_io.turn_picture(b'not a picture', 90) is None


@pytest.mark.skipif(not _HAS_PDF, reason='no PDF library here')
def test_a_picture_becomes_a_one_page_pdf():
    sheet = pdf_io.picture_pdf(_picture('PNG', size=(400, 300)))
    assert pdf_io.is_pdf(sheet)
    assert len(pdf_io.reader(sheet).pages) == 1
    assert pdf_io.picture_pdf(b'not a picture') is None


@pytest.mark.skipif(not _HAS_PDF, reason='no PDF library here')
def test_a_logo_inside_a_text_page_is_not_a_scan(monkeypatch):
    """A 400px logo on an A4 sheet is not the document. Drawing the page is."""
    from PIL import Image

    logo = io.BytesIO()
    Image.new('RGB', (400, 400), 'red').save(logo, format='JPEG')
    jpeg = logo.getvalue()
    raw = _build([
        b'<</Type/Catalog/Pages 2 0 R>>',
        b'<</Type/Pages/Kids[3 0 R]/Count 1>>',
        b'<</Type/Page/Parent 2 0 R/MediaBox[0 0 595 842]'
        b'/Resources<</XObject<</Im1 4 0 R>>>>/Contents 5 0 R>>',
        b'<</Type/XObject/Subtype/Image/Width 400/Height 400/ColorSpace/DeviceRGB'
        b'/BitsPerComponent 8/Filter/DCTDecode/Length %d>>stream\n' % len(jpeg)
        + jpeg + b'\nendstream',
        b'<</Length 35>>stream\nq 100 0 0 100 50 700 cm /Im1 Do Q\nendstream',
    ])
    assert pdf_io._embedded(raw, pdf_io.MAX_PAGES, pdf_io.MAX_SIDE) == []
    monkeypatch.setattr(pdf_io, '_drawn_fitz', lambda *a: [b'\xff\xd8\xffpage'])
    assert pdf_io.pdf_pictures(raw) == [b'\xff\xd8\xffpage']


@pytest.mark.skipif(not _HAS_PDF, reason='no PDF library here')
def test_pages_are_written_and_turned_the_same_on_both_libraries():
    raw = _text_pdf(b'Factura 2026-17 Total 121,00 EUR')
    out = pdf_io.writer()
    for page in pdf_io.reader(raw).pages:
        pdf_io.turn_page(page, 90)
        pdf_io.add_page(out, page)
    buf = io.BytesIO()
    out.write(buf)
    assert pdf_io.is_pdf(buf.getvalue())
    assert len(pdf_io.reader(buf.getvalue()).pages) == 1


def test_text_takes_the_first_reader_that_gives_usable_text(monkeypatch):
    monkeypatch.setattr(pdf_io, '_text_fitz', _blank)
    monkeypatch.setattr(pdf_io, '_text_pdfminer', lambda *a: ['NIF B12345674 Total 568,19 EUR'])
    monkeypatch.setattr(pdf_io, '_text_pypdf', lambda *a: ['should not be used'])
    assert pdf_io.pdf_text(b'%PDF') == 'NIF B12345674 Total 568,19 EUR'


def test_pymupdf_reads_the_text_first_so_one_package_covers_both_routes(monkeypatch):
    monkeypatch.setattr(pdf_io, '_text_fitz', lambda *a: ['Factura 597970 Total 9,61 EUR'])
    monkeypatch.setattr(pdf_io, '_text_pdfminer', lambda *a: ['should not be used'])
    monkeypatch.setattr(pdf_io, '_text_pypdf', lambda *a: ['(cid:66)(cid:97)'])
    assert pdf_io.pdf_text(b'%PDF') == 'Factura 597970 Total 9,61 EUR'
    assert 'for read in (_text_fitz, _text_pdfminer, _text_pypdf):' in _PATH.read_text(encoding='utf-8')


def test_each_page_keeps_its_number_even_when_one_is_empty(monkeypatch):
    """Page 3 must be the third page, so an empty page stays in the list."""
    monkeypatch.setattr(pdf_io, '_text_fitz', lambda *a: ['Factura 597970', '', 'Total 9,61 EUR IVA 1,67'])
    assert pdf_io.pdf_page_texts(b'%PDF') == ['Factura 597970', '', 'Total 9,61 EUR IVA 1,67']
    assert pdf_io.pdf_text(b'%PDF') == 'Factura 597970\n\nTotal 9,61 EUR IVA 1,67'


def test_pdfminer_pages_are_split_at_the_form_feed(monkeypatch):
    import types
    import sys

    fake = types.ModuleType('pdfminer.high_level')
    fake.extract_text = lambda stream, maxpages=0: 'one\fsecond page\f\fFour\f'
    monkeypatch.setitem(sys.modules, 'pdfminer', types.ModuleType('pdfminer'))
    monkeypatch.setitem(sys.modules, 'pdfminer.high_level', fake)
    assert pdf_io._text_pdfminer(b'%PDF', 10) == ['one', 'second page', '', 'Four']
    assert pdf_io._text_pdfminer(b'%PDF', 2) == ['one', 'second page']


def test_unmapped_glyphs_from_pdfminer_are_not_text(monkeypatch):
    """``(cid:66)(cid:97)…`` is pdfminer failing on a font. Draw the page instead."""
    garbage = ''.join('(cid:%d)' % n for n in range(66, 120))
    assert not pdf_io.usable(garbage)
    assert pdf_io.usable('Factura 597970 Base 7,94 IVA 1,67 Total 9,61')
    monkeypatch.setattr(pdf_io, '_text_fitz', _blank)
    monkeypatch.setattr(pdf_io, '_text_pdfminer', lambda *a: [garbage])
    monkeypatch.setattr(pdf_io, '_text_pypdf', _blank)
    assert pdf_io.pdf_text(b'%PDF') == ''


def test_stray_glyphs_are_not_text(monkeypatch):
    monkeypatch.setattr(pdf_io, '_text_fitz', _blank)
    monkeypatch.setattr(pdf_io, '_text_pdfminer', _blank)
    monkeypatch.setattr(pdf_io, '_text_pypdf', lambda *a: ['\x00 \x01 ; ;'])
    assert pdf_io.pdf_text(b'%PDF') == ''


def test_without_embedded_pictures_the_page_is_drawn(monkeypatch):
    monkeypatch.setattr(pdf_io, '_embedded', _none)
    monkeypatch.setattr(pdf_io, '_drawn_fitz', _none)
    monkeypatch.setattr(pdf_io, '_drawn_tool', lambda *a: [b'\xff\xd8\xffpage'])
    assert pdf_io.pdf_pictures(b'%PDF') == [b'\xff\xd8\xffpage']


def test_a_renderer_that_breaks_is_skipped(monkeypatch):
    def broken(*args):
        raise OSError('no renderer')

    monkeypatch.setattr(pdf_io, '_embedded', _none)
    monkeypatch.setattr(pdf_io, '_drawn_fitz', broken)
    monkeypatch.setattr(pdf_io, '_drawn_tool', _none)
    assert pdf_io.pdf_pictures(b'%PDF') == []


def _photo(orientation):
    """A JPEG whose EXIF says how the camera was held."""
    from PIL import Image
    exif = (b'Exif\x00\x00MM\x00*\x00\x00\x00\x08\x00\x01\x01\x12\x00\x03\x00\x00\x00\x01\x00'
            + bytes([orientation]) + b'\x00\x00\x00\x00\x00\x00')
    picture = Image.new('RGB', (40, 80))
    picture.paste((255, 0, 0), (0, 0, 20, 40))
    out = io.BytesIO()
    picture.save(out, 'JPEG', quality=95, exif=exif)
    return out.getvalue()


@pytest.mark.parametrize('orientation', range(1, 9))
def test_pillow5_stands_a_photo_up_like_pillow6(orientation):
    """Odoo 14 ships Pillow 5.4, which has no ``ImageOps.exif_transpose``."""
    from PIL import Image, ImageOps
    if not hasattr(ImageOps, 'exif_transpose'):
        pytest.skip('needs Pillow 6+ as the reference')
    raw = _photo(orientation)
    ours = pdf_io._stand_up(Image.open(io.BytesIO(raw)))
    pillow = ImageOps.exif_transpose(Image.open(io.BytesIO(raw)))
    assert ours.size == pillow.size
    assert ours.convert('RGB').tobytes() == pillow.convert('RGB').tobytes()


@pytest.mark.parametrize('stack', STACKS)
def test_exif_transpose_is_never_called_bare(stack):
    src = (ROOT / 'stacks' / stack / 'pns_base' / 'utils' / 'pdf_io.py').read_text(encoding='utf-8')
    assert 'ImageOps.exif_transpose(' not in src
    assert "getattr(ImageOps, 'exif_transpose', None) or _stand_up" in src
