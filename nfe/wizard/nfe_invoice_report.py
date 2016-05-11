# -*- coding: utf-8 -*-
# © <2016> <Luis Felipe Mileo>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import xlwt
from dateutil import parser

from openerp.report import report_sxw
from openerp.addons.report_xls.report_xls import report_xls
from openerp.addons.report_xls.utils import _render
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
    ('open_and_paid', u'Open and Paid'),
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
            domain.append(('date_hour_invoice', '>=', self.start_date + ' 00:00:01'))
        if self.stop_date:
            domain.append(('date_hour_invoice', '<=', self.stop_date + ' 23:59:59'))
        if fiscal_category_ids:
            domain.append(
                ('fiscal_category_id', 'in', fiscal_category_ids.ids))
        if self.state:
            if self.state == "open_and_paid":
                domain.append('|')
                domain.append(('state', '=', 'open'))
                domain.append(('state', '=', 'paid'))
            else:
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
                    'date': parser.parse(invoice.date_hour_invoice).strftime('%d-%m-%Y') or '-',
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


class StockHistoryXlsParser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(StockHistoryXlsParser, self).__init__(
            cr, uid, name, context=context)
        self.context = context


class StockHistoryXls(report_xls):

    def __init__(self, name, table, rml=False, parser=False, header=True,
                 store=False):
        super(StockHistoryXls, self).__init__(
            name, table, rml, parser, header, store)

        # Cell Styles
        _xs = self.xls_styles
        # header
        rh_cell_format = _xs['bold'] + _xs['fill'] + \
            _xs['borders_all'] + _xs['right']
        self.rh_cell_style = xlwt.easyxf(rh_cell_format)
        self.rh_cell_style_center = xlwt.easyxf(rh_cell_format + _xs['center'])
        self.rh_cell_style_right = xlwt.easyxf(rh_cell_format + _xs['right'])
        self.rh_cell_style_date = xlwt.easyxf(
            rh_cell_format, num_format_str=report_xls.date_format)
        # lines
        self.mis_rh_cell_style = xlwt.easyxf(
            _xs['borders_all'] + _xs['bold'] + _xs['fill'])
        line_cell_format = _xs['borders_all']
        self.line_cell_style_decimal = xlwt.easyxf(
            line_cell_format + _xs['right'],
            num_format_str=report_xls.decimal_format)
        self.line_cell_style = xlwt.easyxf(line_cell_format)

        self.col_specs_template = {
            'date': {
                'header': [1, 15, 'text', _render("('Data')")],
                'lines': [1, 0, 'text', _render("line.get('date')")],
                'totals': [1, 0, 'text', None]},
            'cnpj_cpf': {
                'header': [1, 30, 'text', _render("('CNPJ - CPF')")],
                'lines': [1, 0, 'text', _render("line.get('cnpj_cpf')")],
                'totals': [1, 0, 'text', None]},
            'partner': {
                'header': [1, 50, 'text', _render("('Parceiro')")],
                'lines': [1, 0, 'text', _render("line.get('partner')")],
                'totals': [1, 0, 'text', None]},
            'internal_number': {
                'header': [1, 15, 'text', _render("('Numero Interno')")],
                'lines': [1, 0, 'text', _render("line.get('internal_number')")],
                'totals': [1, 0, 'text', None]},
            'revenue_expense': {
                'header': [1, 15, 'text', _render("('Revenue Expense')")],
                'lines': [1, 0, 'text', _render("line.get('revenue_expense')")],
                'totals': [1, 0, 'text', None]},
            'type': {
                'header': [1, 15, 'text', _render("('Tipo')")],
                'lines': [1, 0, 'text', _render("line.get('type')")],
                'totals': [1, 0, 'text', None]},
            'amount_gross': {
                'header': [1, 15, 'text', _render("('Valor Bruto')")],
                'lines': [1, 0, 'number',
                          _render("line.get('amount_gross')"),
                          None, self.line_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'amount_untaxed': {
                'header': [1, 15, 'text', _render("('Valor Não Taxado')")],
                'lines': [1, 0, 'number',
                          _render("line.get('amount_untaxed')"),
                          None, self.line_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'amount_total': {
                'header': [1, 15, 'text', _render("('Valor Total')")],
                'lines': [1, 0, 'number',
                          _render("line.get('amount_total')"),
                          None, self.line_cell_style_decimal],
                'totals': [1, 0, 'text', None]},
            'state': {
                'header': [1, 15, 'text', _render("('Estado')")],
                'lines': [1, 0, 'text', _render("line.get('state')")],
                'totals': [1, 0, 'text', None]},
        }

    def _get_invoices_search_domain(self, invoices_report):
        domain = []
        journal_domain = []
        journal_domain += invoices_report._revenue_expense()
        fiscal_category_ids = False
        if len(journal_domain) > 0:
            journal_ids = self.pool.get('account.journal').\
                search(self.cr, self.uid, [journal_domain], context=self.context)
            fiscal_category_ids = self.pool.get('l10n_br_account.fiscal.category').\
                search(
                    self.cr, self.uid,
                    [('property_journal', 'in', journal_ids.ids)],
                    context=self.context
                )
        if invoices_report.fiscal_category_ids:
            fiscal_category_ids = fiscal_category_ids.filtered(
                lambda record: record.id in invoices_report.fiscal_category_ids.ids)
        if invoices_report.start_date:
            domain.append(('date_hour_invoice', '>=', invoices_report.start_date + ' 00:00:01'))
        if invoices_report.stop_date:
            domain.append(('date_hour_invoice', '<=', invoices_report.stop_date + ' 23:59:59'))
        if fiscal_category_ids:
            domain.append(
                ('fiscal_category_id', 'in', fiscal_category_ids.ids))
        if invoices_report.state:
            if invoices_report.state == "open_and_paid":
                domain.append('|')
                domain.append(('state', '=', 'open'))
                domain.append(('state', '=', 'paid'))
            else:
                domain.append(('state', '=', invoices_report.state))
        if invoices_report.operation_type:
            domain.append(
                ('type', '=', invoices_report.operation_type))
        if invoices_report.fiscal_type:
            domain.append(('fiscal_type', '=', invoices_report.fiscal_type))
        if invoices_report.issuer:
            domain.append(('issuer', '=', invoices_report.issuer))
        return domain

    def _get_invoices(self, invoices_report):
        return self.pool.get('account.invoice').search(self.cr, self.uid,
            self._get_invoices_search_domain(invoices_report),
            # order=invoices_report.search_order,
        )

    def compute(self, invoices_report):
        assert len(invoices_report) == 1

        invoices = self.pool.get('account.invoice').browse(
                self.cr, self.uid, self._get_invoices(invoices_report)
            )

        content = []
        amount_total = amount_gross = 0.00

        for invoice in invoices:
            content.append(
                {
                    'internal_number': invoice.internal_number or '-',
                    # 'serie': invoice.internal_number or '',
                    'date': parser.parse(invoice.date_hour_invoice).strftime('%d-%m-%Y') or '-',
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

        return content

    def generate_xls_report(self, _p, _xs, data, objects, wb):

        report_name = 'Relatório de emissão de NF-E'
        ws = wb.add_sheet(report_name[:31])
        ws.panes_frozen = True
        ws.remove_splits = True
        ws.portrait = 0  # Landscape
        ws.fit_width_to_pages = 1
        row_pos = 0

        # set print header/footer
        ws.header_str = self.xls_headers['standard']
        ws.footer_str = self.xls_footers['standard']

        # Title
        c_specs = [
            ('report_name', 1, 0, 'text', report_name),
        ]
        row_data = self.xls_row_template(c_specs, ['report_name'])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=xlwt.easyxf(_xs['xls_title']))
        row_pos += 1

        # Column headers
        c_specs = map(lambda x: self.render(
            x, self.col_specs_template, 'header'),
            [
                'date',
                'cnpj_cpf',
                'partner',
                'internal_number',
                'revenue_expense',
                'type',
                'amount_gross',
                'amount_untaxed',
                'amount_total',
                'state'
            ])
        row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
        row_pos = self.xls_write_row(
            ws, row_pos, row_data, row_style=self.rh_cell_style_center,
            set_column_size=True)
        ws.set_horz_split_pos(row_pos)

        #lines
        active_ids = self.context.get('active_ids')
        wizard_obj = self.pool.get('nfe.invoice.report').browse(
            self.cr, self.uid, active_ids)
        data = self.compute(wizard_obj)
        for line in data:
            c_specs = map(
                lambda x: self.render(
                    x, self.col_specs_template, 'lines'), [
                    'date',
                    'cnpj_cpf',
                    'partner',
                    'internal_number',
                    'revenue_expense',
                    'type',
                    'amount_gross',
                    'amount_untaxed',
                    'amount_total',
                    'state'
                ])
            row_data = self.xls_row_template(c_specs, [x[0] for x in c_specs])
            row_pos = self.xls_write_row(
                ws, row_pos, row_data, row_style=self.line_cell_style)
        pass


StockHistoryXls(
    'report.wizard.nfe.faturamento',
    'nfe.invoice.report',
    parser=StockHistoryXlsParser
)
