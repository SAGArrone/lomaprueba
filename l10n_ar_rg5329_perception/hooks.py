from odoo import Command, SUPERUSER_ID, api


def _post_init_l10n_ar_rg5329(*args):
    if len(args) == 1:
        env = args[0]
    else:
        env = api.Environment(args[0], SUPERUSER_ID, {})

    companies = env["res.company"].sudo().search([])
    default_types = env["res.company"]._l10n_ar_rg5329_default_responsibility_types()
    for company in companies:
        vals = {}
        if not company.l10n_ar_rg5329_min_amount:
            vals["l10n_ar_rg5329_min_amount"] = 3000.0
        if default_types and not company.l10n_ar_rg5329_responsibility_type_ids:
            vals["l10n_ar_rg5329_responsibility_type_ids"] = [Command.set(default_types.ids)]
        if vals:
            company.with_context(l10n_ar_rg5329_skip_apply=True).write(vals)

