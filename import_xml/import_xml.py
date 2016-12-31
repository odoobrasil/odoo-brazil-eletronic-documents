# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Carlos Silveira.
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
import re
from openerp import models, fields, api, _
#from openerp.osv import fields, osv
import base64
from openerp.tools.translate import _
from xml.dom import minidom
from datetime import datetime, date
from cStringIO import StringIO
import time
import tempfile
import pdb

_TASK_STATE = [('open', 'Novo'),('done', 'Importado'), ('cancelled', 'Cancelado')]


class import_xml(models.Model):

    _name = 'import.xml'

    name = fields.Char('Descrição', size=256, required=True)
    input_file = fields.Binary('Arquivo', required=False)
    user_id = fields.Many2one('res.users', 'Inserido por', track_visibility='onchange')
    location_id = fields.Many2one('stock.location', 'Destination', required=True, domain=[('usage','<>','view')])
    company_id = fields.Many2one('res.company', 'Company', required=True, select=1, states={'confirmed': [('readonly', True)], 'approved': [('readonly', True)]})
    categ_id = fields.Many2one('product.category','Internal Category', required=True, change_default=True, domain="[('type','=','normal')]" ,help="S     elect category for the current product")
    pos_categ_id = fields.Many2one('pos.category','Point of Sale Category', help="Those categories are used to group similar products for point of s     ale.")
    state = fields.Selection(_TASK_STATE, 'Situacao', required=True)


    _defaults = {
        'state': 'open',
        'user_id': lambda obj, cr, uid, context: uid,
    }

    def set_done(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'done'}, context=context)

    def set_open(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'open'}, context=context)

    def set_cancelled(self, cr, uid, ids, context=None):
        return self.write(cr, uid, ids, {'state':'cancelled'}, context=context)

    def get_order(self, cr, uid, vals, context=None):
        order_obj = self.pool.get('purchase.order')
        
        order_id = None
        if vals.get('partner_ref'):
            order_id = order_obj.search(cr, uid, [('partner_ref', '=', vals.get('partner_ref')),('partner_id','=', vals.get('partner_id'))], limit=1)

        if not order_id:
            order_id =  order_obj.create(cr, uid, vals, context=context)
        else:    
            raise Warning(_(u'Nota já importada! Já existe esta NF para este fornecedor.'))
        return order_id

    def get_order_line(self, cr, uid, vals, context=None):
        order_line_obj = self.pool.get('purchase.order.line')
        
        #order_line_id = None
        if vals.get('order_id'):
            order_line_id = order_line_obj.search(cr, uid, [('order_id', '=', vals.get('order_id')),('product_id','=', vals.get('product_id'))], limit=1)

        if not order_line_id:
            order_line_id =  order_line_obj.create(cr, uid, vals, context=context)
        return order_line_id

    def get_supplier(self, cr, uid, vals, context=None):
        #pdb.set_trace()
        cnpj_cpf = vals.get('cnpj_cpf')
        if cnpj_cpf:
            val = re.sub('[^0-9]', '', cnpj_cpf)
            #if is_company and len(val) == 14:
            cnpj_cpf = "%s.%s.%s/%s-%s"\
            % (val[0:2], val[2:5], val[5:8], val[8:12], val[12:14])
            vals['cnpj_cpf'] = cnpj_cpf
            #elif not is_company and len(val) == 11:
            #    cnpj_cpf = "%s.%s.%s-%s"\
            #    % (val[0:3], val[3:6], val[6:9], val[9:11])
            #vals['cnpj_cpf'] = cnpj_cpf
        supplier_obj = self.pool.get('res.partner')
        #supplier_id = None
        #procura pelo cnpj
        if cnpj_cpf:
            supplier_id = supplier_obj.search(cr, uid, [('cnpj_cpf', '=', cnpj_cpf), ('supplier','=',True)], limit=1)
        if not supplier_id:
            if vals.get('name'):
                supplier_id = supplier_obj.search(cr, uid, [('name', '=', vals.get('name')), ('supplier','=',True)], context=context)
        #se nao existir cadastra
        if supplier_id:
            supplier_id = supplier_id[0]
        else:
            country_obj = self.pool.get('res.country')
            country_id = country_obj.search(cr, uid, [('ibge_code', '=', vals.get('country_id'))])
            if country_id:
                vals['country_id'] = country_id[0]                                
            else:
                raise Warning(_(u'País não localizado! Verifique se o país possui o cód. do IBGE.'))
            city_obj = self.pool.get('l10n_br_base.city')
            ibge_code = vals.get('l10n_br_city_id')[2:]

            city_id = city_obj.search(cr, uid, [('ibge_code', '=', ibge_code)])
            for city in city_obj.browse(cr, uid, city_id, context=context):
                vals['l10n_br_city_id'] = city.id                                
                vals['state_id'] = city.state_id.id                                
            supplier_id =  supplier_obj.create(cr, uid, vals, context=context)
            #self.pool.get('res.partner').write(cr,uid,ids,{'street2':street},context=context)
        return supplier_id
    
    def get_product(self, cr, uid, vals, context=None):
        prodt_obj = self.pool.get('product.template')
        prod_obj = self.pool.get('product.product')
                
        # procura pelo codBarra
        prod_id = None
        if vals.get('ean13'):
            prod_id = prod_obj.search(cr, uid, [('ean13', '=', vals.get('ean13'))], limit=1)
        # procura pelo codProduto
        if not prod_id:
            if vals.get('default_code'):
                prod_id = prod_obj.search(cr, uid, [('default_code', '=', vals.get('default_code')[0])], limit=1)
        # procura pelo nome
        if not prod_id:
            if vals.get('name'):
                prod_id = prod_obj.search(cr, uid, [('name', '=', vals.get('name'))], limit=1)
        if prod_id:
            prod_id = prod_id[0]
        else:    
            vals_p = {'name': vals.get('name'),
                'type': 'product',
                'company_id': None,
                'cost_method': 'average',
                'valuation': 'real_time',
                'categ_id': vals.get('categ_id'),
                'pos_categ_id': vals.get('pos_categ_id'),
            }
            #pdb.set_trace()
            if vals.get('categ_id'):
                categ_obj = self.pool.get('product.category')
                for categ in categ_obj.browse(cr, uid, vals.get('categ_id'), context=context):
                    vals_p['property_account_income'] = categ.property_account_income_categ.id
                    vals_p['property_account_expense'] = categ.property_account_expense_categ.id
                    vals_p['property_stock_account_input'] = categ.property_stock_account_input_categ.id
                    vals_p['property_stock_account_output'] = categ.property_stock_account_output_categ.id



            prodt_id =  prodt_obj.create(cr, uid, vals_p, context=None)
            vals_pp = {'default_code': vals.get('default_code')[0],
                      'product_tmpl_id': prodt_id,
            }
            prod_id =  prod_obj.create(cr, uid, vals_pp, context=None)
        # se nao existir cadastra
        return prod_id

    def import_to_db(self, cr, uid, ids, context={}):

        user_obj = self.pool.get('res.users')
        company_id = user_obj.browse(cr, uid, uid, context=context).company_id.id
        type_obj = self.pool.get('stock.picking.type')
        types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)], context=context)
        if not types:
            types = type_obj.search(cr, uid, [('code', '=', 'incoming'), ('warehouse_id', '=', False)], context=context)
            if not types:
                raise Warning(_('Error! Make sure you have at least an incoming picking type defined'))

        nfe = str(uid)
        context['result_ids'] = []
        #result_pool = self.pool.get('ea_import.chain.result')
        for chain in self.browse(cr, uid, ids, context=context):
            file_path = tempfile.gettempdir()+'/file.xml'
            data = chain.input_file
            f = open(file_path,'wb')
            f.write(data.decode('base64'))
            f.close()

            xmldoc = minidom.parse(file_path)
            NFe = xmldoc.getElementsByTagName("NFe")[0]
            infNFe = NFe.getElementsByTagName("infNFe")[0]

            ide = infNFe.getElementsByTagName("ide")[0]
            nNF = ide.getElementsByTagName("nNF")[0].firstChild.data
            if ide.getElementsByTagName("dhEmi"):
                dEmi = ide.getElementsByTagName("dhEmi")[0].firstChild.data
            if ide.getElementsByTagName("dEmi"):
                dEmi = ide.getElementsByTagName("dEmi")[0].firstChild.data
            serie = ide.getElementsByTagName("serie")[0].firstChild.data

            dest = infNFe.getElementsByTagName("dest")[0]
            cnpjDest = dest.getElementsByTagName("CNPJ")[0].firstChild.data

            emit = infNFe.getElementsByTagName("emit")[0]
            cnpj = emit.getElementsByTagName("CNPJ")[0].firstChild.data
            supplier = emit.getElementsByTagName("xNome")[0].firstChild.data
            if emit.getElementsByTagName("xFant"):
                fantasia = emit.getElementsByTagName("xFant")[0].firstChild.data
            else:
                fantasia = supplier 
            ie = emit.getElementsByTagName("IE")[0].firstChild.data

            enderEmit = infNFe.getElementsByTagName("enderEmit")[0]
            enderEmit = infNFe.getElementsByTagName("enderEmit")[0]
            street = enderEmit.getElementsByTagName("xLgr")[0].firstChild.data
            nro = enderEmit.getElementsByTagName("nro")[0].firstChild.data
            district = enderEmit.getElementsByTagName("xBairro")[0].firstChild.data
            city = enderEmit.getElementsByTagName("cMun")[0].firstChild.data
            state = enderEmit.getElementsByTagName("UF")[0].firstChild.data
            zip = enderEmit.getElementsByTagName("CEP")[0].firstChild.data
            if enderEmit.getElementsByTagName("cPais"):
                country = enderEmit.getElementsByTagName("cPais")[0].firstChild.data
            else:
                country = 1058
            phone = enderEmit.getElementsByTagName("fone")[0].firstChild.data
            print 'NF :' + nNF
            print 'Fornecedor :' + supplier + '-' + fantasia + '-' + cnpj + '-' + ie
            print 'Endereco :' + street + '-' + nro + '-' + city + '-' + state
            vals_supplier = {'name': fantasia,
                             'legal_name': supplier,
                             'street': street,
                             'number': nro,
                             'district': district,
                             'l10n_br_city_id': city,
                             'state_id': state,
                             'zip': zip,
                             'country_id': country,
                             'phone': phone,
                             'cnpj_cpf': cnpj,
                             'supplier': True,
                             'is_company': True,
            }
            if enderEmit.getElementsByTagName("xCpl"):
                street2 = enderEmit.getElementsByTagName("xCpl")[0].firstChild.data
                vals_supplier['street2'] = street2
            supplier_id = self.get_supplier(cr, uid, vals_supplier, None)

            vals_order = {'partner_ref': nNF,
                          'partner_id' : supplier_id,
                          'date_order' : dEmi,
                          'company_id' : chain.company_id.id,
                          'location_id' : chain.location_id.id,
            }

            partner = self.pool.get('res.partner')
            supplier = partner.browse(cr, uid, supplier_id, context=context)
            if supplier.property_product_pricelist_purchase:
                vals_order['pricelist_id'] = supplier.property_product_pricelist_purchase.id
            if supplier.property_account_position:
                vals_order['fiscal_position'] = supplier.property_account_position.id
            if supplier.property_supplier_payment_term:
                vals_order['payment_term_id'] = supplier.property_supplier_payment_term.id
            order_id = self.get_order(cr, uid, vals_order, None)

            nfeProc = xmldoc.getElementsByTagName("nfeProc")[0]

            chNFe = nfeProc.getElementsByTagName("chNFe")[0].firstChild.data

            itemlist = xmldoc.getElementsByTagName("det")
            for itens in itemlist:
                print "*****itens*****"
                #if itens.hasAttribute("xProd"):
                codProd = itens.getElementsByTagName("cProd")[0]
                produto = itens.getElementsByTagName("xProd")[0]
                ncm = itens.getElementsByTagName("NCM")[0]
                ean = itens.getElementsByTagName("cEAN")[0]
                un = itens.getElementsByTagName("uCom")[0]
                qtde = itens.getElementsByTagName("qCom")[0]
                vlr = itens.getElementsByTagName("vUnCom")[0]
                print "Prod. : %s-%s-%s-%s %s %s " % (produto.firstChild.data, codProd.firstChild.data,ncm.firstChild.data, un.firstChild.data, qtde.firstChild.data, vlr.firstChild.data)
                vals_prod = {'name': produto.firstChild.data,
                             'type': 'product',
                             'company_id': None,
                             'categ_id': chain.categ_id.id,
                             'pos_categ_id': chain.pos_categ_id.id,
                }
                if ean.firstChild:
                    vals_prod['ean13'] = ean.firstChild.data
                vals_prod['default_code'] = str(codProd.firstChild.data),
                prod_id = self.get_product(cr, uid, vals_prod, None)
                vals_order_line = {'order_id': order_id,
                                   'product_id' : prod_id,
                                   'product_qty' : qtde.firstChild.data,
                                   'price_unit' : vlr.firstChild.data,
                                   'name' : produto.firstChild.data,
                                   'date_planned' : dEmi,
                }
                order_line_id = self.get_order_line(cr, uid, vals_order_line, None)


        return self.write(cr, uid, ids, {'state':'done'}, context=context)

import_xml()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
