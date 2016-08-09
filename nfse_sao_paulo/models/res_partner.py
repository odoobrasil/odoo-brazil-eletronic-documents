# -*- coding: utf-8 -*-
# © 2016 Danimar Ribeiro, Trustcode
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import re
import base64
from pytrustnfe.certificado import Certificado
from pytrustnfe.nfse.paulistana import consulta_cnpj

from openerp import api, fields, models
from openerp.exceptions import Warning as UserError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.multi
    def consulta_cnpj_prefeitura(self):
        self.ensure_one()
        company = self.company_id or self.env.user.company_id
        if not company.nfe_a1_file:
            raise UserError('Atenção!', 'Certificado não configurado')
        if not company.nfe_a1_password:
            raise UserError('Atenção!', 'Senha do Certificado não configurado')
        if not company.cnpj_cpf:
            raise UserError('Atenção!', 'CNPJ da empresa não configurado')
        if not self.cnpj_cpf:
            raise UserError('Atenção!', 'CNPJ do cliente não preenchido')

        pfx_stream = base64.b64decode(company.nfe_a1_file)
        certificado = Certificado(pfx_stream, company.nfe_a1_password)
        consulta = {'cnpj_remetente': re.sub('[^0-9]', '', company.cnpj_cpf),
                    'cnpj_contribuinte': re.sub('[^0-9]', '', self.cnpj_cpf)}
        result = consulta_cnpj(certificado, consulta=consulta)
        if result['object'].Cabecalho.Sucesso:
            if "Alerta" in dir(result['object']):
                message = "%s - %s" % (result['object'].Alerta.Codigo,
                                       result['object'].Alerta.Descricao)
                raise UserError('Atenção', message)

            message = u"Emitente com inscrição: %s\nEmite NFe: %s" % (
                result['object'].Detalhe.InscricaoMunicipal,
                u'Sim' if result['object'].Detalhe.EmiteNFe else u'Não')
            raise UserError('Resultado da Consulta', message)
        else:
            message = "%s - %s" % (result['object'].Erro.Codigo,
                                   result['object'].Erro.Descricao)
            raise UserError('Atenção', message)
