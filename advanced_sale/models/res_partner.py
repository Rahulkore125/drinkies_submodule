from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_default_country(self):
        return self.env.ref('base.ph').id

    title_gender = fields.Selection(string="Title", selection=[('miss', 'Miss'), ('mister', 'Mister')])
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',
                                 default=lambda self: self._compute_default_country())

    def _get_name(self):
        res = super(ResPartner, self)._get_name()
        if res:
            return res
        else:
            return self.name

    def remove_duplicate(self):
        users = self.env['res.users'].sudo().search(['|', ('active', '=', True), ('active', '=', False)])
        list_partner = []
        for user in users:
            list_partner.append(user.partner_id.id)
        magento_partners = self.env['magento.res.partner'].sudo().search([])
        for rec in magento_partners:
            if rec.odoo_id.id not in list_partner:
                list_partner.append(rec.odoo_id.id)
        sale_orders = self.env['sale.order'].sudo().search([])
        for order in sale_orders:
            if order.partner_id.id not in list_partner:
                list_partner.append(order.partner_id.id)
            if order.partner_shipping_id.id not in list_partner:
                list_partner.append(order.partner_shipping_id.id)
            if order.partner_invoice_id.id not in list_partner:
                list_partner.append(order.partner_invoice_id.id)

        self.env.cr.execute(
            'delete from res_partner where id != 1 and  id not in %s and id in %s',
            (tuple(list_partner), tuple(self.ids))
        )
        self.env.cr.commit()
