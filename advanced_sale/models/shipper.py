from odoo import models, fields


class Shipper(models.Model):
    _name = 'shipper'

    name = fields.Char(string="Name")
