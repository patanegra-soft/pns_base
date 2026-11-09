/** @odoo-module **/
/* SPDX-License-Identifier: Apache-2.0
 * Copyright (C) 2026 Patanegra Soft <https://patanegra.com>
 *
 * Odoo 20 reads a view button's `icon` as a Material Symbols name (`check`).
 * pns_* views share their XML with 14-19 and say `fa-download`: those keep
 * the Font Awesome classes that pns_fa_compat.css draws.
 */
import { patch } from "@web/core/utils/patch";
import { ViewButton } from "@web/views/view_button/view_button";

patch(ViewButton.prototype, {
    setup() {
        super.setup();
        if (this.icon && /^fa-/.test(this.icon.name || "")) {
            this.icon = { tag: "i", class: "o_button_icon fa " + this.icon.name };
        }
    },
});
