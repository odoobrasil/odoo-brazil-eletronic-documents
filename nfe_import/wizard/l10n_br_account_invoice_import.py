# coding=utf-8
# ###########################################################################
#
#    Author: Luis Felipe Mileo
#            Fernando Marcato Rodrigues
#            Daniel Sadamo Hirayama
#            Danimar Ribeiro <danimaribeiro@gmail.com>
#    Copyright 2015 KMEE - www.kmee.com.br
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from openerp import models, fields, api
from openerp.tools.translate import _
from openerp.addons.nfe.sped.nfe.nfe_factory import NfeFactory
from openerp.exceptions import Warning

import os


_logger = logging.getLogger(__name__)


class NfeImportAccountInvoiceImport(models.TransientModel):
    """
        Assistente de importaçao de txt e xml
    """
    _name = 'nfe_import.account_invoice_import'
    _description = 'Import Eletronic Document in TXT and XML format'

    edoc_input = fields.Binary(u'Arquivo do documento eletrônico',
                               help=u'Somente arquivos no formato TXT e XML')
    file_name = fields.Char('File Name', size=128)
    create_partner = fields.Boolean(
        u'Criar fornecedor automaticamente?', default=True,
        help=u'Cria o fornecedor automaticamente caso não esteja cadastrado')
    state = fields.Selection([('init', 'init'), ('done', 'done')],
                             string='state', readonly=True, default='init')

    def _check_extension(self, filename):
        (__, ftype) = os.path.splitext(filename)
        if ftype.lower() not in ('.txt', '.xml'):
            raise Warning(_('Please use a file in extensions TXT or XML'))
        return ftype

    def _get_nfe_factory(self, nfe_version):
        return NfeFactory().get_nfe(nfe_version)

    @api.multi
    def import_edoc(self, req_id, context=False):
        try:
            self.ensure_one()
            importer = self[0]

            ftype = self._check_extension(importer.file_name)

            edoc_obj = self._get_nfe_factory(
                self.env.user.company_id.nfe_version)

            # TODO: Tratar mais de um documento por vez.
            eDoc = edoc_obj.import_edoc(
                self._cr, self._uid, importer.edoc_input, ftype, context)[0]

            inv_values = eDoc['values']
            if importer.create_partner and inv_values['partner_id'] == False:
                partner = self.env['res.partner'].create(
                    inv_values['partner_values'])
                inv_values['partner_id'] = partner.id
            elif inv_values['partner_id'] == False:
                raise Exception(
                    u'Fornecedor não cadastrado, o xml não será importado\n'
                    u'Marque a opção "Criar fornecedor" se deseja importar '
                    u'mesmo assim')

            invoice = self.env['account.invoice'].create(inv_values)
            self.attach_doc_to_invoice(invoice.id, importer.edoc_input,
                                       importer.file_name)

            model_obj = self.pool.get('ir.model.data')
            action_obj = self.pool.get('ir.actions.act_window')
            action_id = model_obj.get_object_reference(
                self._cr, self._uid, eDoc['action'][0], eDoc['action'][1])[1]
            res = action_obj.read(self._cr, self._uid, action_id)
            res['domain'] = res['domain'][:-1] + \
                ",('id', 'in', %s)]" % [invoice.id]
            return res
        except Exception as e:
            if isinstance(e.message, unicode):
                _logger.error(e.message, exc_info=True)
            elif isinstance(e.message, str):
                _logger.error(e.message.decode('utf-8','ignore'), exc_info=True)
            else:
                _logger.error(str(e), exc_info=True)
            raise Warning(
                u'Erro ao tentar importar o xml\n'
                u'Mensagem de erro:\n{0}'.format(
                    e.message))

    def attach_doc_to_invoice(self, invoice_id, doc, file_name):
        obj_attachment = self.env['ir.attachment']

        attachment_id = obj_attachment.create({
            'name': file_name,
            'datas': doc,
            'description': _('No Description'),
            'res_model': 'account.invoice',
            'res_id': invoice_id
        })
        return attachment_id

    @api.multi
    def done(self, cr, uid, ids, context=False):
        return True
