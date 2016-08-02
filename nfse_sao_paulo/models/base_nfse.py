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
from pytrustnfe.nfse.paulistana import teste_envio_lote_rps
from pytrustnfe.nfse.paulistana import cancelamento_nfe


from lxml import etree
from datetime import datetime
from openerp import api, fields, models, tools
from suds.client import Client
from suds.sax.text import Raw
from suds.transport.http import HttpTransport, Reply, TransportError
from suds.plugin import MessagePlugin
from openerp.addons.base_nfse.service.xml import render
from openerp.addons.base_nfse.service.signature import Assinatura

logging.getLogger('suds.client').setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)

class EnvelopeFixer(MessagePlugin):

    def sending(self, context):
        # removendo prefixo
        context.envelope = re.sub( 'ns[0-9]:', '', context.envelope )
        context.envelope = re.sub( '<SOAP-ENV:Header/>', '', str(context.envelope) )
        context.envelope = re.sub( '</VersaoSchema>', '</MensagemXML>', str(context.envelope) )
        context.envelope = re.sub( '<VersaoSchema>', '<VersaoSchema>1</VersaoSchema><MensagemXML>', str(context.envelope) )
        return context.envelope

    def marshalled(self, context):
        #print context.envelope.str()
        envelope = context.envelope
        envelope.name = 'Envelope'
        envelope.setPrefix('soap12')
        envelope.nsprefixes = {
           'xsi' : 'http://www.w3.org/2001/XMLSchema-instance',
           'soap12': 'http://www.w3.org/2003/05/soap-envelope',
           'xsd' : 'http://www.w3.org/2001/XMLSchema'

        }
        body_ele = envelope.getChildren()[1]
        body_ele.setPrefix("soap12")
        consulta = envelope.getChildren()[1][0]
        consulta.set("xmlns", "http://www.prefeitura.sp.gov.br/nfe")
        return Raw(context)


class HTTPSClientAuthHandler(urllib2.HTTPSHandler):
    def __init__(self, key, cert):
        urllib2.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert

    def https_open(self, req):
        #Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)

    def getConnection(self, host, timeout=300):
        return httplib.HTTPSConnection(host,
                                       key_file=self.key,
                                       cert_file=self.cert)


class HTTPSClientCertTransport(HttpTransport):
    def __init__(self, key, cert, *args, **kwargs):
        HttpTransport.__init__(self, *args, **kwargs)
        self.key = key
        self.cert = cert

    def u2open(self, u2request):
        """
        Open a connection.
        @param u2request: A urllib2 request.
        @type u2request: urllib2.Requet.
        @return: The opened file-like urllib2 object.
        @rtype: fp
        """
        tm = self.options.timeout
        url = urllib2.build_opener(HTTPSClientAuthHandler(self.key, self.cert))
        if self.u2ver() < 2.6:
            socket.setdefaulttimeout(tm)
            return url.open(u2request)
        else:
            return url.open(u2request, timeout=tm)


class BaseNfse(models.TransientModel):
    _inherit = 'base.nfse'

    @api.multi
    def send_rps(self):
        self.ensure_one()
        if self.city_code == '50308':  # São Paulo
            nfse = self._get_nfse_object()

            pfx_stream = base64.b64decode(self.certificate)

            certificado = Certificado(pfx_stream, self.password)
            teste_envio_lote_rps(certificado, nfse=nfse)


            
            t = HTTPSClientCertTransport('/home/carlos/certificado/key2.pem',
                                         '/home/carlos/certificado/cert.pem')
            location = 'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx'

            envelope = EnvelopeFixer()
            client = Client(url, location=location, transport=t, plugins=[envelope])

            xml_send = render(path, 'envio_loterps.xml', nfse=nfse)

            reference = ""
            xml_signed = sign.assina_xml(xml_send, reference)

            #TODO - arrumar para pasta do sistema
            arq_temp = open('/home/carlos/tmp/pyxmlsec2.xml', 'w')
            arq_temp.write(xml_signed)
            arq_temp.close()

            #TODO - arrumar para pasta do sistema
            valida_schema = self._valida_schema(xml_signed, '/home/carlos/schemas/nfse/PedidoEnvioLoteRPS_v01.xsd')

            if len(valida_schema):
                erros = "Erro(s) no XML: \n"
                for erro in valida_schema:
                    erros += erro['type_name'] + ': ' + erro['message'] + '\n'
                raise ValueError(erros)
            try:
                response = client.service.TesteEnvioLoteRPS(xml_signed)
            except suds.WebFault, e:
                print e.fault.faultstring
                print e.document

            x = Raw(response)
            arq_temp = open('/home/carlos/tmp/retorno_enviolote.xml', 'w')
            arq_temp.write(x)
            arq_temp.close()

            print response

            received_xml = client.last_received()

            status = {'status': '', 'message': '', 'files': [
                {'name': '{0}-envio-rps.xml'.format(
                    nfse['lista_rps'][0]['assinatura']),
                 'data': base64.encodestring(sent_xml)},
                {'name': '{0}-retenvio-rps.xml'.format(
                    nfse['lista_rps'][0]['assinatura']),
                 'data': base64.encodestring(received_xml)}
            ]}
            if 'RetornoEnvioLoteRPS' in response:
                resp = objectify.fromstring(response)
                if resp.Cabecalho.sucesso:
                    if resp.Cabecalho.Assincrono == 'S':
                        return self.check_nfse_by_lote()
                    else:
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

            cnpj_cpf = result['lista_rps'][0]['tomador']['cpf_cnpj']
            data_envio = result['lista_rps'][0]['data_emissao']
            inscr = result['lista_rps'][0]['prestador']['inscricao_municipal']
            iss_retido = 0
            valor_servico = 0
            valor_deducao = 0
            tipo_cpfcnpj = 0
            codigo_atividade = '123'
            tipo_recolhimento = 'T'  # T – Tributado em São Paulo
            assinatura = ('%s%s%s%s%sN%s%s%s%s%s%s3%sN') % (
                str().zfill(8),
                inv.document_serie_id.code.ljust(5),
                str(inv.internal_number).zfill(12),
                str(data_envio[0:4] + data_envio[4:6] + data_envio[6:8]),
                str(tipo_recolhimento),
                str(iss_retido),
                str(int(valor_servico*100)).zfill(15),
                str(int(valor_deducao*100)).zfill(15),
                str(codigo_atividade).zfill(5),
                str(tipo_cpfcnpj),
                str(cnpj_cpf).zfill(14),
                str('').zfill(14)
                )
            assinatura = hashlib.sha1(assinatura).hexdigest()
            if not result['lista_rps'][0]['tomador']['cidade_descricao']:
                desc = 'Teste de Envio de Arquivo'

        return result

    def _valida_schema(self, xml, arquivo_xsd):
        '''Função que valida um XML usando lxml do Python via arquivo XSD'''
        # Carrega o esquema XML do arquivo XSD
        xsd = etree.XMLSchema(file = arquivo_xsd)
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
