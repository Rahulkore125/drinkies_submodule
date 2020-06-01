from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    original_invoice = fields.Boolean()
    order_id = fields.Integer()

    user_related = fields.Many2one(string="Owner location", comodel_name="res.users", compute="compute_user_related",
                                   store=True)
    # estimate_discount_total = fields.Monetary(string='Additional Whole Order Discount')
    # computed_discount_total = fields.Monetary(string='Discount Amount', compute='compute_discount_total', store=True)
    #
    # @api.multi
    # def compute_discount_total(self):
    #     for rec in self:
    #         rec.computed_discount_total = 0
    #         order = self.env['sale.order'].sudo().search([('name', '=', rec.origin)], limit=1)
    #         if order:
    #             rec.compute_discount_total = order.compute_discount_total
    #
    # @api.depends('amount', 'amount_rounding', 'compute_discount_total')
    # def _compute_amount_total(self):
    #     for tax_line in self:
    #         tax_line.amount_total = tax_line.amount + tax_line.amount_rounding

    @api.depends('origin')
    def compute_user_related(self):
        for rec in self:
            rec.user_related = False
            if rec.origin:
                sale_order = self.env['sale.order'].sudo().search([('name', '=', rec.origin)], limit=1)
                if sale_order:
                    if sale_order.user_related:
                        rec.user_related = sale_order.user_related
