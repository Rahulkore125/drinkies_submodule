from datetime import date

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.multi
    def action_confirm(self):
        for rec in self:
            result = super(SaleOrder, self).action_confirm()
            # if rec.is_magento_sale_order:
            #     return result
            # else:
            invoice_id = rec.action_invoice_create(grouped=False, final=False)

            for e in invoice_id:
                invoice = self.env['account.invoice'].browse(e)
                invoice.update({
                    'original_invoice': True,
                    'order_id': rec.id
                })
                # print('ste_' + rec.magento_bind_ids.state)
                invoice.action_invoice_open()
                # if rec.is_magento_sale_order and rec.magento_bind_ids.state != 'complete':
                #     print('not_done')
                #     return result
                # else:
                if invoice.state != 'open':
                    invoice.state = 'open'
                if rec.payment_method == 'cod':
                    journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                elif rec.payment_method == 'online_payment':
                    journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                payment = self.env['account.payment'].create({
                    'invoice_ids': [(4, e, None)],
                    'amount': invoice.amount_total,
                    'payment_date': date.today(),
                    'communication': invoice.number,
                    'payment_type': 'inbound',
                    'journal_id': journal_id,
                    'partner_type': 'customer',
                    'payment_method_id': 1,
                    'partner_id': invoice.partner_id.id
                })
                payment.action_validate_invoice_payment()
                return result
