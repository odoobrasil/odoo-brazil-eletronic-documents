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

import base64
import requests
import suds.client
import suds_requests
from uuid import uuid4
from lxml import etree
from ..service.nota_servico import NotaServico
from ..service.certificate import converte_pfx_pem
from openerp import api, fields, models



class BaseNfse(models.Model):
    _name = 'base.nfse'
    
    def _company_certificate(self):
        for item in self:
            item.certificate = self.env.user.company_id.nfe_a1_file

    city_code = fields.Char(u'Código Cidade', size=100)
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

    def _get_nfse_object(self):
        """
        Sobrescrever este método para adicionar novos itens ao gerar o xml.
        Returns:
            dict: retorna um dicionário com os dados da nfse
         """
        return None     
      

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