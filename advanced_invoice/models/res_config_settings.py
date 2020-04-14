from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_advanced_invoice = fields.Boolean(string="Use Heineken Invoice Flow")
