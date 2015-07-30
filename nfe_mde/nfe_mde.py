# coding=utf-8
###############################################################################
#                                                                             #
# Copyright (C) 2015  Danimar Ribeiro www.trustcode.com.br                    #
#                                                                             #
# This program is free software: you can redistribute it and/or modify        #
# it under the terms of the GNU Affero General Public License as published by #
# the Free Software Foundation, either version 3 of the License, or           #
# (at your option) any later version.                                         #
#                                                                             #
# This program is distributed in the hope that it will be useful,             #
# but WITHOUT ANY WARRANTY; without even the implied warranty of              #
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the               #
# GNU Affero General Public License for more details.                         #
#                                                                             #
# You should have received a copy of the GNU Affero General Public License    #
# along with this program.  If not, see <http://www.gnu.org/licenses/>.       #
###############################################################################


from datetime import datetime
from openerp import models, api, fields
from .service.mde import download_nfe, send_event
from openerp.addons.nfe.sped.nfe.validator.config_check import \
    validate_nfe_configuration


class L10n_brDocumentEvent(models.Model):
    _inherit = 'l10n_br_account.document_event'

    mde_event_id = fields.Many2one('nfe.mde', string="Manifesto")


class Nfe_Mde(models.Model):
    _name = 'nfe.mde'
    _rec_name = 'nSeqEvento'
    _inherit = [
        'ir.needaction_mixin'
    ]

    company_id = fields.Many2one('res.company', string="Empresa")
    chNFe = fields.Char(string="Chave de Acesso", size=50, readonly=True)
    nSeqEvento = fields.Char(
        string="Número Sequencial", readonly=True, size=20)
    CNPJ = fields.Char(string="CNPJ", readonly=True, size=20)
    IE = fields.Char(string="RG/IE", readonly=True, size=20)
    xNome = fields.Char(string="Razão Social", readonly=True, size=200)
    partner_id = fields.Many2one('res.partner', string='Fornecedor',
                                 readonly=True)
    dEmi = fields.Datetime(string="Data Emissão", readonly=True)
    tpNF = fields.Integer(string="Tipo de Operação", readonly=True)
    vNF = fields.Float(string="Valor Total da NF-e",
                       readonly=True, digits=(18, 6))
    cSitNFe = fields.Integer(string="Situação da NF-e", readonly=True)
    state = fields.Selection(string="Situação da Manifestação", readonly=True,
                             selection=[
                                 ('pending', 'Pendente'),
                                 ('ciente', 'Ciente da operação'),
                                 ('confirmado', 'Confirmada operação'),
                                 ('desconhecido', 'Desconhecimento'),
                                 ('nao_realizado', 'Não realizado')
                             ])
    formInclusao = fields.Char(string="Forma de Inclusão", readonly=True)
    dataInclusao = fields.Datetime(string="Data de Inclusão", readonly=True)
    versao = fields.Integer(string="Versão", readonly=True)
    file_path = fields.Char(string="Local Xml", size=300, readonly=True)

    document_event_ids = fields.One2many(
        'l10n_br_account.document_event',
        'mde_event_id', string="Documentos eletrônicos")

    def _needaction_domain_get(self, cr, uid, context=None):
        return [('state', '=', 'pending')]

    def _create_event(self, response, nfe_result, type_event='13'):
        return {
            'type': type_event, 'response': response,
            'company_id': self.company_id.id,
            'file_returned': nfe_result['file_returned'],
            'status': nfe_result['code'], 'message': nfe_result['message'],
            'create_date': datetime.now(), 'write_date': datetime.now(),
            'end_date': datetime.now(), 'state': 'done',
            'origin': response, 'mde_event_id': self.id
        }

    @api.one
    def action_known_emission(self):
        validate_nfe_configuration(self.company_id)
        nfe_result = send_event(
            self.company_id, self.chNFe, 'ciencia_operacao')
        env_events = self.env['l10n_br_account.document_event']

        event = self._create_event('Ciência da operação', nfe_result)

        if nfe_result['code'] == '135':
            self.state = 'ciente'
        elif nfe_result['code'] == '573':
            self.state = 'ciente'
            event['response'] = 'Ciência da operação já previamente realizada'
        else:
            event['response'] = 'Ciência da operação sem êxito'

        env_events.create(event)
        return True

    @api.one
    def action_confirm_operation(self):
        validate_nfe_configuration(self.company_id)
        nfe_result = send_event(
            self.company_id,
            self.chNFe,
            'confirma_operacao')
        env_events = self.env['l10n_br_account.document_event']

        event = self._create_event('Confirmação da operação', nfe_result)

        if nfe_result['code'] == '135':
            self.state = 'confirmado'
        else:
            event['response'] = 'Confirmação da operação sem êxito'

        env_events.create(event)
        return True

    @api.one
    def action_unknown_operation(self):
        validate_nfe_configuration(self.company_id)
        nfe_result = send_event(
            self.company_id,
            self.chNFe,
            'desconhece_operacao')
        env_events = self.env['l10n_br_account.document_event']

        event = self._create_event('Desconhecimento da operação', nfe_result)

        if nfe_result['code'] == '135':
            self.state = 'desconhecido'
        else:
            event['response'] = 'Desconhecimento da operação sem êxito'

        env_events.create(event)
        return True

    @api.one
    def action_not_operation(self):
        validate_nfe_configuration(self.company_id)
        nfe_result = send_event(
            self.company_id,
            self.chNFe,
            'nao_realizar_operacao')
        env_events = self.env['l10n_br_account.document_event']
        event = self._create_event('Operação não realizada', nfe_result)
        if nfe_result['code'] == '135':
            self.state = 'nap_realizado'
        else:
            event['response'] = 'Tentativa de Operação não realizada sem êxito'

        env_events.create(event)
        return True

    @api.one
    def action_download_xml(self):
        validate_nfe_configuration(self.company_id)
        nfe_result = download_nfe(self.company_id, [self.chNFe])
        env_events = self.env['l10n_br_account.document_event']

        if nfe_result['code'] == '140':
            event = self._create_event('Download NFe concluido', nfe_result,
                                       type_event='10')
            env_events.create(event)

        else:
            event = self._create_event('Download NFe não efetuado', nfe_result,
                                       type_event='10')
            env_events.create(event)
        return True
