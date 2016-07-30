# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 Trustcode - www.trustcode.com.br                         #
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


import logging
from openerp import api, fields, models
from openerp.tools.translate import _
from openerp.exceptions import Warning


_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    """account_invoice overwritten methods"""
    _inherit = 'account.invoice'

    nfse_status = fields.Char(u'Status NFS-e', size=100)
    state = fields.Selection(selection_add=[
        ('nfse_ready', u'Enviar RPS'),
        ('nfse_exception', u'Erro de autorização'),
        ('nfse_cancelled', u'Cancelada')])

    def _attach_files(self, obj_id, model, data, filename):
        obj_attachment = self.env['ir.attachment']

        obj_attachment.create({
            'name': filename,
            'datas': data,
            'datas_fname': filename,
            'description': '' or _('No Description'),
            'res_model': model,
            'res_id': obj_id,
        })

    @api.multi
    def action_resend(self):
        self.state = 'nfse_ready'

    @api.multi
    def action_set_to_draft(self):
        self.button_cancel()
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.multi
    def validate_nfse(self):
        self.ensure_one()

        strErro = u''
        if not self.document_serie_id:
            strErro = u'Nota Fiscal - Série da nota fiscal\n'

        if not self.fiscal_document_id:
            strErro += u'Nota Fiscal - Tipo de documento fiscal\n'

        if not self.document_serie_id.internal_sequence_id:
            strErro += u'Nota Fiscal - Número da nota fiscal, a série deve ter uma sequencia interna\n'

        # Emitente
        if not self.company_id.partner_id.legal_name:
            strErro += u'Emitente - Razão Social\n'

        if not self.company_id.partner_id.name:
            strErro += u'Emitente - Fantasia\n'

        if not self.company_id.partner_id.cnpj_cpf:
            strErro += u'Emitente - CNPJ/CPF\n'

        if not self.company_id.partner_id.street:
            strErro += u'Emitente / Endereço - Logradouro\n'

        if not self.company_id.partner_id.number:
            strErro += u'Emitente / Endereço - Número\n'

        if not self.company_id.partner_id.zip:
            strErro += u'Emitente / Endereço - CEP\n'

        if not self.cnae_id:
            strErro += u'Fatura / CNAE\n'

        if not self.company_id.partner_id.inscr_est:
            strErro += u'Emitente / Inscrição Estadual\n'

        if not self.company_id.partner_id.state_id:
            strErro += u'Emitente / Endereço - Estado\n'
        else:
            if not self.company_id.partner_id.state_id.ibge_code:
                strErro += u'Emitente / Endereço - Código do IBGE do estado\n'
            if not self.company_id.partner_id.state_id.name:
                strErro += u'Emitente / Endereço - Nome do estado\n'

        if not self.company_id.partner_id.l10n_br_city_id:
            strErro += u'Emitente / Endereço - município\n'
        else:
            if not self.company_id.partner_id.l10n_br_city_id.name:
                strErro += u'Emitente / Endereço - Nome do município\n'
            if not self.company_id.partner_id.l10n_br_city_id.ibge_code:
                strErro += u'Emitente / Endereço - Código do IBGE do município\n'

        if not self.company_id.partner_id.country_id:
            strErro += u'Emitente / Endereço - país\n'
        else:
            if not self.company_id.partner_id.country_id.name:
                strErro += u'Emitente / Endereço - Nome do país\n'
            if not self.company_id.partner_id.country_id.bc_code:
                strErro += u'Emitente / Endereço - Código do BC do país\n'

        # Destinatário
        if self.partner_id.is_company and not self.partner_id.legal_name:
            strErro += u'Destinatário - Razão Social\n'

        if self.partner_id.country_id.id == self.company_id.partner_id.country_id.id:
            if not self.partner_id.cnpj_cpf:
                strErro += u'Destinatário - CNPJ/CPF\n'

        if not self.partner_id.street:
            strErro += u'Destinatário / Endereço - Logradouro\n'

        if not self.partner_id.number:
            strErro += u'Destinatário / Endereço - Número\n'

        if self.partner_id.country_id.id == self.company_id.partner_id.country_id.id:
            if not self.partner_id.zip:
                strErro += u'Destinatário / Endereço - CEP\n'

        if self.partner_id.country_id.id == self.company_id.partner_id.country_id.id:
            if not self.partner_id.state_id:
                strErro += u'Destinatário / Endereço - Estado\n'
            else:
                if not self.partner_id.state_id.ibge_code:
                    strErro += u'Destinatário / Endereço - Código do IBGE do estado\n'
                if not self.partner_id.state_id.name:
                    strErro += u'Destinatário / Endereço - Nome do estado\n'

        if self.partner_id.country_id.id == self.company_id.partner_id.country_id.id:
            if not self.partner_id.l10n_br_city_id:
                strErro += u'Destinatário / Endereço - Município\n'
            else:
                if not self.partner_id.l10n_br_city_id.name:
                    strErro += u'Destinatário / Endereço - Nome do município\n'
                if not self.partner_id.l10n_br_city_id.ibge_code:
                    strErro += u'Destinatário / Endereço - Código do IBGE do município\n'

        if not self.partner_id.country_id:
            strErro += u'Destinatário / Endereço - País\n'
        else:
            if not self.partner_id.country_id.name:
                strErro += u'Destinatário / Endereço - Nome do país\n'
            if not self.partner_id.country_id.bc_code:
                strErro += u'Destinatário / Endereço - Código do BC do país\n'

        # produtos
        for inv_line in self.invoice_line:
            if inv_line.product_id:
                if not inv_line.product_id.default_code:
                    strErro += u'Produtos e Serviços: %s, Qtde: %s - Referência/Código do produto\n' % (
                        inv_line.product_id.name, inv_line.quantity)
                if not inv_line.product_id.name:
                    strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - Nome do produto\n' % (
                        inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)
                if not inv_line.quantity:
                    strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - Quantidade\n' % (
                        inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)

                if not inv_line.price_unit:
                    strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - Preco unitario\n' % (
                        inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)

                if inv_line.product_type == 'service':
                    if not inv_line.issqn_type:
                        strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - Tipo do ISSQN\n' % (
                            inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)

                if not inv_line.pis_cst_id:
                    strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - CST do PIS\n' % (
                        inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)

                if not inv_line.cofins_cst_id:
                    strErro += u'Produtos e Serviços: %s - %s, Qtde: %s - CST do COFINS\n' % (
                        inv_line.product_id.default_code, inv_line.product_id.name, inv_line.quantity)

        if strErro:
            raise Warning(
                _(u'Atenção !'), (u"Por favor corrija os erros antes de prosseguir:\n '%s'") % (strErro, ))

    @api.multi
    def action_invoice_send_nfse(self):
        event_obj = self.env['l10n_br_account.document_event']
        base_nfse = self.env['base.nfse'].create({'invoice_id': self.id,
                                                  'company_id': self.company_id.id,
                                                  'city_code': '6291',
                                                  'certificate': self.company_id.nfe_a1_file,
                                                  'password': self.company_id.nfe_a1_password})

        send = base_nfse.send_rps()
        vals = {
            'type': '14',
            'status': send['status'],
            'company_id': self.company_id.id,
            'origin': '[NFS-e] {0}'.format(self.internal_number),
            'message': send['message'],
            'state': 'done',
            'document_event_ids': self.id
        }
        event = event_obj.create(vals)
        for xml_file in send['files']:
            self._attach_files(event.id, 'l10n_br_account.document_event',
                               xml_file['data'], xml_file['name'])

        if send['success']:
            self.state = 'open'
            self.nfse_status = str(send['status']) + ' - ' + send['message']
        else:
            self.state = 'nfse_exception'
            self.nfse_status = str(send['status']) + ' - ' + send['message']

    @api.multi
    def button_cancel_nfse(self):
        cancel_result = True
        if self.state == 'open' and self.company_id.nfse_environment == '1':
            cancel_result, last_event = self.cancel_nfse_online()
        if cancel_result:
            return super(AccountInvoice, self).action_cancel()
        if last_event:
            view = self.env['ir.model.data'].get_object_reference(
                'l10n_br_account', 'l10n_br_account_document_event_form')
            return {
                'name': _(u"Eventos Eletrônicos"),
                'view_mode': 'form',
                'view_id': view[1],
                'view_type': 'form',
                'res_model': 'l10n_br_account.document_event',
                'res_id': last_event,
                'type': 'ir.actions.act_window',
                'nodestroy': True,
                'target': 'new',
                'domain': '[]',
                'context': None
            }

    @api.multi
    def cancel_nfse_online(self):
        event_obj = self.env['l10n_br_account.document_event']
        base_nfse = self.env['base.nfse'].create({'invoice_id': self.id,
                                                  'company_id': self.company_id.id,
                                                  'city_code': '6291',
                                                  'certificate': self.company_id.nfe_a1_file,
                                                  'password': self.company_id.nfe_a1_password})

        cancelamento = base_nfse.cancel_nfse()
        vals = {
            'type': '16',
            'status': cancelamento['status'],
            'company_id': self.company_id.id,
            'origin': '[NFS-e] {0}'.format(self.internal_number),
            'message': cancelamento['message'],
            'state': 'done',
            'document_event_ids': self.id
        }
        event = event_obj.create(vals)
        last_event = False
        for xml_file in cancelamento['files']:
            self._attach_files(event.id, 'l10n_br_account.document_event',
                               xml_file['data'], xml_file['name'])
            last_event = event.id
        return cancelamento['success'], last_event

    @api.multi
    def invoice_print_nfse(self):
        base_nfse = self.env['base.nfse'].create({'invoice_id': self.id,
                                                  'city_code': '6291'})

        return base_nfse.print_pdf(self)
