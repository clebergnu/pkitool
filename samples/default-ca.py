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
default-ca.py

    
"""
from pkitool.ca import CertificateAuthority
from pkitool.configparser import OpenSSLConfigParser

from getpass import getpass

def dont_ask_key(caname):
    return caname

def ask_key_password_console(caname):
    first_pass = getpass('Please enter %s Key password: ' % caname)
    second_pass = getpass('Please verify %s Key password: ' % caname)

    if first_pass != second_pass:
        print 'Passwords do not match, try again!'
        ask_key_password_console(caname)
    else:
        return first_pass

def ask_key_password_gui(caname):
    try:
        import gtk
    except ImportError:
        return ask_key_password_console(caname)

    class PasswordInputDialog(gtk.Dialog):
        def __init__(self):
            gtk.Dialog.__init__(self, parent=None, flags=0, buttons=(gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))

            # hig stuff
            self.set_border_width(5)
            self.vbox.set_border_width(2)
            self.vbox.set_spacing(6)
            
            self.set_title('Enter password for %s key' % caname)

            self.first_pass_label = gtk.Label('Enter password')
            self.first_pass_entry = gtk.Entry()
            self.first_pass_entry.set_visibility(False)
            self.second_pass_label = gtk.Label('Verify password')
            self.second_pass_entry = gtk.Entry()
            self.second_pass_entry.set_visibility(False)

            self.table = gtk.Table(2, 2, False)
            self.table.attach(self.first_pass_label, 0, 1, 0, 1, xoptions=gtk.FILL)
            self.table.attach(self.first_pass_entry, 1, 2, 0, 1, xoptions=gtk.FILL|gtk.EXPAND)
            self.table.attach(self.second_pass_label, 0, 1, 1, 2, xoptions=gtk.FILL)
            self.table.attach(self.second_pass_entry, 1, 2, 1, 2, xoptions=gtk.FILL|gtk.EXPAND)

            self.table.show_all()
            
            self.vbox.add(self.table)

        def getpass(self):
            response = self.run()
            if response == gtk.RESPONSE_ACCEPT:
                if self.first_pass_entry.get_text() == self.second_pass_entry.get_text():
                    return self.first_pass_entry.get_text()
                else:
                    d = gtk.MessageDialog(parent=self,
                                          message_format='Passwords do not match!',
                                          buttons=gtk.BUTTONS_OK,
                                          flags=gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)
                    d.run()
                    d.destroy()

                    self.first_pass_entry.set_text('')
                    self.second_pass_entry.set_text('')
                    self.first_pass_entry.grab_focus()
                    
                    return self.getpass()
                

    passdialog = PasswordInputDialog()
    return passdialog.getpass()

if __name__ == '__main__':
    config = OpenSSLConfigParser()
    config.create_default_config()
    default_ca = config.get_default_ca()
    config.set(default_ca, 'dir', 'default-ca')

    ca = CertificateAuthority(config)

    ca.register_callback('get_ca_key_password', dont_ask_key, default_ca)

    ca.create_directory_structure()
    ca.init()
