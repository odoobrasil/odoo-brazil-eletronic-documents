# -*- coding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2015 Trustcode - www.trustcode.com.br                         #
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

from decimal import Decimal
from datetime import datetime
import dateutil.parser as parser_dateutil

from unicodedata import normalize

def normalize_str(string):
    """
    Remove special characters and return the ascii string
    """
    if string:
        if not isinstance(string, unicode):
            string = unicode(string, 'utf-8', 'replace')

        string = string.encode('utf-8')
        return normalize('NFKD', string.decode('utf-8')).encode('ASCII','ignore')
    return ''

def format_percent(value):
    if value:
        return Decimal(value) / 100

def format_datetime(value):
    """
    Format datetime
    """
    dt_format = '%Y-%m-%dT%H:%M:%I'
    if isinstance(value, datetime):
        return value.strftime(dt_format)

    try:
        value = parser_dateutil.parse(value).strftime(dt_format)
    except AttributeError:
        pass

    return value

def format_date(value):
    """
    Format date
    """
    dt_format = '%Y-%m-%d'
    if isinstance(value, datetime):
        return value.strftime(dt_format)
    
    try:
        value = parser_dateutil.parse(value).strftime(dt_format)
    except AttributeError:
        pass

    return value