# -*- coding: utf-8 -*-
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

import os.path
from lxml import etree
from jinja2 import Environment, FileSystemLoader
from . import filters_xml as filters


def render(base_path, template_path, **kwargs):    
    env = Environment(loader=FileSystemLoader(os.path.join(base_path, 'templates')))
    
    env.filters["normalize"] = filters.normalize_str
    env.filters["format_percent"] = filters.format_percent
    env.filters["format_datetime"] = filters.format_datetime
    env.filters["format_date"] = filters.format_date
    
    template = env.get_template(template_path)

    # TODO Remover espaços e possíveis tags vazias
    xml = template.render(**kwargs)    
    parser = etree.XMLParser(remove_blank_text=True, remove_comments=True)
    elem = etree.fromstring(xml, parser=parser)
    return etree.tostring(elem)
