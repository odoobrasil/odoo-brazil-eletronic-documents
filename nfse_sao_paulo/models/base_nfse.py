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
import urllib2, httplib, socket
import logging
import suds
#TODO - REMOVER
import json
from lxml import etree
from datetime import datetime
from openerp import api, fields, models, tools
from suds.client import Client
from suds.sax.text import Raw
from suds.transport.http import HttpTransport, Reply, TransportError
from suds.plugin import MessagePlugin
from openerp.addons.base_nfse.service.xml import render
from openerp.addons.base_nfse.service.signature import Assinatura

from assinatura import AssinaturaA1
logging.getLogger('suds.client').setLevel(logging.CRITICAL)
logging.basicConfig(level=logging.INFO)
logging.getLogger('suds.transport').setLevel(logging.DEBUG)

class EnvelopeFixer(MessagePlugin): 

    def sending(self, context):
        # removendo prefixo
        context.envelope = re.sub( 'ns[0-9]:', '', context.envelope )
        context.envelope = re.sub( '<SOAP-ENV:Header/>', '', str(context.envelope) )
        context.envelope = re.sub( '<VersaoSchema>', '', str(context.envelope) )
        context.envelope = re.sub( '</VersaoSchema>', '', str(context.envelope) )
        context.envelope = re.sub( '<?xml version="1.0"?>', '', str(context.envelope) )
        #context.envelope = re.sub( '</ConsultaCNPJRequest>', '', str(context.envelope) )
        return context.envelope

    def marshalled(self, context): 
        #print context.envelope.str()
        #import pudb;pu.db
        envelope = context.envelope    
        envelope.name = 'Envelope'
        envelope.setPrefix('soap12')
        envelope.nsprefixes = {
           'xsi' : 'http://www.w3.org/2001/XMLSchema-instance', 
           'soap12': 'http://www.w3.org/2003/05/soap-envelope',
           'xsd' : 'http://www.w3.org/2001/XMLSchema'
           
        }
        env1 = envelope.getRoot()
        
        consulta = envelope.getChildren()[1][0]                                                                             
        consulta.set("xmlns", "http://www.prefeitura.sp.gov.br/nfe")
        body_ele = envelope.getChildren()[1]
        body_ele.setPrefix("soap12")
        context.envelope = re.sub( 'ns[0-9]:', '', str(context.envelope) )
        context.envelope = re.sub( '<SOAP-ENV:Header/>', '', str(context.envelope) )
        context.envelope = re.sub( '<VersaoSchema>', '', str(context.envelope) )
        context.envelope = re.sub( '</VersaoSchema>', '', str(context.envelope) )
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
        if self.city_code == '1':  # São Paulo
            nfse = self._get_nfse_object()
            url = self._url_envio_nfse()
            path = os.path.dirname(os.path.dirname(__file__))
            import pudb;pu.db
            #TODO - Buscar do certificado
            t = HTTPSClientCertTransport('/home/carlos/certificado/key2.pem',
                                         '/home/carlos/certificado/cert.pem')
            location = 'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx'

            envelope = EnvelopeFixer()
            client = Client(url, location = location, transport = t, plugins=[envelope])
            
            xml_send = render(path, 'envio_loterps.xml', nfse=nfse)
            # tirei pq estava deixando uma linha em branco
            #xml_send = "<!DOCTYPE EnvioLoteRPS>" + \
            #    xml_send

            pfx_path = self._save_pfx_certificate()
            sign = Assinatura(pfx_path, self.password)

            reference = ""
            xml_signed = sign.assina_xml(xml_send, reference)

            #xml_signed = xml_signed.replace("""<!DOCTYPE EnvioLoteRPS>""", "")
            #xml_signed = xml_signed.replace("""<!DOCTYPE ns1:PedidoEnvioLoteRPS [ \
            #   <!ATTLIST Lote Id ID #IMPLIED> \
            #   ]>""", "")
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
            #response = client.service.ConsultaCNPJ(xml_signed)
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
    def print_pdf(self):
        if self.city_code == '1':
            return self.env['report'].get_action(
                self, 'trust_nfse_campinas.danfse_report')

    def _url_envio_nfse(self):
        if self.city_code == '1':  # São Paulo
            return 'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx?wsdl'
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
            cpf_cnpj = re.sub('[^0-9]', '', inv.partner_id.cnpj_cpf or '')
            if len(cpf_cnpj) == 11:
                tipo_cpfcnpj = 1
            else:
                tipo_cpfcnpj = 2
            tomador = {
                'cpf_cnpj': re.sub('[^0-9]', '', inv.partner_id.cnpj_cpf or ''),
                'tipo_cpfcnpj': tipo_cpfcnpj,
                'razao_social': inv.partner_id.legal_name or '',
                'logradouro': inv.partner_id.street or '',
                'numero': inv.partner_id.number or '',
                'complemento': inv.partner_id.street2 or '',
                'bairro': inv.partner_id.district or 'Sem Bairro',
                'cidade': '%s%s' % (inv.partner_id.state_id.ibge_code, inv.partner_id.l10n_br_city_id.ibge_code),
                'cidade_descricao': inv.company_id.partner_id.city or '',
                'uf': inv.partner_id.state_id.code,
                'cep': re.sub('[^0-9]', '', inv.partner_id.zip),
                'tipo_logradouro': 'Rua',
                'tipo_bairro': 'Normal',
                'ddd': re.sub('[^0-9]', '', phone.split(' ')[0]),
                'telefone': re.sub('[^0-9]', '', phone.split(' ')[1]),
                'inscricao_municipal': inv.partner_id.inscr_mun or '',
                'email': inv.partner_id.email or '',
            }

            phone = inv.partner_id.phone or ''
            prestador = {
                'cnpj': re.sub('[^0-9]', '', inv.company_id.partner_id.cnpj_cpf or ''),
                'razao_social': inv.company_id.partner_id.legal_name or '',
                'inscricao_municipal': re.sub('[^0-9]', '', inv.company_id.partner_id.inscr_mun or ''),
                'cod_municipio': '%s%s' % (inv.company_id.partner_id.state_id.ibge_code, inv.company_id.partner_id.l10n_br_city_id.ibge_code),
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
                    'quantidade': str("%.4f" % inv_line.quantity),
                    'valor_unitario': str("%.4f" % (inv_line.price_unit)),
                    'valor_total': str("%.2f" % (inv_line.quantity * inv_line.price_unit)),
                }
                itens.append(item)
                aliquota_pis = inv_line.pis_percent
                aliquota_cofins = inv_line.cofins_percent
                #aliquota_csll = inv_line.csll_percent
                #aliquota_inss = inv_line.inss_percent
                #aliquota_ir = inv_line.ir_percent
                #aliquota_issqn = inv_line.issqn_percent
                #csll_value = inv.csll_value
                #inss_value = inv.inss_value
                #ir_value = inv.ir_value
                csll_value = 0.0
                inss_value = 0.0
                ir_value = 0.0

            valor_servico = inv.amount_total
            valor_deducao = 0.0
            codigo_atividade = re.sub('[^0-9]', '', inv.cnae_id.code or '')
            #tipo_recolhimento = 'A'
            tipo_recolhimento = 'N' # 03/02/2016 peguei no xsd - TiposNFe_v01.xsd
            #if inv.issqn_wh or inv.pis_wh or inv.cofins_wh or inv.csll_wh or inv.irrf_wh or inv.inss_wh:
            #    tipo_recolhimento = 'R'

            data_envio = datetime.strptime(
                inv.date_in_out,
                tools.DEFAULT_SERVER_DATETIME_FORMAT)
            data_envio = data_envio.strftime('%Y%m%d')

            print tomador['cpf_cnpj']
            cnpj_cpf = int(tomador['cpf_cnpj'])
            assinatura = '%011dNF   %012d%s%s %s%s%015d%015d%010d%014d' % \
                (int(prestador['inscricao_municipal']),
                 int(inv.internal_number),
                 data_envio, inv.taxation, 'N', tipo_recolhimento,
                 valor_servico,
                 valor_deducao,
                 int(codigo_atividade),
                 cnpj_cpf
                 )

            assinatura = hashlib.sha1(assinatura).hexdigest()
            if not tomador['cidade_descricao']:
                desc = 'Teste de Envio de Arquivo'
            rps = [{
                'descricao': 'RPS DE TESTE',
                'assinatura': assinatura,
                'tomador': tomador,
                'prestador': prestador,
                'serie': 'NF',  # inv.document_serie_id.code or '',
                'numero': inv.internal_number or '',
                'data_emissao': "%s-%s-%s" % (inv.date_in_out[:4],inv.date_in_out[5:7], inv.date_in_out[8:10]),
                'situacao': 'N',
                'serie_prestacao': '99',
                'codigo_atividade': codigo_atividade,
                'aliquota_atividade': str("%.2f" % aliquota_issqn),
                'tipo_recolhimento': tipo_recolhimento,
                'municipio_prestacao': tomador['cidade'],
                'municipio_descricao_prestacao': tomador['cidade_descricao'],
                'operacao': inv.operation,
                'tributacao': inv.taxation,
                'valor_pis': str("%.2f" % inv.pis_value),
                'valor_cofins': str("%.2f" % inv.cofins_value),
                'valor_csll': str("%.2f" % csll_value),
                'valor_inss': str("%.2f" % inss_value),
                'valor_ir': str("%.2f" % ir_value),
                'aliquota_pis': aliquota_pis,
                'aliquota_cofins': aliquota_cofins,
                'aliquota_csll': aliquota_csll,
                'aliquota_inss': aliquota_inss,
                'aliquota_ir': aliquota_ir,
                'deducoes': deducoes,
                'itens': itens,
            }]

            nfse_object = {
                'cidade': '1',
                'cpf_cnpj': prestador['cnpj'],
                'remetente': prestador['razao_social'],
                'transacao': inv.transaction,
                'data_inicio': datetime.now(),
                'data_fim': datetime.now(),
                'total_rps': '1',
                'total_servicos': str("%.2f" % inv.amount_total),
                'total_deducoes': '0.00',
                'lote_id': 'lote:%s' % inv.lote_nfse,
                'lista_rps': rps
            }
            return nfse_object
        return None


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
