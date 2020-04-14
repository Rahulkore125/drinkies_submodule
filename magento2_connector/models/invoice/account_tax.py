from odoo import fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
    )

    external_id = fields.Integer(string='ID on Magento')

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Magento ID.'),
    ]
