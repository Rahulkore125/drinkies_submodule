# -*- coding: utf-8 -*-

from odoo import models, fields


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def auto_install(self):
        self.env.cr.execute("DELETE FROM account_invoice")
        self.env.cr.execute("DELETE FROM account_invoice_line");
        self.env.cr.execute("DELETE FROM account_invoice_line");
        self.env.cr.execute("DELETE FROM stock_change_product_qty");

        self.env.cr.execute("DELETE FROM sale_order")
        self.env.cr.execute("DELETE from account_payment")

        self.env.cr.execute("DELETE from account_partial_reconcile")
        self.env.cr.execute("DELETE from account_move")
        self.env.cr.execute("DELETE from account_move_line")
        self.env.cr.execute("DELETE from stock_inventory")
        self.env.cr.execute("DELETE from stock_picking")
        self.env.cr.execute("DELETE from stock_scrap")
        self.env.cr.execute("DELETE from stock_return_picking")
        self.env.cr.execute("DELETE from stock_return_picking_line")
        self.env.cr.execute("DELETE from stock_move")
        self.env.cr.execute("DELETE from stock_quant")
        # self.env.cr.execute("UPDATE magento_backend SET auto_fetching = False")
        # self.env.cr.execute("UPDATE magento_pull_history set sync_date = '2020-1-5 00:00:04.347442' WHERE name='sale_orders'")
        # self.env.cr.execute("DELETE  from product_template WHERE is_magento_product = True")
        # self.env.cr.execute("DELETE from magento_pull_history WHERE name = 'normal_product'")
        # self.env.cr.execute("DELETE from magento_pull_history WHERE name = 'categories'")
        # self.env.cr.execute("DELETE from magento_product_attribute")
        # self.env.cr.execute("DELETE from magento_product_category")
        # self.env.cr.execute("DELETE from magento_pull_history WHERE name = 'sale_orders'")

        # self.env.cr.execute(" UPDATE sale_order set create_date = '2020-01-05 17:27:51.768691' WHERE id > 4012 and id < 4020")
        # self.env.cr.execute(
        #     "UPDATE sale_order set date_order = '2020-01-05 17:27:51.768691' WHERE id > 4012 and id < 4020")
        #
        #
        #








        # self.env.cr.execute("UPDATE magento_product_product SET odoo_id = 107 WHERE external_id = 244")
        # self.env.cr.execute("UPDATE magento_product_product SET odoo_id = 108 WHERE external_id = 245")
        # self.env.cr.execute("UPDATE product_template SET is_heineken_product = True WHERE is_magento_product = TRUE")

        # self.env.cr.execute("UPDATE product_product SET display_deduct_parent_product = TRUE WHERE id = 68")
        # self.env.cr.execute("UPDATE product_product SET display_deduct_parent_product = TRUE WHERE id = 69")

        self.env.cr.execute("UPDATE magento_backend SET auto_fetching = FALSE ")


