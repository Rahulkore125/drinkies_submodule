from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    multiple_sku_one_stock = fields.Boolean("Manage Multiple Stock Variant by Flow Heineken", default=False)
    deduct_amount_parent_product = fields.Integer("Deductible amount of parent product when it be sold", default=1)
    display_deduct_parent_product = fields.Boolean(compute='compute_display_deduct_parent_product', default=False,
                                                   store=True)
    variant_manage_stock = fields.Many2one('product.product', domain="[('product_tmpl_id', '=', id)]",
                                           string="Variant Manage Stock")
    is_heineken_product = fields.Boolean("Is Heineken Product", default=False)
    origin_quantity = fields.Float(string="Origin Quantity", default=0)
    fetching = fields.Boolean("Fetching", default=False)

    @api.depends('variant_manage_stock')
    def _compute_product_variant_id(self):
        for p in self:
            if self.multiple_sku_one_stock:
                p.product_variant_id = p.variant_manage_stock.id
            else:
                p.product_variant_id = p.product_variant_ids[:1].id

    @api.multi
    @api.depends('multiple_sku_one_stock')
    def compute_display_deduct_parent_product(self):
        for rec in self:
            if rec.multiple_sku_one_stock:
                rec.display_deduct_parent_product = True

    def _compute_quantities_dict(self):
        # TDE FIXME: why not using directly the function fields ?
        variants_available = self.mapped('product_variant_ids')._product_available()
        prod_available = {}
        for template in self:
            qty_available = 0
            virtual_available = 0
            incoming_qty = 0
            outgoing_qty = 0
            template.origin_qty = qty_available

            if template.multiple_sku_one_stock:
                for p in template.variant_manage_stock:
                    # print(variants_available[p.id]["qty_available"] * p.deduct_amount_parent_product)
                    qty_available += variants_available[p.id]["qty_available"] * p.deduct_amount_parent_product
                    virtual_available += variants_available[p.id]["virtual_available"] * p.deduct_amount_parent_product
                    incoming_qty += variants_available[p.id]["incoming_qty"] * p.deduct_amount_parent_product
                    outgoing_qty += variants_available[p.id]["outgoing_qty"] * p.deduct_amount_parent_product
                prod_available[template.id] = {
                    "qty_available": qty_available,
                    "virtual_available": virtual_available,
                    "incoming_qty": incoming_qty,
                    "outgoing_qty": outgoing_qty,
                }
            else:
                for p in template.product_variant_ids:
                        qty_available += variants_available[p.id]["qty_available"]
                        virtual_available += variants_available[p.id]["virtual_available"]
                        incoming_qty += variants_available[p.id]["incoming_qty"]
                        outgoing_qty += variants_available[p.id]["outgoing_qty"]
                prod_available[template.id] = {
                            "qty_available": qty_available,
                            "virtual_available": virtual_available,
                            "incoming_qty": incoming_qty,
                            "outgoing_qty": outgoing_qty,
                        }

            template.origin_qty = qty_available
        return prod_available