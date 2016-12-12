# -*- coding: utf-8 -*-
# © <2016> <Luis Felipe Mileo>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from openerp import api, models

_logger = logging.getLogger(__name__)


class ReportNfeInvoiceInstance(models.AbstractModel):

    _name = 'report.nfe.report_nfe_invoice_instance'

    @api.multi
    def render_html(self, data=None):
        docs = self.env['nfe.invoice.report'].browse(self._ids)
        docs_computed = {}
        for doc in docs:
            docs_computed[doc.id] = doc.compute()
        docargs = {
            'doc_ids': self._ids,
            'doc_model': 'nfe.invoice.report',
            'docs': docs,
            'docs_computed': docs_computed,
        }
        return self.env['report'].\
            render('nfe.report_nfe_invoice_instance', docargs)


class Report(models.Model):
    _inherit = "report"

    @api.v7
    def get_pdf(self, cr, uid, ids, report_name, html=None, data=None,
                context=None):
        if ids:
            report = self._get_report_from_name(cr, uid, report_name)
            obj = self.pool[report.model].browse(cr, uid, ids,
                                                 context=context)[0]
            context = context.copy()
            if hasattr(obj, 'landscape_pdf') and obj.landscape_pdf:
                context.update({'landscape': True})
        return super(Report, self).get_pdf(cr, uid, ids, report_name,
                                           html=html, data=data,
                                           context=context)
