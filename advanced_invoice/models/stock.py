from datetime import date

from odoo import models


class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        context = dict(self._context or {})
        order = self.env['stock.picking'].browse(context.get('active_ids')).sale_id
        # if order.is_magento_sale_order:
        #     return super(StockReturnPicking, self).create_returns()
        # else:

        refund = self.env['account.invoice.refund'].create({
            'filter_refund': 'refund',
            'description': 'Return product',
            'date_invoice': date.today(),
        })

        action = super(StockReturnPicking, self).create_returns()
        invoice = self.env['account.invoice'].search([('original_invoice', '=', True), (
            'order_id', '=', order.id)])
        invoice_lines = invoice.invoice_line_ids

        invoice_lines_copy = {}
        for e in invoice_lines:
            invoice_lines_copy[e.product_id.id] = e.copy()
            invoice_lines_copy[e.product_id.id].write({'invoice_id': False})
        invoice_lines_update = []
        for e in self.product_return_moves:
            if e.product_id.id in invoice_lines_copy:
                invoice_lines_copy[e.product_id.id].write({
                    'quantity': e.quantity
                })
                invoice_lines_update.append(invoice_lines_copy[e.product_id.id].id)

        refund.with_context({'active_ids': [invoice.id]}).compute_refund(mode='refund')
        credit_note = self.env['account.invoice'].search([('refund_invoice_id', '=', invoice.id)])
        for e in credit_note:
            if e.state != 'paid':
                # e.invoice_line_ids = invoice_lines
                e.write({
                    'invoice_line_ids': [(6, 0, invoice_lines_update)]
                })
                e.action_invoice_open()
                if order.payment_method == 'cod':
                    journal_id = self.env['account.journal'].search([('code', '=', 'CSH1')]).id
                elif order.payment_method == 'online_payment':
                    journal_id = self.env['account.journal'].search([('code', '=', 'BNK1')]).id
                payment = self.env['account.payment'].create({
                    'invoice_ids': [(4, e.id, None)],
                    'amount': e.amount_total,
                    'payment_date': date.today(),
                    'communication': e.number,
                    'payment_type': 'outbound',
                    'journal_id': journal_id,
                    'partner_type': 'customer',
                    'payment_method_id': 1,
                    'partner_id': e.partner_id.id
                })
                payment.action_validate_invoice_payment()
        return action
