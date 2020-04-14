from odoo import api, fields, models


class PopupDialog(models.TransientModel):
    _name = "popup.dialog"

    message = fields.Text(string='Message', readonly=True)
