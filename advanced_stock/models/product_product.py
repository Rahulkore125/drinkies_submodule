from datetime import timedelta
from odoo.exceptions import UserError
from odoo import models, fields, api, tools
from datetime import date, datetime
from ...magento2_connector.utils.magento.rest import Client


class ProductProduct(models.Model):
    _inherit = 'product.product'

    def get_default_lst_price(self):
        return self.product_tmpl_id.list_price

    deduct_amount_parent_product = fields.Integer("Deductible amount of parent product when it be sold", default=1)
    display_deduct_parent_product = fields.Boolean(compute='compute_display_deduct_parent_product', default=False,
                                                   store=True)

    @api.multi
    @api.depends('multiple_sku_one_stock')
    def compute_display_deduct_parent_product(self):
        for rec in self:
            if rec.multiple_sku_one_stock:
                rec.display_deduct_parent_product = True

    def _compute_quantities_dict(self, lot_id, owner_id, package_id, from_date=False, to_date=False):
        res = super(ProductProduct, self)._compute_quantities_dict(self._context.get('lot_id'),
                                                                   self._context.get('owner_id'),
                                                                   self._context.get('package_id'),
                                                                   self._context.get('from_date'),
                                                                   to_date=to_date)

        # only to_date as to_date will correspond to qty_available
        to_date = fields.Datetime.to_datetime(to_date)

        dates_in_the_past = False
        template_qty = dict()

        for e in res:
            product = self.env['product.product'].search([('id', '=', e)])
            if product.product_tmpl_id.multiple_sku_one_stock:
                if product.product_tmpl_id.id in template_qty:
                    pass
                else:
                    template_qty[product.product_tmpl_id.id] = True

        if to_date and to_date < (fields.Datetime.now() + timedelta(seconds=-10)):
            dates_in_the_past = True

        if not dates_in_the_past:
            for f in template_qty:
                template = self.env['product.template'].search([('id', '=', f)])
                stock_quants = self.env['stock.quant'].search(
                    [('product_id', '=', template.variant_manage_stock.id), ('updated_qty', '=', True)])

                for e in stock_quants:
                    if e.updated_qty:
                        line_ids = []
                        for t in template.product_variant_ids:
                            line_ids.append((0, 0,
                                             {'product_id': t.id, 'location_id': e.location_id.id,
                                              'product_qty': e.original_qty / t.deduct_amount_parent_product}))

                        stock_inventory = self.env['stock.inventory'].create({
                            'location_id': e.location_id.id,
                            'date': date.today(),
                            'filter': 'partial',
                            'line_ids': line_ids,
                            'name': ('INV: %s') % tools.ustr(template.name)
                        })
                        stock_inventory.update_to_magento = True

                        stock_inventory.action_validate()

                        e.sudo().write({
                            'updated_qty': False
                        })

        res = super(ProductProduct, self)._compute_quantities_dict(self._context.get('lot_id'),
                                                                   self._context.get('owner_id'),
                                                                   self._context.get('package_id'),
                                                                   self._context.get('from_date'),
                                                                   to_date=to_date)

        return res
