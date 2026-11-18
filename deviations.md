# Deviations

This file lists the rules of tiavelum/engineering-standards that this
repository deviates from, with the reason for each, for its maintainers and
for anyone who applies the standards to it.

## TL-6, TL-8, TL-23, TL-33: no formatter or linter for JavaScript

The only JavaScript is the 18-line script of `app/transfer-form.html`, which posts the form to the service; adding a Node toolchain for it would outweigh the file, and the UI tests that follow in a separate issue exercise it.
Recorded 2026-11-18.
