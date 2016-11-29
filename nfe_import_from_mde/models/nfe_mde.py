# coding: utf-8
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

from openerp import models, api, fields
from openerp.exceptions import Warning as UserError


class NfeMde(models.Model):
    _inherit = 'nfe.mde'

    xml_downloaded = fields.Boolean(u'Xml já baixado?', default=False)
    xml_imported = fields.Boolean(u'Xml já importado?', default=False)

    @api.multi
    def action_download_xml(self):
        for record in self:
            if not record.xml_downloaded:
                value = super(NfeMde, record).action_download_xml()
                if value:
                    record.write({'xml_downloaded': True})
        return True

    @api.multi
    def action_import_xml(self):
        self.ensure_one()
        attach_xml = self.env['ir.attachment'].search([
            ('res_id', '=', self.id),
            ('res_model', '=', 'nfe.mde'),
            ('name', '=like', 'NFe%')
        ], limit=1)

        if attach_xml:
            import_doc = {'edoc_input': attach_xml.datas,
                          'file_name': attach_xml.datas_fname}
            nfe_import = self.env[
                'nfe_import.account_invoice_import'].create(import_doc)

            action_name = \
                'action_l10n_br_account_periodic_processing_edoc_import'
            model_obj = self.pool.get('ir.model.data')
            action_obj = self.pool.get('ir.actions.act_window')
            action_id = model_obj.get_object_reference(
                self._cr, self._uid, 'nfe_import', action_name)
            res = action_obj.read(self._cr, self._uid, action_id[1])
            res['domain'] = "[('id', 'in', %s)]" % [nfe_import.id]
            res['res_id'] = nfe_import.id
            return res

        else:
            raise UserError(
                u'O arquivo xml já não existe mais no caminho especificado\n'
                u'Contate o responsável pelo sistema')

    @api.multi
    def action_visualizar_danfe(self):
        return self.env['report'].get_action(self, 'danfe_nfe_mde',
                                             data={'ids': self.ids,
                                                   'model': 'nfe.mde'})
