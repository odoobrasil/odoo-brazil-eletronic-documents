# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 TrustCode - www.trustcode.com.br                         #
#              Danimar Ribeiro <danimaribeiro@gmail.com>                      #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU General Public License for more details.                                #
#                                                                             #
# You should have received a copy of the GNU General Public License           #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
#                                                                             #
###############################################################################


from lxml import etree
from openerp import api, fields, models
from openerp.exceptions import Warning

FIELD_STATE = {'draft': [('readonly', False)]}


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    def _default_operation(self):
        return self.env.user.company_id.default_operation

    def _default_taxation(self):
        return self.env.user.company_id.default_taxation

    operation = fields.Selection([('A', u"Sem Dedução"),
                                  ('B', u"Com dedução/Materiais"),
                                  ('C', u"Imune/Isenta de ISSQN"),
                                  ('D', u"Devolução/Simples Remessa"),
                                  ('J', u"Intermediação")], u"Operação",
                                 default=_default_operation, readonly=True,
                                 states=FIELD_STATE)

    taxation = fields.Selection([('C', u"Isenta de ISS"),
                                 ('E', u"Não incidência no município"),
                                 ('F', u"Imune"),
                                 ('K', u"Exigibilidade Susp.Dec.J/Proc.A"),
                                 ('N', u"Não Tributável"),
                                 ('T', u"Tributável"),
                                 ('G', u"Tributável Fixo"),
                                 ('H', u"Tributável S.N."),
                                 ('M', u"Micro Empreendedor Individual(MEI)")],
                                u"Tributação", default=_default_taxation,
                                readonly=True, states=FIELD_STATE)

    cnae_id = fields.Many2one('l10n_br_account.cnae', string=u"CNAE",
                              readonly=True, states=FIELD_STATE)
    lote_nfse = fields.Char(
        u'Lote', size=20, readonly=True, states=FIELD_STATE)
    transaction = fields.Char(u'Transação', size=60,
                              readonly=True, states=FIELD_STATE)

    @api.multi
    def action_invoice_send_nfse(self):
        if self.company_id.lote_sequence_id:
            ir_env = self.env['ir.sequence']
            lote = ir_env.next_by_id(self.company_id.lote_sequence_id.id)
            self.lote_nfse = lote
        else:
            raise Warning(u'Atenção!', u'Configure na empresa a sequência para\
                                        gerar o lote da NFS-e')

        return super(AccountInvoice, self).action_invoice_send_nfse()

    def fields_view_get(self, cr, uid, view_id=None, view_type='form',
                        context=None, toolbar=False, submenu=False):

        res = super(AccountInvoice, self).fields_view_get(
            cr, uid, view_id=view_id, view_type=view_type, context=context,
            toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res['arch'])
            nodes = doc.xpath("//field[@name='cnae_id']")
            if nodes:
                user = self.pool['res.users'].browse(
                    cr, uid, uid, context=context)
                main_id = user.company_id.cnae_main_id.id
                secondary_ids = user.company_id.cnae_secondary_ids.ids
                ids = [main_id]
                ids.extend(secondary_ids)
                nodes[0].set("domain", "[('id', '=', %s)]" % str(ids))
                res['arch'] = etree.tostring(doc)
        return res
