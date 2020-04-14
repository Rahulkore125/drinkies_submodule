import json

from odoo import models, fields, api


class MagentoBackendDashboard(models.Model):
    _inherit = "magento.backend"

    @api.one
    def _kanban_dashboard(self):
        self.kanban_dashboard = json.dumps(self.get_magento_backend_dashboard_datas())

    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    color = fields.Integer()

    @api.multi
    def get_magento_backend_dashboard_datas(self):
        magento_backend_id = self.id
        title = ''
        number_website = len(self.website_ids)
        self.env.cr.execute("""SELECT COUNT(DISTINCT(id)) FROM magento_store WHERE backend_id = %s""",
                            (magento_backend_id,))
        number_store = self.env.cr.fetchone()[0]
        self.env.cr.execute("""SELECT COUNT(DISTINCT(id)) FROM magento_storeview  WHERE backend_id = %s""",
                            (magento_backend_id,))
        number_store_view = self.env.cr.fetchone()[0]

        # customers
        self.env.cr.execute("""SELECT COUNT(DISTINCT(id)) FROM magento_res_partner  WHERE backend_id = %s""",
                            (magento_backend_id,))
        number_customer = self.env.cr.fetchone()[0]
        number_product = 0

        # order
        self.env.cr.execute(
            """SELECT COUNT(DISTINCT(id)) FROM magento_sale_order  WHERE backend_id = %s AND odoo_id in (SELECT id FROM sale_order WHERE state LIKE 'sale')""",
            (magento_backend_id,))
        number_sale_order = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            """SELECT COUNT(DISTINCT(id)) FROM magento_sale_order  WHERE backend_id = %s AND odoo_id in (SELECT id FROM sale_order WHERE state LIKE 'draft')""",
            (magento_backend_id,))
        number_quotation = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            """SELECT COUNT(DISTINCT(id)) FROM magento_sale_order  WHERE backend_id = %s AND odoo_id in (SELECT id FROM sale_order WHERE state LIKE 'done')""",
            (magento_backend_id,))
        number_done = self.env.cr.fetchone()[0]
        self.env.cr.execute(
            """SELECT COUNT(DISTINCT(id)) FROM magento_sale_order  WHERE backend_id = %s AND odoo_id in (SELECT id FROM sale_order WHERE state LIKE 'cancel')""",
            (magento_backend_id,))
        number_cancel = self.env.cr.fetchone()[0]

        # product
        self.env.cr.execute("""SELECT COUNT(DISTINCT(id)) FROM magento_product_product  WHERE backend_id = %s""",
                            (magento_backend_id,))
        number_product = self.env.cr.fetchone()[0]

        return {
            'number_website': number_website,
            'number_store': number_store,
            'number_store_view': number_store_view,
            'number_customer': number_customer,
            'number_product': number_product,
            'number_sale_order': number_sale_order,
            'number_quotation': number_quotation,
            'number_done': number_done,
            'number_cancel': number_cancel,
            'title': title,
        }
