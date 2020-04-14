from odoo import fields, models


class MagentoOperation(models.Model):
    _name = "magento.operation"

    name = fields.Many2many("magento.backend")
    import_customer = fields.Boolean('import Customer')
    import_product = fields.Boolean('import Product')
    import_sale_order = fields.Boolean('import Sale Order')
    import_invoice = fields.Boolean('import Invoice')

    def execute_operation(self):
        pass
