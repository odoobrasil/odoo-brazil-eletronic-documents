# -*- encoding: utf-8 -*-
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
#                                                                             #
###############################################################################

import os.path
import base64
from openerp import models, api, fields
from openerp.exceptions import Warning
from pysped.nfe.danfe import DANFE
from pysped.nfe.leiaute import ProcNFe_310


class Nfe_Mde(models.Model):
    _inherit = 'nfe.mde'

    xml_downloaded = fields.Boolean(u'Xml já baixado?', default=False)
    xml_imported = fields.Boolean(u'Xml já importado?', default=False)

    @api.one
    def action_download_xml(self):
        if not self.xml_downloaded:
            value = super(Nfe_Mde, self).action_download_xml()
            if value:
                self.write({'xml_downloaded': True})
        return True

    @api.multi
    def action_import_xml(self):
        self.ensure_one()
        if os.path.isfile(self.file_path):
            arq = open(self.file_path, 'r')
            filename = arq.name
            content = arq.read().decode('utf-8')
            arq.close()
            content = base64.b64encode(content)

            import_doc = {'edoc_input': content, 'file_name': filename}
            nfe_import = self.env[
                'nfe_import.account_invoice_import'].create(import_doc)

            action_name = 'action_l10n_br_account_periodic_processing_edoc_import'
            model_obj = self.pool.get('ir.model.data')
            action_obj = self.pool.get('ir.actions.act_window')
            action_id = model_obj.get_object_reference(
                self._cr, self._uid, 'nfe_import', action_name)
            res = action_obj.read(self._cr, self._uid, action_id[1])
            res['domain'] = "[('id', 'in', %s)]" % [nfe_import.id]
            res['res_id'] = nfe_import.id
            return res

        else:
            raise Warning(u'O arquivo xml já não existe mais no caminho especificado\n'
                          u'Contate o responsável pelo sistema')
    
    @api.multi    
    def action_visualizar_danfe(self):
        raise Warning(u'Não implementado ainda! Desculpe!')
        self.ensure_one()
        if os.path.isfile(self.file_path):
            arq = open(self.file_path, 'r')            
            content = arq.read().decode('utf-8')
            arq.close()     

            
            #TODO Finalizar DANFE, talvez reutilizar o código do NF-e,
            # porém precisa refatorar aquele código
            procnfe = ProcNFe_310()
            procnfe.xml = content
            danfe = DANFE()
            danfe.NFe = procnfe.NFe
            danfe.protNFe = procnfe.protNFe
            danfe.caminho = "/tmp/"
            danfe.gerar_danfe()
            
            
        else:
            raise Warning(u'O arquivo xml já não existe mais no caminho especificado\n'
                          u'Contate o responsável pelo sistema')
        
        
        
        
