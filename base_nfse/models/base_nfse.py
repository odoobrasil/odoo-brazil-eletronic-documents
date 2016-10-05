# -*- encoding: utf-8 -*-
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

import re
import base64
import requests
import suds.client
import suds_requests
from uuid import uuid4
from datetime import datetime
from ..service.certificate import converte_pfx_pem
from openerp import api, fields, models
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT


class BaseNfse(models.Model):
    _name = 'base.nfse'

    date_format = '%Y%m%d'
    date_hour_format = '%Y%m%d%H%M%S'

    def _company_certificate(self):
        for item in self:
            item.certificate = self.env.user.company_id.nfe_a1_file

    city_code = fields.Char(u'Código Cidade', size=100)
    company_id = fields.Many2one('res.company', string=u'Empresa')
    invoice_id = fields.Many2one('account.invoice', string=u'Fatura')
    name = fields.Char('Nome', size=100)
    certificate = fields.Binary('Certificado', default=_company_certificate)
    password = fields.Char('Senha', size=100)

    def _url_envio_rps(self):
        return ''

    def _url_envio_nfse(self):
        return ''

    def _url_cancelamento_nfse(self):
        return ''

    def _url_consulta_lote_rps(self):
        return ''

    def _url_consulta_nfse_por_rps(self):
        return ''

    def _nfse_invoice_line_data(self, inv_line):
        item = {
            'descricao': inv_line.product_id.name_template or '',
            'quantidade': str("%.0f" % inv_line.quantity),
            'valor_unitario': str("%.2f" % (inv_line.price_unit)),
            'valor_total': str("%.2f" %
                               (inv_line.quantity * inv_line.price_unit)),
        }
        return item

    def _get_nfse_object(self):
        """
        Sobrescrever este método para adicionar novos itens ao gerar o xml.
        Returns:
            dict: retorna um dicionário com os dados da nfse
         """
        if not self.invoice_id:
            return {}

        inv = self.invoice_id
        city_tomador = inv.partner_id.l10n_br_city_id
        tomador = {
            'tipo_cpfcnpj': 2 if inv.partner_id.is_company else 1,
            'cpf_cnpj': re.sub('[^0-9]', '', inv.partner_id.cnpj_cpf or ''),
            'razao_social': inv.partner_id.legal_name or '',
            'logradouro': inv.partner_id.street or '',
            'numero': inv.partner_id.number or '',
            'complemento': inv.partner_id.street2 or '',
            'bairro': inv.partner_id.district or 'Sem Bairro',
            'cidade': '%s%s' % (city_tomador.state_id.ibge_code,
                                city_tomador.ibge_code),
            'cidade_descricao': inv.partner_id.l10n_br_city_id.name or '',
            'uf': inv.partner_id.state_id.code,
            'cep': re.sub('[^0-9]', '', inv.partner_id.zip),
            'telefone': re.sub('[^0-9]', '', inv.partner_id.phone or ''),
            'inscricao_municipal': re.sub(
                '[^0-9]', '', inv.partner_id.inscr_mun or ''),
            'email': inv.partner_id.email or '',
        }
        city_prestador = inv.company_id.partner_id.l10n_br_city_id
        prestador = {
            'cnpj': re.sub(
                '[^0-9]', '', inv.company_id.partner_id.cnpj_cpf or ''),
            'razao_social': inv.company_id.partner_id.legal_name or '',
            'inscricao_municipal': re.sub(
                '[^0-9]', '', inv.company_id.partner_id.inscr_mun or ''),
            'cidade': '%s%s' % (city_prestador.state_id.ibge_code,
                                city_prestador.ibge_code),
            'telefone': re.sub('[^0-9]', '', inv.company_id.phone or ''),
            'email': inv.company_id.partner_id.email or '',
        }

        aliquota_pis = 0.0
        aliquota_cofins = 0.0
        aliquota_csll = 0.0
        aliquota_inss = 0.0
        aliquota_ir = 0.0
        aliquota_issqn = 0.0
        deducoes = []
        itens = []
        for inv_line in inv.invoice_line:
            item = self._nfse_invoice_line_data(inv_line)
            itens.append(item)

            aliquota_pis = inv_line.pis_percent
            aliquota_cofins = inv_line.cofins_percent
            aliquota_csll = inv_line.csll_percent
            aliquota_inss = inv_line.inss_percent
            aliquota_ir = inv_line.ir_percent
            aliquota_issqn = inv_line.issqn_percent

        data_envio = datetime.strptime(
            inv.date_in_out,
            DEFAULT_SERVER_DATETIME_FORMAT)
        data_envio = data_envio.strftime(self.date_format)

        rps = [{
            'tomador': tomador,
            'prestador': prestador,
            'numero': inv.number or '',
            'data_emissao': data_envio,
            'serie': inv.document_serie_id.code or '',
            'aliquota_atividade': str("%.4f" % aliquota_issqn),
            'municipio_prestacao': inv.provider_city_id.ibge_code,
            'municipio_descricao_prestacao': inv.provider_city_id.name or '',
            'valor_pis': str("%.2f" % inv.pis_value),
            'valor_cofins': str("%.2f" % inv.cofins_value),
            'valor_csll': str("%.2f" % inv.csll_value),
            'valor_inss': str("%.2f" % inv.inss_value),
            'valor_ir': str("%.2f" % inv.ir_value),
            'aliquota_pis': str("%.2f" % aliquota_pis),
            'aliquota_cofins': str("%.2f" % aliquota_cofins),
            'aliquota_csll': str("%.2f" % aliquota_csll),
            'aliquota_inss': str("%.2f" % aliquota_inss),
            'aliquota_ir': str("%.2f" % aliquota_ir),
            'valor_servico': str("%.2f" % inv.amount_total),
            'valor_deducao': '0',
            'descricao': "%s\n%s" % (inv.comment, inv.fiscal_comment),
            'deducoes': deducoes,
            'itens': itens,
        }]

        nfse_object = {
            'cidade': prestador['cidade'],
            'cpf_cnpj': prestador['cnpj'],
            'remetente': prestador['razao_social'],
            'transacao': '',
            'data_inicio': data_envio,
            'data_fim': data_envio,
            'total_rps': '1',
            'total_servicos': str("%.2f" % inv.amount_total),
            'total_deducoes': '0',
            'lote_id': '%s' % inv.lote_nfse,
            'lista_rps': rps
        }
        return nfse_object

    def _validate_result(self, result):
        pass

    def _save_pfx_certificate(self):
        pfx_tmp = '/tmp/' + uuid4().hex
        arq_temp = open(pfx_tmp, 'w')
        arq_temp.write(base64.b64decode(self.certificate))
        arq_temp.close()
        return pfx_tmp

    def _preparar_temp_pem(self):
        chave_temp = '/tmp/' + uuid4().hex
        certificado_temp = '/tmp/' + uuid4().hex

        pfx_tmp = self._save_pfx_certificate()

        chave, certificado = converte_pfx_pem(pfx_tmp, self.password)
        arq_temp = open(chave_temp, 'w')
        arq_temp.write(chave)
        arq_temp.close()

        arq_temp = open(certificado_temp, 'w')
        arq_temp.write(certificado)
        arq_temp.close()

        return certificado_temp, chave_temp

    def _get_client(self, base_url):
        cache_location = '/tmp/suds'
        cache = suds.cache.DocumentCache(location=cache_location)

        session = requests.Session()

        return suds.client.Client(
            base_url,
            cache=cache,
            transport=suds_requests.RequestsTransport(session)
        )

    @api.multi
    def send_rps(self):
        pass

    @api.multi
    def cancel_nfse(self):
        pass

    @api.multi
    def check_nfse_by_rps(self):
        pass

    @api.multi
    def check_nfse_by_lote(self):
        pass

    @api.multi
    def print_pdf(self):
        pass
