from odoo import models, fields


class MagentoCity(models.Model):
    _name = 'magento.city'

    name = fields.Char("Name")
    external_id = fields.Char("External ID")
