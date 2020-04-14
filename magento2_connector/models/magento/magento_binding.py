from odoo import models, fields


class MagentoBinding(models.AbstractModel):
    """ Abstract Model for the Bindings.
    All the models used as bindings between Magento and Odoo
    """
    _name = 'magento.binding'
    _description = 'Magento Binding (abstract)'

    backend_id = fields.Many2one(
        comodel_name='magento.backend',
        string='Magento Backend',
        required=True,
        ondelete='restrict',
    )

    external_id = fields.Integer(string='ID on Magento')

    _sql_constraints = [
        ('magento_uniq', 'unique(backend_id, external_id)',
         'A binding already exists with the same Magento ID.'),
    ]
