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


FIELD_STATE = {'draft': [('readonly', False)]}

_logger = logging.getLogger(__name__)


class AccountInvoice(models.Model):
    """account_invoice overwritten methods"""
    _inherit = 'account.invoice'

    def _default_state(self):
        if self.env.user.company_id.state_id:
            return self.env.user.company_id.state_id

    def _default_city(self):
        if self.env.user.company_id.l10n_br_city_id:
            return self.env.user.company_id.l10n_br_city_id

    nfse_status = fields.Char(u'Status NFS-e', size=100)
    state = fields.Selection(selection_add=[
        ('nfse_ready', u'Enviar RPS'),
        ('nfse_exception', u'Erro de autorização'),
        ('nfse_cancelled', u'Cancelada')])
    lote_nfse = fields.Char(
        u'Lote', size=20, readonly=True, states=FIELD_STATE)

    state_id = fields.Many2one('res.country.state', string=u"Estado",
                               default=_default_state,
                               domain=[('country_id.code', '=', 'BR')])

    provider_city_id = fields.Many2one('l10n_br_base.city',
                                       string=u"Munícipio Prestação",
                                       readonly=True, default=_default_city,
                                       states=FIELD_STATE)

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
        self.action_cancel()
        self.write({'state': 'draft'})
        self.delete_workflow()
        self.create_workflow()
        return True

    @api.multi
    def _hook_validation(self):
        """
            Override this method to implement the validations specific
            for the city you need
            @returns list<string> errors
        """
        errors = []
        if not self.document_serie_id:
            errors.append('Nota Fiscal - Série da nota fiscal')
        if not self.fiscal_document_id:
            errors.append(u'Nota Fiscal - Tipo de documento fiscal')
        if not self.document_serie_id.internal_sequence_id:
            errors.append(u'Nota Fiscal - Número da nota fiscal, \
                          a série deve ter uma sequencia interna')

        # Emitente
        if not self.company_id.partner_id.legal_name:
            errors.append(u'Emitente - Razão Social')
        if not self.company_id.partner_id.name:
            errors.append(u'Emitente - Fantasia')
        if not self.company_id.partner_id.cnpj_cpf:
            errors.append(u'Emitente - CNPJ/CPF')
        if not self.company_id.partner_id.street:
            errors.append(u'Emitente / Endereço - Logradouro')
        if not self.company_id.partner_id.number:
            errors.append(u'Emitente / Endereço - Número')
        if not self.company_id.partner_id.zip:
            errors.append(u'Emitente / Endereço - CEP')
        if not self.company_id.partner_id.inscr_est:
            errors.append(u'Emitente / Inscrição Estadual')
        if not self.company_id.partner_id.state_id:
            errors.append(u'Emitente / Endereço - Estado')
        else:
            if not self.company_id.partner_id.state_id.ibge_code:
                errors.append(u'Emitente / Endereço - Cód. do IBGE do estado')
            if not self.company_id.partner_id.state_id.name:
                errors.append(u'Emitente / Endereço - Nome do estado')

        if not self.company_id.partner_id.l10n_br_city_id:
            errors.append(u'Emitente / Endereço - município')
        else:
            if not self.company_id.partner_id.l10n_br_city_id.name:
                errors.append(u'Emitente / Endereço - Nome do município')
            if not self.company_id.partner_id.l10n_br_city_id.ibge_code:
                errors.append(u'Emitente/Endereço - Cód. do IBGE do município')

        if not self.company_id.partner_id.country_id:
            errors.append(u'Emitente / Endereço - país')
        else:
            if not self.company_id.partner_id.country_id.name:
                errors.append(u'Emitente / Endereço - Nome do país')
            if not self.company_id.partner_id.country_id.bc_code:
                errors.append(u'Emitente / Endereço - Código do BC do país')

        partner = self.partner_id
        company = self.company_id
        # Destinatário
        if partner.is_company and not partner.legal_name:
            errors.append(u'Destinatário - Razão Social')

        if partner.country_id.id == company.partner_id.country_id.id:
            if not partner.cnpj_cpf:
                errors.append(u'Destinatário - CNPJ/CPF')

        if not partner.street:
            errors.append(u'Destinatário / Endereço - Logradouro')

        if not partner.number:
            errors.append(u'Destinatário / Endereço - Número')

        if partner.country_id.id == company.partner_id.country_id.id:
            if not partner.zip:
                errors.append(u'Destinatário / Endereço - CEP')

        if partner.country_id.id == company.partner_id.country_id.id:
            if not partner.state_id:
                errors.append(u'Destinatário / Endereço - Estado')
            else:
                if not partner.state_id.ibge_code:
                    errors.append(u'Destinatário / Endereço - Código do IBGE \
                                  do estado')
                if not partner.state_id.name:
                    errors.append(u'Destinatário / Endereço - Nome do estado')

        if partner.country_id.id == company.partner_id.country_id.id:
            if not partner.l10n_br_city_id:
                errors.append(u'Destinatário / Endereço - Município')
            else:
                if not partner.l10n_br_city_id.name:
                    errors.append(u'Destinatário / Endereço - Nome do \
                                  município')
                if not partner.l10n_br_city_id.ibge_code:
                    errors.append(u'Destinatário / Endereço - Código do IBGE \
                                  do município')

        if not partner.country_id:
            errors.append(u'Destinatário / Endereço - País')
        else:
            if not partner.country_id.name:
                errors.append(u'Destinatário / Endereço - Nome do país')
            if not partner.country_id.bc_code:
                errors.append(u'Destinatário / Endereço - Cód. do BC do país')

        # produtos
        for inv_line in self.invoice_line:
            if inv_line.product_id:
                if not inv_line.product_id.default_code:
                    errors.append(
                        u'Prod: %s - Código do produto' % (
                            inv_line.product_id.name))
                prod = "Produto: %s - %s" % (inv_line.product_id.default_code,
                                             inv_line.product_id.name)
                if not inv_line.product_id.name:
                    errors.append(u'%s - Nome do produto' % prod)
                if not inv_line.quantity:
                    errors.append(u'%s - Quantidade' % prod)
                if not inv_line.price_unit:
                    errors.append(u'%s - Preco unitario' % prod)
                if inv_line.product_type == 'service':
                    if not inv_line.issqn_type:
                        errors.append(u'%s - Tipo do ISSQN' % prod)
                if not inv_line.pis_cst_id:
                    errors.append(u'%s - CST do PIS' % prod)
                if not inv_line.cofins_cst_id:
                    errors.append(u'%s - CST do COFINS' % prod)
        return errors

    @api.multi
    def validate_nfse(self):
        self.ensure_one()
        errors = self._hook_validation()
        if len(errors) > 0:
            msg = u"\n".join(
                ["Por favor corrija os erros antes de prosseguir"] + errors)
            raise Warning(u'Atenção !', msg)

    @api.multi
    def action_invoice_send_nfse(self):
        event_obj = self.env['l10n_br_account.document_event']
        base_nfse = self.env['base.nfse'].create({
            'invoice_id': self.id,
            'company_id': self.company_id.id,
            'city_code': self.company_id.l10n_br_city_id.ibge_code,
            'certificate': self.company_id.nfe_a1_file,
            'password': self.company_id.nfe_a1_password
        })

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
        return send

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
        base_nfse = self.env['base.nfse'].create({
            'invoice_id': self.id,
            'company_id': self.company_id.id,
            'city_code': self.company_id.l10n_br_city_id.ibge_code,
            'certificate': self.company_id.nfe_a1_file,
            'password': self.company_id.nfe_a1_password
        })

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
        base_nfse = self.env['base.nfse'].create({
            'invoice_id': self.id,
            'city_code': self.company_id.l10n_br_city_id.ibge_code
        })
        return base_nfse.print_pdf()
