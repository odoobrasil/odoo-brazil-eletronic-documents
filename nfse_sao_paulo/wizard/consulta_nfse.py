# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import base64
from lxml import etree
from openerp import api, fields, models
from openerp.exceptions import Warning as UserError

from pytrustnfe.certificado import Certificado
from pytrustnfe.nfse.paulistana import consulta_nfe
from pytrustnfe.nfse.paulistana import consulta_lote
from pytrustnfe.nfse.paulistana import consulta_informacoes_lote
from pytrustnfe.nfse.paulistana import consulta_nfe_emitidas
from pytrustnfe.nfse.paulistana import consulta_nfe_recebidas


class NFSeRetornoConsulta(models.TransientModel):
    _name = 'nfse.consulta.retorno'

    name = fields.Char(string="Nome")
    xml_nfse = fields.Text(string="Xml")


class ConsultaNFSe(models.TransientModel):
    _name = 'nfse.consulta'
    _description = 'Consulta NFS-e'

    def _default_company(self):
        return 1
        return self.env.user.company_id.id

    company_id = fields.Many2one('res.company', string="Empresa")
    tipo_consulta = fields.Selection([('chave_rps', 'Por Chave RPS'),
                                      ('chave_nfse', 'Por Chave NFS-e'),
                                      ('emitidas', 'Emitidas'),
                                      ('recebidas', 'Recebidas'),
                                      ('lote', 'Por Lote')],
                                     string="Consultar notas",
                                     default="chave_rps")
    numero_nfse = fields.Char(string="Número NFS-e")
    codigo_verificacao = fields.Char(string="Código de Verificação")
    serie_rps = fields.Char(string="Série RPS")
    numero_rps = fields.Char(string="Número RPS")
    data_inicio = fields.Date(string="Data Inicio")
    data_fim = fields.Date(string="Data Fim")
    numero_paginas = fields.Integer(string="Número de Páginas", default=1)
    numero_lote = fields.Char(string="Lote")

    @api.multi
    def action_consultar_nfse(self):
        self.ensure_one()
        company = self.company_id
        if not company.nfe_a1_file:
            raise UserError('Atenção!', 'Certificado não configurado')
        if not company.nfe_a1_password:
            raise UserError('Atenção!', 'Senha do Certificado não configurado')
        if not company.cnpj_cpf:
            raise UserError('Atenção!', 'CNPJ da empresa não configurado')

        pfx_stream = base64.b64decode(company.nfe_a1_file)
        certificado = Certificado(pfx_stream, company.nfe_a1_password)

        if self.tipo_consulta == 'chave_rps':
            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
                'numero_rps': self.numero_rps,
                'serie_rps': self.serie_rps
            }
            result = consulta_nfe(certificado, consulta=consulta)
            if result['object'].Cabecalho.Sucesso:
                if "Alerta" in dir(result['object']):
                    message = "%s - %s" % (result['object'].Alerta.Codigo,
                                           result['object'].Alerta.Descricao)
                    raise UserError('Atenção', message)

                self.env['nfse.consulta.retorno'].create({
                    'name': str(result['object'].NFe.ChaveNFe.NumeroNFe),
                    'xml_nfse': etree.tostring(result['object'].NFe),
                })

            else:
                message = ""
                for erro in result['object'].Erro:
                    message += "%s - %s\n" % (erro.Codigo, erro.Descricao)
                raise UserError('Atenção', message)

        elif self.tipo_consulta == 'chave_nfse':
            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
                'numero_nfse': self.numero_nfse,
                'codigo_verificacao': self.codigo_verificacao
            }

            result = consulta_nfe(certificado, consulta=consulta)
            if result['object'].Cabecalho.Sucesso:
                if "Alerta" in dir(result['object']):
                    message = "%s - %s" % (result['object'].Alerta.Codigo,
                                           result['object'].Alerta.Descricao)
                    raise UserError('Atenção', message)

                self.env['nfse.consulta.retorno'].create({
                    'name': str(result['object'].NFe.ChaveNFe.NumeroNFe),
                    'xml_nfse': etree.tostring(result['object'].NFe),
                })

            else:
                message = ""
                for erro in result['object'].Erro:
                    message += "%s - %s\n" % (erro.Codigo, erro.Descricao)
                raise UserError('Atenção', message)

        elif self.tipo_consulta == 'emitidas':
            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'cnpj_cpf': re.sub('[^0-9]', '', company.cnpj_cpf),
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
                'data_inicio': self.data_inicio,
                'data_fim': self.data_fim,
                'numero_pagina': self.numero_paginas
            }
            result = consulta_nfe_emitidas(certificado, consulta=consulta)

            if result['object'].Cabecalho.Sucesso:
                if "Alerta" in dir(result['object']):
                    message = "%s - %s" % (result['object'].Alerta.Codigo,
                                           result['object'].Alerta.Descricao)
                    raise UserError('Atenção', message)

                message = ""
                for nfe in result['object'].NFe:
                    self.env['nfse.consulta.retorno'].create({
                        'name': str(nfe.ChaveNFe.NumeroNFe),
                        'xml_nfse': etree.tostring(nfe),
                    })

            else:
                message = ""
                for erro in result['object'].Erro:
                    message += "%s - %s\n" % (erro.Codigo, erro.Descricao)
                raise UserError('Atenção', message)

        elif self.tipo_consulta == 'recebidas':

            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'cnpj_cpf': re.sub('[^0-9]', '', company.cnpj_cpf),
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun),
                'data_inicio': self.data_inicio,
                'data_fim': self.data_fim,
                'numero_pagina': self.numero_paginas
            }
            result = consulta_nfe_recebidas(certificado, consulta=consulta)

            if result['object'].Cabecalho.Sucesso:
                if "Alerta" in dir(result['object']):
                    message = "%s - %s" % (result['object'].Alerta.Codigo,
                                           result['object'].Alerta.Descricao)
                    raise UserError('Atenção', message)

                message = ""
                if "NFe" in dir(result['object']):
                    for nfe in result['object'].NFe:
                        self.env['nfse.consulta.retorno'].create({
                            'name': str(nfe.ChaveNFe.NumeroNFe),
                            'xml_nfse': etree.tostring(nfe),
                        })
                else:
                    raise UserError('Atenção!', 'Nenhuma nota encontrada')

            else:
                message = ""
                for erro in result['object'].Erro:
                    message += "%s - %s\n" % (erro.Codigo, erro.Descricao)
                raise UserError('Atenção', message)

        elif self.tipo_consulta == 'lote':
            consulta = {
                'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                'lote': self.numero_lote,
                'inscricao_municipal': re.sub('[^0-9]', '', company.inscr_mun)
            }
            result = consulta_lote(certificado, consulta=consulta)
            # Apenas para teste - Remover futuramente
            consulta_informacoes_lote(certificado, consulta=consulta)
            if result['object'].Cabecalho.Sucesso:
                if "Alerta" in dir(result['object']):
                    message = "%s - %s" % (result['object'].Alerta.Codigo,
                                           result['object'].Alerta.Descricao)
                    raise UserError('Atenção', message)

                self.env['nfse.consulta.retorno'].create({
                    'name': str(result['object'].NFe.ChaveNFe.NumeroNFe),
                    'xml_nfse': etree.tostring(result['object'].NFe),
                })

            else:
                message = ""
                for erro in result['object'].Erro:
                    message += "%s - %s\n" % (erro.Codigo, erro.Descricao)
                raise UserError('Atenção', message)

        dummy, action_id = self.env['ir.model.data'].get_object_reference(
            'nfse_sao_paulo', 'action_nfse_sao_paulo_nfse_de_consulta')

        vals = self.env['ir.actions.act_window'].browse(action_id).read()[0]
        return vals
