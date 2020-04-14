from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_default_country(self):
        return self.env.ref('base.ph').id

    title_gender = fields.Selection(string="Title", selection=[('miss', 'Miss'), ('mister', 'Mister')])
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',
                                 default=lambda self: self._compute_default_country())
