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


from openerp import api, fields, models
from openerp.exceptions import Warning

FIELD_STATE = {'draft': [('readonly', False)]}


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    lote_nfse = fields.Char(
        u'Lote', size=20, readonly=True, states=FIELD_STATE)


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
