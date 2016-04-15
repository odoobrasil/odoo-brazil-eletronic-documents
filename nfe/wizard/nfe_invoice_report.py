# -*- coding: utf-8 -*-
# © <2016> <Luis Felipe Mileo>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openerp import api, fields, models
from openerp.addons.l10n_br_account_product.models.l10n_br_account import \
    PRODUCT_FISCAL_TYPE

OPERATION_TYPE = {
    'out_invoice': u'S',
    'in_invoice': u'E',
    'out_refund': u'E',
    'in_refund': u'S'
}

OPERATION_TYPE_LIST = [
    ('out_invoice', u'Saída'),
    ('in_invoice', u'Entrada'),
    ('out_refund', u'Devolução de Venda'),
    ('in_refund', u'Devolução de Compra'),
]

REVENUE_EXPENSE = {
    True: u'S',
    False: u'N',
}

INVOICE_STATE = [
    ('draft', u'Draft'),
    ('proforma', u'Pro-forma'),
    ('proforma2', u'Pro-forma'),
    ('open', u'Open'),
    ('paid', u'Paid'),
    ('cancel', u'Cancelled'),
    ('sefaz_export', u'Enviar para Receita'),
    ('sefaz_exception', u'Erro de autorização da Receita'),
    ('sefaz_cancelled', u'Cancelado no Sefaz'),
    ('sefaz_denied', u'Denegada no Sefaz'),
]

INVOICE_STATE_SRING = {
    'draft': u'Draft',
    'proforma': u'Pro-forma',
    'proforma2': u'Pro-forma',
    'open': u'Open',
    'paid': u'Paid',
    'cancel': u'Cancelled',
    'sefaz_export': u'Enviar para Receita',
    'sefaz_exception': u'Erro de autorização da Receita',
    'sefaz_cancelled': u'Cancelado no Sefaz',
    'sefaz_denied': u'Denegada no Sefaz',
}

class NfeInvoiceReportWizard(models.TransientModel):

    _name = 'nfe.invoice.report'
    _description = u'Assistente de relatório de faturamento'

    name = fields.Char(
        string=u'Name')
    start_date = fields.Date(
        string=u'Data Inicial'
    )
    stop_date = fields.Date(
        string=u'Data Final'
    )
    revenue_expense = fields.Selection(
        selection=[
            ('yes', u'Sim'),
            ('no', u'Não'),
            (False, u'Todos'),
        ],
        string=u'Gera Financeiro')
    fiscal_type = fields.Selection(
        selection=PRODUCT_FISCAL_TYPE,
        string=u'Tipo Fiscal',
    )
    operation_type = fields.Selection(
        selection=OPERATION_TYPE_LIST,
        string=u'Tipo de operação',
        required=True
    )
    issuer = fields.Selection(
        selection=[
            ('0', u'Emissão própria'),
            ('1', u'Terceiros'),
            (False, u'Todos'),
        ],
        string=u'Emitente'
    )
    fiscal_category_ids = fields.Many2many(
        comodel_name='l10n_br_account.fiscal.category',
        string=u'Categoria Fiscal'
    )
    landscape_pdf = fields.Boolean(
        string=u'Landscape PDF'
    )
    state = fields.Selection(
        selection=INVOICE_STATE,
        string=u'Situação',
    )

    search_order = fields.Selection(
        selection=[
            ('internal_number', u'Numero da Fatura'),
            ('date_due', u'Data'),
            ('fiscal_type', u'Tipo fiscal'),
            ('type', u'Tipo de Operação'),
            ('issuer', u'Emitente'),
            ('state', u'Situação'),
        ],
        string="Ordenação"
    )

    def _get_invoices_search_order(self):
        return self.search_order

    def _revenue_expense(self):
        revenue_expense = []
        if self.revenue_expense:
            revenue_expense = [('revenue_expense', '=', False)]
            if self.revenue_expense == 'yes':
                revenue_expense = [('revenue_expense', '=', True)]
        return revenue_expense

    def _get_invoices_search_domain(self):
        domain = []
        journal_domain = []
        journal_domain += self._revenue_expense()
        journal_ids = self.env['account.journal'].search(journal_domain)
        fiscal_category_ids = self.env[
            'l10n_br_account.fiscal.category'].search(
            [('property_journal', 'in', journal_ids.ids)]
        )
        if self.fiscal_category_ids:
            fiscal_category_ids = fiscal_category_ids.filtered(
                lambda record: record.id in self.fiscal_category_ids.ids)
        if self.start_date:
            domain.append(('date_invoice', '>=', self.start_date))
        if self.stop_date:
            domain.append(('date_invoice', '<=', self.stop_date))
        if fiscal_category_ids:
            domain.append(
                ('fiscal_category_id', 'in', fiscal_category_ids.ids))
        if self.state:
            domain.append(('state', '=', self.state))
        if self.operation_type:
            domain.append(
                ('type', '=', self.operation_type))
        if self.fiscal_type:
            domain.append(('fiscal_type', '=', self.fiscal_type))
        if self.issuer:
            domain.append(('issuer', '=', self.issuer))
        return domain

    def _get_invoices(self):
        return self.env['account.invoice'].search(
            self._get_invoices_search_domain(),
            order=self._get_invoices_search_order(),
        )

    @api.multi
    def compute(self):
        assert len(self) == 1

        invoices = self._get_invoices()

        # prepare header and content
        header = []
        content = []
        amount_total = amount_gross = 0.00

        for invoice in invoices:
            content.append(
                {
                    'internal_number': invoice.internal_number or '-',
                    # 'serie': invoice.internal_number or '',
                    'date': invoice.date_invoice or '-',
                    'type': OPERATION_TYPE[invoice.type] or '-',
                    'partner': invoice.partner_id.legal_name or '-',
                    'cnpj_cpf': invoice.partner_id.cnpj_cpf or '-',
                    'fiscal_category': (invoice.fiscal_category_id and
                                        invoice.fiscal_category_id.code or ''),
                    'revenue_expense': REVENUE_EXPENSE[
                        invoice.journal_id.revenue_expense],
                    'amount_gross': invoice.amount_gross or '-',
                    'amount_untaxed': invoice.amount_untaxed or '-',
                    'amount_total': invoice.amount_total or '-',
                    'state': INVOICE_STATE_SRING[invoice.state] or '-',
                    # 'nfe_access_key': invoice.nfe_access_key or '-',
                    # 'nfe_status': invoice.nfe_status[:3] or '-',
                }
            )
            amount_total += invoice.amount_total
            amount_gross += invoice.amount_gross

        header.append({
            'start_date': self.start_date,
            'stop_date': self.stop_date,
            'revenue_expense': self.revenue_expense,
            'fiscal_type': self.fiscal_type,
            'issuer': self.issuer,
            'cols': [],
            'amount_total': amount_total,
            'amount_gross': amount_gross,
        })
        return {'header': header,
                'content': content}
