# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2014 Rodolfo Leme Bertozo - KMEE - www.kmee.com.br            #
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
###############################################################################

from __future__ import with_statement
from openerp.report.render import render
from openerp.report.interface import report_int
from openerp import pooler
from openerp.addons.nfe.sped.nfe.processing.xml import print_daede


class external_pdf(render):

    def __init__(self, pdf):
        render.__init__(self)
        self.pdf = pdf
        self.output_type = 'pdf'

    def _render(self):
        return self.pdf


class report_custom(report_int):
    '''
        Custom report for return danfe
    '''

    def create(self, cr, uid, ids, datas, context=None):
        context = context or {}
        active_ids = context.get('active_ids')
        pool = pooler.get_pool(cr.dbname)
        list_account_invoice = []

        # ai_obj = pool.get('l10n_br_account.invoice.cce')
        # for cce in ai_obj.browse(cr, uid, active_ids):
        #     invoices = pool.get('account.invoice')
        #     list_account_invoice.append(invoices.browse(cr, uid, cce.invoice_id))
        ai_obj = pool.get('account.invoice')
        account_invoice = ai_obj.browse(cr, uid, active_ids)
        pdf_string = print_daede(account_invoice)

        self.obj = external_pdf(pdf_string)
        self.obj.render()
        return (self.obj.pdf, 'pdf')

report_custom('report.daede_account_invoice')
