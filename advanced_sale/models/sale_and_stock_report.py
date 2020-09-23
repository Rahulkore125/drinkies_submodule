from odoo import api, fields, models


class SaleAndStockReport(models.Model):
    _name = "sale.and.stock.report"
    _description = "Sale And Stock Report"

    company_currency_id = fields.Many2one(comodel_name="res.currency",
                                          default=lambda self: self.env.user.company_id.currency_id)

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    uom = fields.Many2one(comodel_name="uom.uom", string="Unit of measure", related="product_id.uom_id")
    location_id = fields.Many2one(comodel_name="stock.location", string="Warehouse location")
    team_id = fields.Many2one(comodel_name="crm.team", string="Sale Channel")
    payment_method = fields.Selection([('cod', 'COD'), ('online_payment', 'Online payment')], string="Payment method")
    sold = fields.Float(string='Sold')
    amount = fields.Monetary(string='Amount', currency_field="company_currency_id")
    is_heineken_product = fields.Boolean(string="Is Drinkies Product", related='product_id.is_heineken_product',
                                         store=True)
