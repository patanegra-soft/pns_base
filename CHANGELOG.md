# Changelog

What changes for people who use this module, one section per published version, newest first. The heading is the git tag.

## owl1-1.2.56_owl2-1.2.65 (2026-11-04)

- Store page: a new 2:1 thumbnail, so the Odoo Apps listing no longer crops the sides of the banner.

## owl1-1.2.55_owl2-1.2.64 (2026-11-04)

- Store page: a new banner that says what the module is and which Odoo series are tested (14.0 and 19.0). The image is much smaller.

## owl1-1.2.54_owl2-1.2.63 (2026-11-02)

- First Odoo test: it opens the web client and fails on any JavaScript error. It needs Chrome; without it Odoo skips the test.
- Store page and README explain this test.

## owl1-1.2.53_owl2-1.2.62 (2026-11-02)

- First public release. The shared base for every PNS module: install it first. The other modules depend on it; it depends on none of them.
- Views written the old way (`attrs`, `<tree>`) keep working on Odoo 17 and later. It also ships a small library: one name for helpers Odoo renamed between versions, toasts and reports, portable import/export, PDF and picture helpers, a full-screen picture viewer and an operation-result wizard.
- Security: the export wizard only deletes the exported file of the user who made it, not any attachment.
- Translations: "Warnings" and "Errors" in operation reports are translated, and on Odoo 19 the Python and JavaScript texts of the module load their translation.
