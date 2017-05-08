# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import base64

from pytrustnfe.certificado import Certificado
from pytrustnfe.nfse.paulistana import envio_lote_rps
from pytrustnfe.nfse.paulistana import teste_envio_lote_rps
from pytrustnfe.nfse.paulistana import consulta_lote
from pytrustnfe.nfse.paulistana import cancelamento_nfe

from openerp import api,  models


class BaseNfse(models.TransientModel):
    _inherit = 'base.nfse'

    def _create_status(self, resposta, name):
        status = {'status': '', 'message': '', 'files': [
            {'name': '{0}.xml'.format(name),
             'data': base64.encodestring(resposta['sent_xml'])},
            {'name': '{0}-retorno.xml'.format(name),
             'data': base64.encodestring(resposta['received_xml'])}
        ]}
        resp = resposta['object']
        if resp:
            if resp.Cabecalho.Sucesso:
                if "Alerta" in dir(resp):
                    status['success'] = True

                    mensagens = ['NFS-e emitida com sucesso.']
                    for alerta in resp.Alerta:
                        if alerta.Codigo == 224:
                            status['success'] = False
                        mensagens.append("%s - %s" % (alerta.Codigo,
                                                      alerta.Descricao))

                    if status['success']:
                        mensagens = ['NFS-e emitida com sucesso\n \
                                     Alertas:\n'] + mensagens
                    status['status'] = resp.Alerta[0].Codigo
                    status['message'] = u"\n".join(mensagens)
                else:
                    status['status'] = '100'
                    if name == 'envio_rps':
                        status['message'] = 'NFS-e emitida com sucesso'
                    elif name == 'cancelamento':
                        status['message'] = 'Cancelamento efetuado com sucesso'
                    else:
                        status['message'] = 'Consulta efetuada com sucesso'
                    status['success'] = resp.Cabecalho.Sucesso
            else:
                status['status'] = resp.Erro[0].Codigo
                status['message'] = resp.Erro[0].Descricao
                status['success'] = resp.Cabecalho.Sucesso
        else:
            status['status'] = -1
            status['message'] = resposta['received_xml']
            status['success'] = False

        return status

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
            status = self._create_status(resposta, 'envio_rps')
            if status['success'] and \
               self.invoice_id.company_id.nfse_environment == '1':
                status['verify_code'] = \
                    resposta['object'].ChaveNFeRPS.ChaveNFe.CodigoVerificacao
                status['nfse_number'] = \
                    resposta['object'].ChaveNFeRPS.ChaveNFe.NumeroNFe
            return status

        return super(BaseNfse, self).send_rps()

    @api.multi
    def cancel_nfse(self):
        if self.city_code == '50308':  # São Paulo
            pfx_stream = base64.b64decode(self.certificate)
            certificado = Certificado(pfx_stream, self.password)

            company = self.invoice_id.company_id
            canc = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
                'numero_nfse': self.invoice_id.internal_number,
                'codigo_verificacao': self.invoice_id.verify_code,
                'assinatura': '%s%s' % (
                    re.sub('[^0-9]', '', company.inscr_mun),
                    self.invoice_id.internal_number.zfill(12)
                )
            }
            resposta = cancelamento_nfe(certificado, cancelamento=canc)

            status = self._create_status(resposta, 'cancelamento')
            return status

        return super(BaseNfse, self).cancel_nfse()

    @api.multi
    def check_nfse_by_lote(self):
        if self.city_code == '50308':  # São Paulo
            pfx_stream = base64.b64decode(self.certificate)
            certificado = Certificado(pfx_stream, self.password)

            company = self.invoice_id.company_id
            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'lote': self.invoice_id.lote_nfse,
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun)
            }
            resposta = consulta_lote(certificado, consulta=consulta)

            status = self._create_status(resposta, 'consulta_lote')
            return status

        return super(BaseNfse, self).check_nfse_by_lote()

    @api.multi
    def print_pdf(self):
        if self.city_code == '50308':  # São Paulo IBGE Code
            return self.env['report'].get_action(
                self.invoice_id, 'nfse_sao_paulo.danfse_report')

    def _url_envio_nfse(self):
        if self.city_code == '50308':  # São Paulo
            return 'https://nfe.prefeitura.sp.gov.br/ws/lotenfe.asmx?wsdl'

    def _get_nfse_object(self):
        result = super(BaseNfse, self)._get_nfse_object()
        if self.invoice_id:
            inv = self.invoice_id

            result['lista_rps'][0]['codigo_atividade'] = \
                re.sub('[^0-9]', '',
                       inv.invoice_line[0].service_type_id.code or '')

            cnpj_cpf = result['lista_rps'][0]['tomador']['cpf_cnpj']
            data_envio = result['lista_rps'][0]['data_emissao']
            inscr = result['lista_rps'][0]['prestador']['inscricao_municipal']
            iss_retido = 'N'
            valor_servico = float(result['lista_rps'][0]['valor_servico'])
            valor_deducao = float(result['lista_rps'][0]['valor_deducao'])
            tipo_cpfcnpj = result['lista_rps'][0]['tomador']['tipo_cpfcnpj']
            codigo_atividade = result['lista_rps'][0]['codigo_atividade']
            tipo_recolhimento = inv.operation  # T – Tributado em São Paulo
            descricao_servicos = ''
            for line in inv.invoice_line:
                descricao_servicos += line.name + '\n'
            result['lista_rps'][0]['descricao'] = descricao_servicos

            assinatura = ('%s%s%s%s%sN%s%015d%015d%s%s%s') % (
                str(inscr).zfill(8),
                inv.document_serie_id.code.ljust(5),
                str(inv.internal_number).zfill(12),
                str(data_envio[0:4] + data_envio[5:7] + data_envio[8:10]),
                str(tipo_recolhimento),
                str(iss_retido),
                round(valor_servico*100),
                round(valor_deducao*100),
                str(codigo_atividade).zfill(5),
                str(tipo_cpfcnpj),
                str(cnpj_cpf).zfill(14)
                )
            result['lista_rps'][0]['assinatura'] = assinatura
            if result['lista_rps'][0]['tomador']['cidade'] != \
               result['lista_rps'][0]['prestador']['cidade']:
                del result['lista_rps'][0]['tomador']['inscricao_municipal']

        return result
