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

import os
import re
import base64
import hashlib
import urllib2, httplib, socket
import logging
import suds

from pytrustnfe.certificado import Certificado
from pytrustnfe.nfse.paulistana import envio_lote_rps
from pytrustnfe.nfse.paulistana import teste_envio_lote_rps
from pytrustnfe.nfse.paulistana import cancelamento_nfe


from lxml import etree
from datetime import datetime
from openerp import api, fields, models, tools


class BaseNfse(models.TransientModel):
    _inherit = 'base.nfse'

    @api.multi
    def send_rps(self):
        self.ensure_one()
        if self.city_code == '50308':  # São Paulo
            self.date_format = '%Y-%m-%d'
            nfse = self._get_nfse_object()

            pfx_stream = base64.b64decode(self.certificate)
            certificado = Certificado(pfx_stream, self.password)

            if self.invoice_id.company_id.nfse_environment == '2':
                resposta = teste_envio_lote_rps(certificado, nfse=nfse)
            else:
                resposta = envio_lote_rps(certificado, nfse=nfse)

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-envio-rps.xml'.format(
                    nfse['lista_rps'][0]['numero']),
                 'data': base64.encodestring(resposta['sent_xml'])},
                {'name': '{0}-retenvio-rps.xml'.format(
                    nfse['lista_rps'][0]['numero']),
                 'data': base64.encodestring(resposta['received_xml'])}
            ]}
            resp = resposta['object']
            if resp:
                if resp.Cabecalho.Sucesso:
                    status['status'] = '100'
                    status['message'] = 'NFS-e emitida com sucesso'
                    status['success'] = resp.Cabecalho.Sucesso
                    if self.invoice_id.company_id.nfse_environment != '2':
                        status['nfse_number'] = resp.ListaNFSe.ConsultaNFSe[
                            0].NumeroNFe
                        status['verify_code'] = resp.ListaNFSe.ConsultaNFSe[
                            0].CodigoVerificacao
                else:
                    status['status'] = resp.Erro[0].Codigo
                    status['message'] = resp.Erro[0].Descricao
                    status['success'] = resp.Cabecalho.Sucesso
            else:
                status['status'] = -1
                status['message'] = resposta['received_xml']
                status['success'] = False
            return status

        return super(BaseNfse, self).send_rps()

    @api.multi
    def cancel_nfse(self):
        if self.city_code == '1':  # São Paulo
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
            sent_xml = client.last_sent()
            received_xml = client.last_received()

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-canc-envio.xml'.format(
                    obj_cancelamento['cancelamento']['nota_id']),
                 'data': base64.encodestring(sent_xml)},
                {'name': '{0}-canc-envio.xml'.format(
                    obj_cancelamento['cancelamento']['nota_id']),
                 'data': base64.encodestring(received_xml)}
            ]}
            if 'RetornoCancelamentoNFSe' in response:
                resp = objectify.fromstring(response)
                status['status'] = resp.Erros.Erro[0].Codigo
                status['message'] = resp.Erros.Erro[0].Descricao
                status['success'] = resp.Cabecalho.Sucesso
            else:
                status['status'] = '-1'
                status['message'] = response
                status['success'] = False

            return status

        return super(BaseNfse, self).cancel_nfse()

    @api.multi
    def check_nfse_by_rps(self):
        if self.city_code == '1':  # são Paulo

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
        if self.city_code == '1':  # São Paulo
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
            sent_xml = client.last_sent()
            received_xml = client.last_received()

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-consulta-lote.xml'.format(
                    obj_consulta['consulta']['lote']),
                 'data': base64.encodestring(sent_xml)},
                {'name': '{0}-ret-consulta-lote.xml'.format(
                    obj_consulta['consulta']['lote']),
                 'data': base64.encodestring(received_xml)}
            ]}
            if 'RetornoConsultaLote' in response:
                resp = objectify.fromstring(response)
                if resp.Cabecalho.sucesso:
                    status['status'] = '100'
                    status['message'] = 'NFS-e emitida com sucesso'
                    status['success'] = resp.Cabecalho.Sucesso
                    status['nfse_number'] = resp.ListaNFSe.ConsultaNFSe[
                        0].NumeroNFe
                    status['verify_code'] = resp.ListaNFSe.ConsultaNFSe[
                        0].CodigoVerificacao
                else:
                    status['status'] = resp.Erros.Erro[0].Codigo
                    status['message'] = resp.Erros.Erro[0].Descricao
                    status['success'] = resp.Cabecalho.Sucesso
            else:
                status['status'] = '-1'
                status['message'] = response
                status['success'] = False

            return status

        return super(BaseNfse, self).check_nfse_by_lote()

    @api.multi
    def print_pdf(self, invoice):
        if self.city_code == '50308':  # São Paulo IBGE Code
            return self.env['report'].get_action(
                invoice, 'nfse_sao_paulo.danfse_report')

    def _url_envio_nfse(self):
        if self.city_code == '50308':  # São Paulo
            return 'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx?wsdl'

    def _get_nfse_object(self):
        result = super(BaseNfse, self)._get_nfse_object()
        if self.invoice_id:
            inv = self.invoice_id

            result['lista_rps'][0]['codigo_atividade'] = \
                re.sub('[^0-9]', '', inv.invoice_line[0].service_type_id.code or '')

            cnpj_cpf = result['lista_rps'][0]['tomador']['cpf_cnpj']
            data_envio = result['lista_rps'][0]['data_emissao']
            inscr = result['lista_rps'][0]['prestador']['inscricao_municipal']
            iss_retido = 'N'
            valor_servico = float(result['lista_rps'][0]['valor_servico'])
            valor_deducao = float(result['lista_rps'][0]['valor_deducao'])
            tipo_cpfcnpj = result['lista_rps'][0]['tomador']['tipo_cpfcnpj']
            codigo_atividade = result['lista_rps'][0]['codigo_atividade']
            tipo_recolhimento = 'T'  # T – Tributado em São Paulo

            assinatura = ('%s%s%s%s%sN%s%s%s%s%s%s') % (
                str(inscr).zfill(8),
                inv.document_serie_id.code.ljust(5),
                str(inv.internal_number).zfill(12),
                str(data_envio[0:4] + data_envio[5:7] + data_envio[8:10]),
                str(tipo_recolhimento),
                str(iss_retido),
                str(int(valor_servico*100)).zfill(15),
                str(int(valor_deducao*100)).zfill(15),
                str(codigo_atividade).zfill(5),
                str(tipo_cpfcnpj),
                str(cnpj_cpf).zfill(14)
                )
            result['lista_rps'][0]['assinatura'] = assinatura
            if result['lista_rps'][0]['tomador']['cidade'] != \
               result['lista_rps'][0]['prestador']['cidade']:
                del result['lista_rps'][0]['tomador']['inscricao_municipal']


        return result

    def _valida_schema(self, xml, arquivo_xsd):
        '''Função que valida um XML usando lxml do Python via arquivo XSD'''
        # Carrega o esquema XML do arquivo XSD
        xsd = etree.XMLSchema(file=arquivo_xsd)
        # Converte o XML passado em XML do lxml
        xml = etree.fromstring(str(xml))
        # Verifica a validade do xml
        erros = []
        if not xsd(xml):
            # Caso tenha erros, cria uma lista de erros
            for erro in xsd.error_log:
                erros.append({
                    'message' : erro.message,
                    'domain' : erro.domain,
                    'type' : erro.type,
                    'level' : erro.level,
                    'line' : erro.line,
                    'column' : erro.column,
                    'filename' : erro.filename,
                    'domain_name': erro.domain_name,
                    'type_name' : erro.type_name,
                    'level_name' : erro.level_name
                })
                print "erro %s, linha %s" % (erro.message, erro.line)
        # Retorna os erros, sendo uma lista vazia caso não haja erros
        return erros
