from odoo import models, fields, api


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    original_invoice = fields.Boolean()
    order_id = fields.Integer()

    user_related = fields.Many2one(string="Owner location", comodel_name="res.users", compute="compute_user_related",
                                   store=True)

    @api.depends('origin')
    def compute_user_related(self):
        for rec in self:
            rec.user_related = False
            if rec.origin:
                sale_order = self.env['sale.order'].sudo().search([('name', '=', rec.origin)], limit=1)
                if sale_order:
                    if sale_order.user_related:
                        rec.user_related = sale_order.user_related
