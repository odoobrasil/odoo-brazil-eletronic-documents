# coding: utf-8
# ###########################################################################
#
#    Author: Luis Felipe Mileo
#            Fernando Marcato Rodrigues
#            Daniel Sadamo Hirayama
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
from openerp.osv import orm, fields
from openerp.tools.translate import _
from openerp.addons.nfe.sped.nfe.nfe_factory import NfeFactory
from openerp.exceptions import Warning

import os

_logger = logging.getLogger(__name__)


class NfeImportAccountInvoiceImport(orm.TransientModel):
    """
        Assistente de importaçao de txt e xml
    """
    _name = 'nfe_import.account_invoice_import'
    _description = 'Import Eletronic Document in TXT and XML format'

    _columns = {
        'edoc_input': fields.binary(u'Arquivo do documento eletrônico',
                                   help=u'Somente arquivos no formato TXT e '
                                        u'XML'),
        'file_name': fields.char('File Name', size=128),
        'state': fields.selection([('init', 'init'),
                                   ('done', 'done')], 'state', readonly=True),
    }

    _defaults = {
        'state': 'init',
    }

    def _check_extension(self, filename):
        (__, ftype) = os.path.splitext(filename)
        if ftype.lower() not in ('.txt', '.xml'):
            raise Warning(_('Please use a file in extensions TXT or XML'))
        return ftype


    def _get_nfe_factory(self, nfe_version):
        return NfeFactory().get_nfe(nfe_version)

    def import_edoc(self, cr, uid, req_id, context=False):
        """
        :param cr:
        :param uid:
        :param ids:
        :param context:
        :return:
        """
        try:
            context = context or {}
    
            if isinstance(req_id, list):
                req_id = req_id[0]
    
            importer = self.browse(cr, uid, req_id, context)
            ftype = self._check_extension(importer.file_name)
    
            user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
            edoc_obj = self._get_nfe_factory(user.company_id.nfe_version)
    
            # TODO: Tratar mais de um documento por vez.
            edoc = edoc_obj.import_edoc(cr, uid, importer.edoc_input,
                                                ftype, context)[0]
    
            model_obj = self.pool.get('ir.model.data')
            action_obj = self.pool.get('ir.actions.act_window')
            action_id = model_obj.get_object_reference(
                cr, uid, edoc['action'][0], edoc['action'][1])[1]
            res = action_obj.read(cr, uid, action_id)
            res['domain'] = res['domain'][:-1] + ",('id', 'in', %s)]" % [edoc['id']]
            return res
        except Exception as e:
            _logger.error(unicode(str(e), 'utf-8'), exc_info=True)
            raise Warning('Erro ao tentar importar o xml\nMensagem de erro:\n{0}'.format(e.message))
            

    def done(self, cr, uid, ids, context=False):
        return True
