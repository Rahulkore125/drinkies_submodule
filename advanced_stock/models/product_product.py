from datetime import timedelta
from odoo.exceptions import UserError
from odoo import models, fields, api, tools
from datetime import date, datetime
from ...magento2_connector.utils.magento.rest import Client


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_default_lst_price(self):
        return self.product_tmpl_id.list_price

    display_deduct_parent_product = fields.Boolean(compute='compute_display_deduct_parent_product', default=False,
                                                   store=True)
    deduct_amount_parent_product = fields.Integer("Deductible amount of parent product when it be sold", default=1)


    @api.multi
    @api.depends('multiple_sku_one_stock')
    def compute_display_deduct_parent_product(self):
        for rec in self:
            if rec.product_tmpl_id.multiple_sku_one_stock:
                rec.display_deduct_parent_product = True
