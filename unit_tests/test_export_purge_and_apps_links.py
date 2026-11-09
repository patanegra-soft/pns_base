# -*- coding: utf-8 -*-
# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
"""Exports expire; Apps links stay the vendor's; list views stay OCA's."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def _src(stack, *parts):
    return (ROOT / 'stacks' / stack / 'pns_base').joinpath(*parts).read_text(encoding='utf-8')


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_export_files_are_marked_and_purged(stack):
    io_src = _src(stack, 'utils', 'portable_io.py')
    assert "'description': EXPORT_MARK" in io_src
    model = _src(stack, 'models', 'ir_attachment.py')
    assert "'pns_base.export_retention_hours'" in model
    assert 'DEFAULT_RETENTION_HOURS = 24' in model
    assert "('description', '=', EXPORT_MARK)" in model
    cron = _src(stack, 'data', 'export_purge_cron.xml')
    assert 'model._cron_purge_pns_exports()' in cron
    assert ('name="numbercall"' in cron) == (stack == 'owl1')
    assert ('name="activity_user_type"' in cron) == (stack == 'owl1')
    manifest = _src(stack, '__manifest__.py')
    assert "'data/export_purge_cron.xml'" in manifest
    assert "'mail'" in manifest.split("'depends'", 1)[1].split(']', 1)[0]


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_export_wizard_unlink_only_deletes_own_exports(stack):
    src = _src(stack, 'models', 'export_file_wizard.py')
    body = src.split('def unlink', 1)[1].split('\n    def ', 1)[0]
    assert 'a.description == EXPORT_MARK' in body
    assert 'self.env.su or a.create_uid == self.env.user' in body


@pytest.mark.parametrize('stack', ['owl1', 'owl2'])
def test_apps_website_is_not_rewritten(stack):
    src = _src(stack, 'models', 'ir_module_module.py')
    assert 'def update_list' not in src
    assert "'website'" not in src.split('class IrModuleModule', 1)[1].replace("'name', 'website'", '')
    js = _src(stack, 'static', 'src', 'js', 'pns_module_index.js')
    assert 'sandbox' in js


def test_owl1_list_controller_not_overridden():
    js = _src('owl1', 'static', 'src', 'js', 'pns_invalid_fields_dedupe.js')
    assert 'ListController' not in js
    assert '_saveMultipleRecords' not in js


def test_invalid_fields_and_required_css_are_pns_views_only():
    css = (ROOT / 'common' / 'static' / 'src' / 'css' / 'pns_required_readonly.css').read_text(
        encoding='utf-8',
    )
    assert '.o_pns_view .o_field_widget.o_required_modifier' in css
    assert '.o_form_view .o_field_widget.o_required_modifier' not in css
    owl1 = _src('owl1', 'static', 'src', 'js', 'pns_invalid_fields_dedupe.js')
    assert '_pnsIsOurView' in owl1
    assert 'if (!this._pnsIsOurView())' in owl1
    owl2 = _src('owl2', 'static', 'src', 'js', 'pns_invalid_fields_dedupe.js')
    assert 'archHasPnsClass' in owl2
    assert 'this.model._pnsOwnedView' in owl2


def test_translation_dedupe_only_drops_pns_modules():
    src = _src('owl1', 'models', 'ir_translation.py')
    assert "startswith('pns')" in src
    assert 'if ours(row[_IDX_MODULE]) and ours(prev[_IDX_MODULE])' in src


def test_review_and_result_screens_reach_the_server():
    # O14 gets the whole context in fields_view_get.
    owl1 = _src('owl1', 'models', 'operation_report_wizard.py')
    assert "ctx['pns_import_preview'] = False" in owl1
    assert "ctx['pns_operation_result'] = False" in owl1
    # 17+ send get_views only lang and *_view_ref: the screen rides form_view_ref.
    owl2 = _src('owl2', 'models', 'operation_report_wizard.py')
    assert "ctx['form_view_ref'] = False" in owl2
    assert "{'form_view_ref': _PREVIEW_VIEW}" in owl2
    assert "{'form_view_ref': _RESULT_VIEW}" in owl2
    assert 'pns_import_preview=' not in owl2
    assert "'pns_operation_result'" not in owl2


def test_import_preview_lives_on_the_mixin():
    for stack in ('owl1', 'owl2'):
        src = _src(stack, 'models', 'operation_report_wizard.py')
        assert 'def action_preview' in src
        assert 'def action_import' in src
        assert 'SAVEPOINT' in src
        assert 'ROLLBACK TO SAVEPOINT' in src
        assert 'def _apply_import_preview' in src
        views = _src(stack, 'views', 'operation_report_wizard_views.xml')
        assert 'view_pns_import_preview_form' in views
        assert 'name="action_import"' in views
        assert 'Apply the import' in views
        assert 'No data has been written.' in views
        assert 'Will create' in views
        assert 'Will replace' in views
        assert 'Will leave' in views
        assert 'def _preview_bucket_title' in src
        assert 'o_pns_preview_box' in views
        assert 'o_pns_preview_attr' in views
        assert 'name="result_status"' not in views.split('view_pns_import_preview_form', 1)[1]
        assert 'o_pns_preview_card' not in views
        assert 'def _preview_param_text' in src
        assert 'o_pns_op_result' in views
        assert 'o_pns_alert_icon' in views
        assert 'def _stamp_review_button' in src
        assert 'def _name_list_text' in src
        assert 'result_created_names' in src
        assert 'name="result_created_names"' in views
        assert 'Breakdown' not in views.split('view_pns_import_preview_form', 1)[1]
        assert 'o_pns_preview_attr">Section list' in views
        assert "('result_created', '=', 0)" in views
        assert "('result_updated', '=', 0)" in views
        assert "('result_skipped', '=', 0)" in views
        css = (ROOT / 'common' / 'static' / 'src' / 'css' / 'pns_import_preview.css').read_text(
            encoding='utf-8',
        )
        assert '.o_pns_import_preview' in css
        assert '.o_pns_preview_box' in css
        assert '.o_pns_preview_attr' in css
        assert '.o_pns_alert_icon' in css
        if stack == 'owl1':
            assert 'def fields_view_get' in src
        else:
            assert 'def get_view' in src


def test_pns_view_class_is_injected_from_xmlid():
    for stack in ('owl1', 'owl2'):
        src = _src(stack, 'models', 'ir_ui_view_patch.py')
        assert "PNS_VIEW_CLASS = 'o_pns_view'" in src
        assert 'def _add_pns_view_class' in src
        assert 'def _view_is_pns_owned' in src
        if stack == 'owl1':
            assert 'def fields_view_get' in src
        else:
            assert 'def get_view' in src
