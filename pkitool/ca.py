# -*- Mode: Python; coding: iso-8859-1 -*-
# vi:si:et:sw=4:sts=4:ts=4

##
## PKI
## Copyright (C) 2006  Global Red <www.globalred.com.br>
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
## Author(s): Cleber Rodrigues <cleber@globalred.com.br>
##
"""
ca.py

    
"""

__all__ = ['CertificateAuthority']

import os
import sys
import optparse

def mkdir_silent_if_isdir(path):
    if os.path.isdir(path):
        return
    else:
        os.mkdir(path)

class UnknownCallbackException(Exception):
    '''
    A not previously defined and known callback name
    '''
    def __init__(self, name):
        Exception.__init__(self,
                           'Callback %s is not a known callback' % name)

class CertificateAuthority:
    '''
    This represents a instance of a CA

    You can specify the ca name from the config file. Or else,
    the default ca is used.
    '''

    allowed_callback_names = (\
        # should return a text string
        'get_ca_key_password',

        # should return a text string
        'get_cert_key_psasword',

        # should return a dict
        'get_req_distinguished_name'
        )

    def __init__(self, config, ca=''):
        self.config = config
        if not ca:
            ca = config.get_default_ca()
        self.ca = ca

        try:
            from backends.pyopenssl import OpenSSLEngine
        except ImportError:
            from backends.openssl import OpenSSLEngine

        self.engine = OpenSSLEngine()


        # callbacks should only be accessed by register_callback_methods*
        # the reason is only to catch some bugs and make things more
        # consistent project-wise
        self.__callbacks = { }


    def register_callback(self, name, function, *args, **kwargs):
        '''
        Registers a function to be called at a specific event
        '''
        if name not in CertificateAuthority.allowed_callback_names:
            raise UnknownCallbackException, name

        if not self.__callbacks.has_key(name):
            self.__callbacks[name] = (function, args, kwargs)

    def unregister_callback(self, name, function):
        '''
        Unregister a previously registered 

        Known liimtations:

        1) only one instance of a given function should
        be registered at a given time for a given event. That is because
        unregister index by name and function, and removes all instances.

        2) is very quiet, complains about nothing
        '''
        if self.__callbacks.has_key(name):
            self.__callbacks[name] = [i for i in self.__callbacks[name] \
                                      if not i[0] == function]


    def create_directory_structure(self):
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

    def create_ca_key(self, size=1024):
        '''
        Creates the Certificate Authority keypair

        openssl genresa does not look into a config file.So, we have to put
        it into the *right* place, which is defined in the private_key option
        of the chosen CA section.
        '''

        if self.__callbacks.has_key('get_ca_key_password'):
            func, args, kwargs = self.__callbacks['get_ca_key_password']
            pwd = func(*args, **kwargs)
        else:
            pwd = ''

        if pwd:
            self.engine.create_private_key(self.config.get_ca_private_key(self.ca),
                                           size=size,
                                           password=pwd)
        else:
            self.engine.create_private_key(self.config.get_ca_private_key(self.ca),
                                           size=size)

    def init(self):
        # First, dump the config file in memory somewhere

        self.dumped_config_path = os.path.join(self.config.get_ca_dir(self.ca),
                                               'openssl.cnf')
        self.config.write(open(self.dumped_config_path, 'w'))

        self.create_ca_key()


if __name__ == '__main__':
    from configparser import OpenSSLConfigParser

    config = OpenSSLConfigParser()
    config.create_default_config()

    ca = CertificateAuthority(config)
    ca.create_directory_structure()

    config_file_path = os.path.join(config.get_default_ca_dir(),
                                    'openssl.cnf')

    print config_file_path
