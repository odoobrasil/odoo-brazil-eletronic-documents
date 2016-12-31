# -*- encoding: utf-8 -*-
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

import os
import re
import base64
import hashlib
from lxml import objectify
from datetime import datetime
from openerp import api, fields, models, tools

from openerp.addons.trust_base_nfse.service.xml import render
from openerp.addons.trust_base_nfse.service.signature import Assinatura
from openerp.addons.trust_base_nfse.service.signxml_test import assinar


class BaseNfse(models.TransientModel):
    _inherit = 'base.nfse'

    @api.multi
    def send_rps(self):
        self.ensure_one()
        if self.city_code == '6291':  # Campinas
            nfse = self._get_nfse_object()
            url = self._url_envio_nfse()

            client = self._get_client(url)
            path = os.path.dirname(os.path.dirname(__file__))
            xml_send = render(path, 'envio_rps.xml', nfse=nfse)

            xml_send = "<!DOCTYPE ns1:ReqEnvioLoteRPS [<!ATTLIST Lote Id ID #IMPLIED>]>" + \
                xml_send

            pfx_path = self._save_pfx_certificate()
            sign = Assinatura(pfx_path, self.password)
            reference = str('#%s' % nfse['lote_id'])
            xml_signed = sign.assina_xml(xml_send, reference)

            xml_signed = xml_signed.replace("""<!DOCTYPE ns1:ReqEnvioLoteRPS [
<!ATTLIST Lote Id ID #IMPLIED>
]>""", "")

            if self.invoice_id.company_id.nfe_environment == '2':
                response = client.service.testeEnviar(xml_signed)
            else:
                response = client.service.testeEnviar(xml_signed)

            import unicodedata
            response = unicodedata.normalize(
                'NFKD', response).encode(
                'ascii', 'ignore')

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-envio-rps.xml'.format(
                    nfse['lista_rps'][0]['assinatura']),
                 'data': base64.encodestring(xml_signed)},
                {'name': '{0}-retenvio-rps.xml'.format(
                    nfse['lista_rps'][0]['assinatura']),
                 'data': base64.encodestring(response or '')}
            ]}
            if 'RetornoEnvioLoteRPS' in response:
                response = response.replace(
                    '<?xml version="1.0" encoding="UTF-8"?>',
                    '')
                resp = objectify.fromstring(response)
                if resp['{}Cabecalho'].Sucesso:
                    if resp['{}Cabecalho'].Assincrono == 'S':
                        return self.check_nfse_by_lote()
                    else:
                        status['status'] = '100'
                        status['message'] = 'NFS-e emitida com sucesso'
                        status['success'] = resp['{}Cabecalho'].Sucesso
                        if self.invoice_id.company_id.nfe_environment == '1':
                            status['nfse_number'] = \
                                resp['{}ListaNFSe'].ConsultaNFSe[0].NumeroNFe
                            status['verify_code'] = \
                                resp['{}ListaNFSe'].ConsultaNFSe[0].CodigoVerificacao
                else:
                    status['status'] = resp['{}Erros'].Erro[0].Codigo
                    status['message'] = resp['{}Erros'].Erro[0].Descricao
                    status['success'] = resp['{}Cabecalho'].Sucesso
            else:
                status['status'] = '-1'
                status['message'] = response
                status['success'] = False

            return status

        return super(BaseNfse, self).send_rps()

    @api.multi
    def cancel_nfse(self):
        if self.city_code == '6291':  # Campinas
            url = self._url_envio_nfse()
            client = self._get_client(url)

            # TODO Preencher corretamente
            obj_cancelamento = {
                'cancelamento': {
                    'nota_id': self.invoice_id.internal_number}}

            path = os.path.dirname(os.path.dirname(__file__))
            xml_send = render(
                path, 'cancelamento.xml', **obj_cancelamento)

            response = client.service.cancelar(xml_send)

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-canc-envio.xml'.format(
                    obj_cancelamento['cancelamento']['nota_id']),
                 'data': base64.encodestring(xml_send)},
                {'name': '{0}-canc-envio.xml'.format(
                    obj_cancelamento['cancelamento']['nota_id']),
                 'data': base64.encodestring(response)}
            ]}
            if 'RetornoCancelamentoNFSe' in response:
                resp = objectify.fromstring(response)
                status['status'] = resp['{}Erros'].Erro[0].Codigo
                status['message'] = resp['{}Erros'].Erro[0].Descricao
                status['success'] = resp['{}Cabecalho'].Sucesso
            else:
                status['status'] = '-1'
                status['message'] = response
                status['success'] = False

            return status

        return super(BaseNfse, self).cancel_nfse()

    @api.multi
    def check_nfse_by_rps(self):
        if self.city_code == '6291':  # Campinas

            url = self._url_envio_nfse()
            client = self._get_client(url)

            obj_check = {}  # TODO Preencher corretamente

            path = os.path.dirname(os.path.dirname(__file__))
            xml_send = render(obj_check, path, 'consulta_nfse_por_rps.xml')

            response = client.service.consultarNFSeRps(xml_send)
            print response  # TODO Tratar resposta

        return super(BaseNfse, self).check_nfse_by_rps()

    @api.multi
    def check_nfse_by_lote(self):
        if self.city_code == '6291':  # Campinas
            url = self._url_envio_nfse()
            client = self._get_client(url)

            obj_consulta = {
                'consulta': {
                    'cidade': self.invoice_id.internal_number,
                    'cpf_cnpj': re.sub('[^0-9]', '', self.invoice_id.company_id.partner_id.cnpj_cpf or ''),
                    'lote': self.invoice_id.lote_nfse}}

            path = os.path.dirname(os.path.dirname(__file__))
            xml_send = render(obj_consulta, path, 'consulta_lote.xml')

            response = client.service.consultarLote(xml_send)

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-consulta-lote.xml'.format(
                    obj_consulta['consulta']['lote']),
                 'data': base64.encodestring(xml_send)},
                {'name': '{0}-ret-consulta-lote.xml'.format(
                    obj_consulta['consulta']['lote']),
                 'data': base64.encodestring(response)}
            ]}
            if 'RetornoConsultaLote' in response:
                resp = objectify.fromstring(response)
                if resp['{}Cabecalho'].sucesso:
                    status['status'] = '100'
                    status['message'] = 'NFS-e emitida com sucesso'
                    status['success'] = resp['{}Cabecalho'].Sucesso
                    status['nfse_number'] = resp['{}ListaNFSe'].ConsultaNFSe[
                        0].NumeroNFe
                    status['verify_code'] = resp['{}ListaNFSe'].ConsultaNFSe[
                        0].CodigoVerificacao
                else:
                    status['status'] = resp['{}Erros'].Erro[0].Codigo
                    status['message'] = resp['{}Erros'].Erro[0].Descricao
                    status['success'] = resp['{}Cabecalho'].Sucesso
            else:
                status['status'] = '-1'
                status['message'] = response
                status['success'] = False

            return status

        return super(BaseNfse, self).check_nfse_by_lote()

    @api.multi
    def print_pdf(self):
        if self.city_code == '6291':  # Campinas
            return self.env['report'].get_action(
                self, 'trust_nfse_campinas.danfse_report')

    def _url_envio_nfse(self):
        if self.city_code == '6291':  # Campinas
            return 'http://issdigital.campinas.sp.gov.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '5403':  # Uberlandia
            return 'http://udigital.uberlandia.mg.gov.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '0427':  # Belem-PA
            return 'http://www.issdigitalbel.com.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '9051':  # Campo Grande
            return 'http://issdigital.pmcg.ms.gov.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '5869':  # Nova Iguaçu
            return 'http://www.issmaisfacil.com.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '1219':  # Teresina
            return 'http://www.issdigitalthe.com.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '0921':  # São Luis
            return 'http://www.issdigitalslz.com.br/WsNFe2/LoteRps.jws?wsdl'
        elif self.city_code == '7145':  # Sorocaba
            return 'http://www.issdigitalsod.com.br/WsNFe2/LoteRps.jws?wsdl'

    def _get_nfse_object(self):
        if self.invoice_id:
            inv = self.invoice_id

            phone = inv.partner_id.phone or ''
            tomador = {
                'cpf_cnpj': re.sub('[^0-9]', '', inv.partner_id.cnpj_cpf or ''),
                'razao_social': inv.partner_id.legal_name or '',
                'logradouro': inv.partner_id.street or '',
                'numero': inv.partner_id.number or '',
                'complemento': inv.partner_id.street2 or '',
                'bairro': inv.partner_id.district or 'Sem Bairro',
                'cidade': inv.partner_id.l10n_br_city_id.siafi_code,
                'cidade_descricao': inv.company_id.partner_id.city or '',
                'uf': inv.partner_id.state_id.code,
                'cep': re.sub('[^0-9]', '', inv.partner_id.zip),
                'tipo_logradouro': 'Rua',
                'tipo_bairro': 'Normal',
                'ddd': re.sub('[^0-9]', '', phone.split(' ')[0]),
                'telefone': re.sub('[^0-9]', '', phone.split(' ')[1]),
                'inscricao_municipal': re.sub('[^0-9]', '', inv.partner_id.inscr_mun or '000000000'),
                'email': inv.partner_id.email or '',
            }

            phone = inv.partner_id.phone or ''
            prestador = {
                'cnpj': re.sub('[^0-9]', '', inv.company_id.partner_id.cnpj_cpf or ''),
                'razao_social': inv.company_id.partner_id.legal_name or '',
                'inscricao_municipal': re.sub('[^0-9]', '', inv.company_id.partner_id.inscr_mun or ''),
                'cidade': inv.company_id.partner_id.city or '',
                'tipo_logradouro': 'Rua',
                'ddd': re.sub('[^0-9]', '', phone.split(' ')[0]),
                'telefone': re.sub('[^0-9]', '', phone.split(' ')[1]),
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
                item = {
                    'descricao': inv_line.product_id.name[:80] or '',
                    'quantidade': str("%.0f" % inv_line.quantity),
                    'valor_unitario': str("%.2f" % (inv_line.price_unit)),
                    'valor_total': str("%.2f" % (inv_line.quantity * inv_line.price_unit)),
                }
                itens.append(item)
                aliquota_pis = inv_line.pis_percent
                aliquota_cofins = inv_line.cofins_percent
                aliquota_csll = inv_line.csll_percent
                aliquota_inss = inv_line.inss_percent
                aliquota_ir = inv_line.ir_percent
                aliquota_issqn = inv_line.issqn_percent

            valor_servico = inv.amount_total
            valor_deducao = 0.0
            codigo_atividade = re.sub('[^0-9]', '', inv.cnae_id.code or '')
            tipo_recolhimento = 'A'
            if inv.issqn_wh or inv.pis_wh or inv.cofins_wh or inv.csll_wh or inv.irrf_wh or inv.inss_wh:
                tipo_recolhimento = 'R'

            data_envio = datetime.strptime(
                inv.date_in_out,
                tools.DEFAULT_SERVER_DATETIME_FORMAT)
            data_envio = data_envio.strftime('%Y%m%d')

            assinatura = '%011dNF   %012d%s%s %s%s%015d%015d%010d%014d' % \
                (int(prestador['inscricao_municipal']),
                 int(inv.internal_number),
                 data_envio, inv.taxation, 'N', 'N' if tipo_recolhimento == 'A' else 'S',
                 valor_servico * 100,
                 valor_deducao * 100,
                 int(codigo_atividade),
                 int(tomador['cpf_cnpj']))
           
            assinatura = hashlib.sha1(assinatura).hexdigest()

            rps = [{
                'assinatura': assinatura,
                'tomador': tomador,
                'prestador': prestador,
                'serie': 'NF',  # inv.document_serie_id.code or '',
                'numero': inv.internal_number or '',
                'data_emissao': inv.date_in_out,
                'situacao': 'N',
                'serie_prestacao': '99',
                'codigo_atividade': codigo_atividade,
                'aliquota_atividade': str("%.4f" % aliquota_issqn),
                'tipo_recolhimento': tipo_recolhimento,
                'municipio_prestacao': tomador['cidade'],
                'municipio_descricao_prestacao': tomador['cidade_descricao'],
                'operacao': inv.operation,
                'tributacao': inv.taxation,
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
                'deducoes': deducoes,
                'itens': itens,
            }]

            nfse_object = {
                'cidade': '6291',
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
        return None
