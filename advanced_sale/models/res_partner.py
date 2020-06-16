from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def _compute_default_country(self):
        return self.env.ref('base.ph').id

    title_gender = fields.Selection(string="Title", selection=[('miss', 'Miss'), ('mister', 'Mister')])
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict',
                                 default=lambda self: self._compute_default_country())

    def _get_name(self):
        # """ Utility method to allow name_get to be overrided without re-browse the partner """
        # partner = self
        # name = partner.name or ''
        #
        # if partner.company_name or partner.parent_id:
        #     if not name and partner.type in ['invoice', 'delivery', 'other']:
        #         name = dict(self.fields_get(['type'])['type']['selection'])[partner.type]
        #     if not partner.is_company:
        #         name = "%s, %s" % (partner.commercial_company_name or partner.parent_id.name, name)
        # if self._context.get('show_address_only'):
        #     name = partner._display_address(without_company=True)
        # if self._context.get('show_address'):
        #     name = name + "\n" + partner._display_address(without_company=True)
        # name = name.replace('\n\n', '\n')
        # name = name.replace('\n\n', '\n')
        # if self._context.get('address_inline'):
        #     name = name.replace('\n', ', ')
        # if self._context.get('show_email') and partner.email:
        #     name = "%s <%s>" % (name, partner.email)
        # if self._context.get('html_format'):
        #     name = name.replace('\n', '<br/>')
        # if self._context.get('show_vat') and partner.vat:
        #     name = "%s ‒ %s" % (name, partner.vat)
        # return name
        res = super(ResPartner, self)._get_name()
        if res:
            return res
        else:
            return self.name
