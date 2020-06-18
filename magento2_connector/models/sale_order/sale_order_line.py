from odoo import api, fields, models


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    direct_discount_amount = fields.Monetary(string="Direct discount", currency_field="currency_id")
