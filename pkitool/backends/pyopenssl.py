# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## Copyright (C) 2006 Cleber Rosa <cleber@tallawa.org>
## All rights reserved
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
## USA.
##
## Author(s): Cleber Rosa <cleber@tallawa.org>
##
"""
pyopenssl.py

    
"""

import os
import OpenSSL

from pkitool.backends.base import Base
from pkitool.configparser import OpenSSLConfigParser

DEFAULT_ROOT_DIR = os.path.expanduser('~/pkitool-ca')

def mkdir_silent_if_isdir(path):
    '''
    Create a directory, bailing out silently if it already exists
    '''
    if os.path.isdir(path):
        return
    else:
        os.mkdir(path)

class OpenSSLEngine(Base):

    key_types = {'rsa' : OpenSSL.crypto.TYPE_RSA,
                 'dsa' : OpenSSL.crypto.TYPE_DSA}
    
    def __init__(self):
        Base.__init__(self)

    def init_database(self):
        self.config = OpenSSLConfigParser(DEFAULT_ROOT_DIR)
        
        mkdir_silent_if_isdir(self.config.get_ca_dir(self.ca))
        mkdir_silent_if_isdir(self.config.get_ca_certs(self.ca))
        mkdir_silent_if_isdir(self.config.get_ca_crl_dir(self.ca))

        ca_private_path = self.config.get_ca_private()
        mkdir_silent_if_isdir(ca_private_path)
        os.chmod(ca_private_path, 0700)
        
        # create empty database file
        open(self.config.get_ca_database(self.ca), 'w')

        mkdir_silent_if_isdir(self.config.get_ca_new_certs_dir(self.ca))

        # write '01' into serial
        serial_file = open(self.config.get_ca_serial(self.ca), 'w')
        serial_file.write('01\n')
        serial_file.close()
        
        # no need to do nothing about the other files and directories

    def create_private_key(self, path, type='rsa', size=1024, password=''):
        pkey = OpenSSL.crypto.PKey()
        pkey.generate_key(self.key_types[type], size)

        if password:
            buffer = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                    pkey,
                                                    'DES-EDE3-CBC',
                                                    password)
        else:
            buffer = OpenSSL.crypto.dump_privatekey(OpenSSL.crypto.FILETYPE_PEM,
                                                    pkey)
        fp = open(path, 'w')
        fp.write(buffer)
        
        
