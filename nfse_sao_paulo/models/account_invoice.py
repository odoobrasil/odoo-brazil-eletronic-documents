# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT

FIELD_STATE = {'draft': [('readonly', False)]}


class AccountInvoice(models.Model):
    _inherit = 'account.invoice'

    operation = fields.Selection(
        [('T', u"Tributado em São Paulo"),
         ('F', u"Tributado Fora de São Paulo"),
         ('A', u"Tributado em São Paulo, porém isento"),
         ('B', u"Tributado Fora de São Paulo, porém isento"),
         ('M', u"Tributado em São Paulo, porém Imune"),
         ('N', u"Tributado Fora de São Paulo, porém Imune"),
         ('X', u"Tributado em São Paulo, porém Exigibilidade Suspensa"),
         ('V', u"Tributado Fora de São Paulo, porém Exigibilidade Suspensa"),
         ('P', u"Exportação de Serviços"),
         ('C', u"Cancelado")], u"Operação",
        default='T', readonly=True, states=FIELD_STATE)
    verify_code = fields.Char(u'Código Verificação', size=20,
                              readonly=True, states=FIELD_STATE)

    @api.multi
    def invoice_print(self):
        if self.fiscal_type == 'service' and \
           self.company_id.l10n_br_city_id.ibge_code == '50308':

            return self.env['report'].get_action(
                self, 'nfse_sao_paulo.danfse_report')

        return super(AccountInvoice, self).invoice_print()

    @api.multi
    def action_invoice_send_nfse(self):
        result = super(AccountInvoice, self).action_invoice_send_nfse()
        if result['success']:
            if self.company_id.nfse_environment == '1':  # Produção
                self.verify_code = result['verify_code']
                self.internal_number = result['nfse_number']
        return

    @api.multi
    def _hook_validation(self):
        res = super(AccountInvoice, self)._hook_validation()

        errors = []
        inscr_mun = re.sub('[^0-9]', '', self.company_id.inscr_mun or '')
        if len(inscr_mun) != 8:
            errors.append(u'Verifique a inscrição municipal da empresa')
        for inv_line in self.invoice_line:
            prod = "Produto: %s - %s" % (inv_line.product_id.default_code,
                                         inv_line.product_id.name)
            if not inv_line.service_type_id:
                errors.append(u'%s - Tipo de Serviço é obrigatório' % prod)
            cod_serv = re.sub('[^0-9]', '',
                              inv_line.service_type_id.code or '')

            if len(cod_serv) != 5:
                errors.append(
                    u'%s - Verifique o código do serviço (5 dígitos)' % prod)

        return res + errors

    def issqn_due_date(self):
        date_emition = datetime.strptime(self.date_hour_invoice,
                                         DEFAULT_SERVER_DATETIME_FORMAT)
        next_month = date_emition + relativedelta(months=1)
        due_date = date(next_month.year, next_month.month, 10)
        if due_date.weekday() >= 5:
            while due_date.weekday() != 0:
                due_date = due_date + timedelta(days=1)
        format = "%d/%m/%Y"
        due_date = datetime.strftime(due_date, format)

        return due_date
