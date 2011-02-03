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
configparser.py

    
"""

__all__ = ['OpenSSLConfigParser']

import os
import sys
import re

from ConfigParser import RawConfigParser, DEFAULTSECT, \
     NoSectionError, NoOptionError

class OpenSSLRawConfigParser(RawConfigParser):

    COMMENTCRE = re.compile(
        r'\s*#.*'
        )

    OPTCRE = re.compile(
        r'(?P<option>[^:=\s][^:=]*)'
        r'([:=])'
        r'(?P<value>[^#]*)'
        )

    def __init__(self, defaults=None):
        RawConfigParser.__init__(self, defaults)

        # Protect global_options (may be temporary)
        self.__global_options = {}

        # OpenSLL by default uses spaces in section names, so that the
        # ca section would be represented as [ ca ] in the config file
        self.__spaces_in_section_names = True



    def optionxform(self, optionstr):
        '''
        Somehow transform the option string
        
        This differs from ConfigParser.RawConfigParser.get(). We do *nothing*
        with the option string.
        '''
        return optionstr

    def parse_value(self, section, value):
        '''
        Parse a openssl configuration variable

        This is a very simplistic (lame?) implementation, that only deals
        with the very simple cases found in the stock openssl config file.
        '''
        if value.startswith('$'):
            slash_pos = value.find('/')
            if  slash_pos > 0:
                var_to_parse = value[1:slash_pos]
                if var_to_parse.startswith('ENV::'):
                    environ_var_name = var_to_parse[5:]
                    environ_var_value = os.environ[environ_var_name]

                    len_environ_var_name = len(environ_var_name)

                    return environ_var_value + value[6+len_environ_var_name:]
                else:
                    var_value = self.get(section, var_to_parse, False)
                    len_var_name = len(var_to_parse)

                    return var_value + value[1+len_var_name:]
        else:
            return value

    def get(self, section, option, parse=True):
        '''
        Retrieve a option value
        
        Works just as ConfigParser.RawConfigParser.get(), but extends in these
        manners:

        1) if section is '', it treats option as global
        2) if parse is False, it returns the value just as it is in the config
           file, with no parsing.
        '''
        opt = self.optionxform(option)

        if not section:
            if opt in self.__global_options:
                value = self.__global_options[opt]
                if not parse:
                    return value
                else:
                    return self.parse_value(section, value)
            else:
                raise NoOptionError(option, 'global')

        elif section not in self._sections:
            if section != DEFAULTSECT:
                raise NoSectionError(section)
            if opt in self._defaults:
                if not parse:
                    return self._defaults[opt]
                else:
                    return self.parse_value(section, self._defaults[option])
            else:
                raise NoOptionError(option, section)
            
        elif opt in self._sections[section]:
            if not parse:
                return self._sections[section][opt]
            else:
                return self.parse_value(section, self._sections[section][opt])
        
        elif opt in self._defaults:
            return self._defaults[opt]
        else:
            raise NoOptionError(option, section)


    def set(self, section, option, value):
        '''
        Sets an option value

        Works just as ConfigParser.RawConfigParser.set(), but extends in this
        manner: if section is '', it treats option as global.
        '''
        if not section:            sectdict = self.__global_options
        elif section == DEFAULTSECT:
            sectdict = self._defaults
        else:
            try:
                sectdict = self._sections[section]
            except KeyError:
                raise NoSectionError(section)
        sectdict[self.optionxform(option)] = value

    def _read(self, fp, fpname):
        cursect = None                            # None, or a dictionary
        optname = None
        lineno = 0
        e = None                                  # None, or an exception
        while True:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            # comment or blank line?
            if line.strip() == '' or line[0] in '#;':
                continue
            if self.COMMENTCRE.match(line):
                continue
            # continuation line?
            if line[0].isspace() and cursect is not None and optname:
                value = line.strip()
                if value:
                    cursect[optname] = "%s\n%s" % (cursect[optname], value)
            # a section header or option header?
            else:
                # is it a section header?
                mo = self.SECTCRE.match(line)
                if mo:
                    sectname = mo.group('header')
                    # internally, the sections names are always stripped of spaces
                    # you can control how this is written to a file with
                    # __spaces_in_section_names 
                    sectname = sectname.strip()
                    if sectname in self._sections:
                        cursect = self._sections[sectname]
                    else:
                        cursect = {'__name__': sectname}
                        self._sections[sectname] = cursect
                    # So sections can't start with a continuation line
                    optname = None
                # an option line?
                else:
                    mo = self.OPTCRE.match(line)
                    if mo:
                        optname, optval = mo.group('option', 'value')
                        optname = optname.strip()
                        optval = optval.strip()
                        # allow empty values
                        if optval == '""':
                            optval = ''
                        # treat global options
                        if cursect == None:
                            self.__global_options[optname] = optval
                        else:
                            cursect[optname] = optval
                    else:
                        # a non-fatal parsing error occurred.  set up the
                        # exception but keep going. the exception will be
                        # raised at the end of the file and will contain a
                        # list of all bogus lines
                        if not e:
                            e = ParsingError(fpname)
                        e.append(lineno, repr(line))
        # if any parsing errors occurred, raise an exception
        if e:
            raise e

    def __value_needs_evalution(self, value):
        '''
        Whether a given value needs evaluation
        '''
        if value[0] != '$':
            return False
        return True

    def __option_needs_evaluation(self, section, option):
        '''
        Whether a given option value needs evalution
        '''
        return self.__value_needs_evalution(self.get(section, option, False))

    def write(self, fp):
        '''
        Writes a text representation of the configuration into fp

        Lines that define options that are 'parseable', such as 'dir'
        have to come first. The openssl parser reads the file sequentially and
        expects to have these values defined prior to use.
        
        '''
        if self.__global_options:
            for (key, value) in self.__global_options.items():
                fp.write("%s = %s\n" % (key, str(value).replace('\n', '\n\t')))
            fp.write("\n")
        for section in self._sections:

            if self.__spaces_in_section_names:
                section_fmt = "[ %s ]\n"
            else:
                section_fmt = "[%s]\n"
            
            fp.write(section_fmt % section)

            need_eval = [opt for opt in self._sections[section].keys() \
                         if self.__option_needs_evaluation(section, opt)]

            for (key, value) in self._sections[section].items():
                # First, skip options that need eval
                if key in need_eval:
                    continue
                else:
                    if key != "__name__":
                        fp.write("%s = %s\n" %
                                 (key, str(value).replace('\n', '\n\t')))

            # Write skiped keys (the ones that need eval)
            for key in need_eval:
                fp.write("%s = %s\n" %
                         (key, str(self._sections[section][key]).replace('\n', '\n\t')))
                
            fp.write("\n")



class OpenSSLConfigParser(OpenSSLRawConfigParser):

    def __init__(self):
        OpenSSLRawConfigParser.__init__(self)

    def create_default_config(self, rootdir=None):
        '''
        Create a default configuration.

        If rootdir is not supplied, the current working directory is used

        @rootdir: CA root directory
        '''

        try:
            from distroconf import distro_default_ca
        except ImportError:
            distro_default_ca = 'Fedora_PKI_CA'

        try:
            from distroconf import distro_default_ca_dir
        except ImportError:
            distro_default_ca_dir = '/tmp/pki/tls/CA'

        # global options
        self.set('', 'HOME', '.')
        self.set('', 'RANDFILE', '$ENV::HOME/.rnd')
        self.set('', 'oid_section', 'new_oids')
        self.add_section('new_oids')

        # [ca]
        self.add_section(' ca ')
        # default_ca = distro_default_ca
        self.set(' ca ', 'default_ca', distro_default_ca)

        self.create_ca(distro_default_ca, distro_default_ca_dir)
        self.create_policy('policy_anything')
        self.create_req()
        self.create_req_dn('req_distinguished_name')

    def create_ca(self, ca_name, ca_dir):
        '''
        Creates a CA section with the given name, having 'ca_dir' as the dir

        ca_name is the name you will use to refer to a set of ca-related
        configuration, that is, a ca section.

        dir is the base path of a certificate authority as built and managed
        by openssl.
        '''
        
        # [ca_name]
        self.add_section(ca_name)
        
        # dir = /path/to/ca
        self.set(ca_name, 'dir', ca_dir)

        # all other stuff
        self.set(ca_name, 'certs', '$dir/certs')
        self.set(ca_name, 'crl_dir', '$dir/crl')
        self.set(ca_name, 'database', '$dir/index.txt')
        self.set(ca_name, 'new_certs_dir', '$dir/newcerts')
        self.set(ca_name, 'certificate', '$dir/%s.crt' % ca_name)
        self.set(ca_name, 'serial', '$dir/serial')
        self.set(ca_name, 'crlnumber', '$dir/crlnumber')
        self.set(ca_name, 'crl', '$dir/%s.crl' % ca_name)
        self.set(ca_name, 'private_key', '$dir/private/%s.key' % ca_name)
        self.set(ca_name, 'RANDFILE', '$dir/private/.rand')
        self.set(ca_name, 'x509_extensions', 'usr_cert')

        self.set(ca_name, 'name_opt', ca_name)
        self.set(ca_name, 'cert_opt', ca_name)

        self.set(ca_name, 'default_days', '365')
        self.set(ca_name, 'default_crl_days', '30')
        self.set(ca_name, 'default_md', 'sha1')
        self.set(ca_name, 'preserve', 'no')

        self.set(ca_name, 'policy_match', 'policy_anything')

    def create_policy(self, policy_name, **overrides):
        '''
        Creates a match policy

        The default makes all bu commonName optional. If you want to override
        this default, supply the match rule and value as parameter name and
        value
        '''

        valid_values = ('optional', 'match', 'supplied')

        defaults = {'country_name' : 'optional',
                    'stateOrProvinceName' : 'optional',
                    'localityName' : 'optional',
                    'organizationName' : 'optional',
                    'organizationalUnitName' : 'optional',
                    'commonName' : 'supplied',
                    'emailAddress' : 'optional'}

        for key, value in overrides.items():
            if key in defaults:
                if value in valid_values:
                    defaults[key] = value

        self.add_section(policy_name)
        for key, value in defaults.items():
            self.set(policy_name, key, value)

    def create_req(self):
        section_name = 'req'
        self.add_section(section_name)
        self.set(section_name, 'default_bits', '1024')
        self.set(section_name, 'default_md', 'sha1')
        self.set(section_name, 'distinguished_name', 'req_distinguished_name')
        self.set(section_name, 'attributes', 'req_attributes')
        self.set(section_name, 'x509_extensions', 'v3_ca')

    def create_req_dn(self, dn):
        '''
        The idea here is that this information would be the default, but editable by
        the user, via a callback, and then merged with the current information.
        '''
        self.add_section(dn)
        # would be cool to fetch the country based on the locale or something else
        self.set(dn, 'countryName_default', 'US')
        self.set(dn, 'stateOrProvinceName_default', 'North Carolina')
        self.set(dn, 'localityName_default', 'Raleigh')
        self.set(dn, '0.organizationName_default', 'Example, Inc.')


    def get_default_ca(self):
        return self.get(' ca ', 'default_ca')

    def get_default_ca_dir(self):
        return self.get_ca_dir(self.get_default_ca())

    def get_ca_dir(self, ca=''):
        '''
        Returns the topmost directory for a CA.

        Snippet from config file might look like:
        dir		= ../../CA		# Where everything is kept
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'dir')

    def get_ca_certs(self, ca=''):
        '''
        Returns the issued certs dir for a CA.

        Snippet from config file might look like:
        certs		= $dir/certs		# Where the issued certs are kept
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'certs')

    def get_ca_crl_dir(self, ca=''):
        '''
        Snippet from config file might look like:
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'crl_dir')

    def get_ca_database(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'database')

    def get_ca_new_certs_dir(self, ca=''):
        '''
        Returns the dfault place for new certs issued by a CA.

        Snippet from config file might look like:
        new_certs_dir	= $dir/newcerts		# default place for new certs.
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'new_certs_dir')

    def get_ca_certificate(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'certificate')

    def get_ca_serial(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'serial')

    def get_ca_crlnumber(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'crlnumber')

    def get_ca_crl(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'crl')

    def get_ca_private_key(self, ca=''):
        '''
        Returns ...
        '''
        if not ca:
            ca = self.get_default_ca()
        return self.get(ca, 'private_key')

    def get_ca_private(self, ca=''):
        '''
        Returns the directory in which the private_key is saved
        '''
        return os.path.dirname(self.get_ca_private_key(ca))


if __name__ == '__main__':

    #filename = sys.argv[1]
    #raw = OpenSSLRawConfigParser()

    #print '>>> Files read:'
    #print raw.read('/etc/pki/tls/openssl.cnf')

    #print '>>> Global Options:'
    #print raw.global_options()

    #print '>>> Sections:'
    #print raw.sections()

    #print '>>> Creating OpenSSLConfigParser...'

    config = OpenSSLConfigParser()
    #config.read(filename)
    #config.set(' CA_default ', 'dir', '/tmp/pki/tls/CA')
    #print '>>> Default CA:'
    #print config.get_default_ca()

    #config.create_policy('policy_email', emailAddress='match')
    #config.write(sys.stdout)

    #default_ca = config.get_default_ca()

    #print config.get('', 'HOME', False)
    #print config.get('', 'HOME', True)

    #print config.get('', 'RANDFILE')
    #print config.get('', 'RANDFILE', True)

    #print config.get(' ca ', 'default_ca')

    #print config.get('Fedora_PKI_CA', 'crl_dir', False)
    #print config.get('Fedora_PKI_CA', 'crl_dir')

    


    
