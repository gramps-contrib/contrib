# -*- coding: utf-8 -*-
#!/usr/bin/env python
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
from gi.repository import Gtk
import os

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------

from gramps.gen.const import USER_PLUGINS
from gramps.gui.glade import Glade
from gramps.gui.managedwindow import ManagedWindow
from gramps.gui.widgets import MonitoredEntry, MonitoredDate
from gramps.gui.plug import tool
import gramps.gen.datehandler

#------------------------------------------------------------------------
#
# Internationalisation
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

import gramps.gen.constfunc

# Handlers and signal class

class GtkHandlers:
    def on_quit_clicked(event):
        print('quit')
        Gtk.main_quit()

    def on_ok_clicked(event):
        print('save')
        Gtk.main_save()


class Witness(tool.Tool, ManagedWindow):
    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate

        self.label = _('Sources Index')
        self.base = os.path.dirname(__file__)

        ManagedWindow.__init__(self, uistate,[], self.__class__)
        self.set_window(Gtk.Window(),Gtk.Label(),'')

        tool.Tool.__init__(self, dbstate, options_class, name)

        glade_file = os.path.join(USER_PLUGINS, "SourceIndex", "witness.glade")

        if gramps.gen.constfunc.lin():
            import locale
            locale.setlocale(locale.LC_ALL, '')
            # This is needed to make gtk.Builder work by specifying the
            # translations directory
            locale.bindtextdomain("addon", self.base + "/locale")

            self.glade = Gtk.Builder()
            self.glade.set_translation_domain("addon")

            self.glade.add_from_file(glade_file)

            from gi.repository import GObject
            GObject.GObject.__init__(self.glade)

            window = self.glade.get_object('witness_editor')

            self.set_window(window, self.glade.get_object('title'), self.label)

            self.ok_button = self.glade.get_object('ok')
            self.quit_button = self.glade.get_object('cancel')

        else:

            # Glade class from gui/glade.py and gui/managedwindow.py
            self.top = Glade()
            window = self.top.toplevel
            self.set_window(window, None, glade_file)

            self.ok_button = self.top.get_object('ok')
            self.quit_button = self.top.get_object('cancel')

        self.ok_button.connect('clicked', self.close)
        self.quit_button.connect('clicked', self.close)

        self.window.show()

    def __getitem__(self, key):
        return self.glade.get_widget(key)

    def _setup_fields(self):
        r'''
        Gramps XML storage means ability to also import/manage alone records
        /!\ some attributes are translated keys
        see data_item keys and eventref types of attribute
        '''

        #/database/people/person/name/surname/surname/text()
        self.wname   = MonitoredEntry(
            self.top.get_object("wname"),
            self.obj.set_wname,
            self.obj.get_wname,
            self.db.readonly)

        #/database/people/person/name/first/text()
        self.wfname  = MonitoredEntry(
            self.top.get_object("wfname"),
            self.obj.set_wfname,
            self.obj.get_wfname,
            self.db.readonly)

        #/database/people/person/eventref/attribute/@type
        #/database/people/person/eventref/attribute/@value
        self.wage  = MonitoredEntry(
            self.top.get_object("wage"),
            self.obj.set_wage,
            self.obj.get_wage,
            self.db.readonly)

        #/database/people/person/eventref/@hlink
        #/database/events/event/place/@hlink
        #/database/places/placeobj/ptitle/text()
        self.worig  = MonitoredEntry(
            self.top.get_object("worig"),
            self.obj.set_worig,
            self.obj.get_worig,
            self.db.readonly)

        #/database/people/person/eventref/@hlink
        #/database/events/event/description/text()
        self.woccu  = MonitoredEntry(
            self.top.get_object("woccu"),
            self.obj.set_woccu,
            self.obj.get_woccu,
            self.db.readonly)

        #/database/people/person/eventref/@hlink
        #/database/events/event/dateval/@val
        #/database/events/event/description/text()
        self.wlive  = MonitoredEntry(
            self.top.get_object("wlive"),
            self.obj.set_wlive,
            self.obj.get_wlive,
            self.db.readonly)

        #/database/people/person/personref/@hlink
        #/database/people/person/@handle
        #/database/people/person/personref/@rel
        self.wrelation  = MonitoredEntry(
            self.top.get_object("wrelation"),
            self.obj.set_wrelation,
            self.obj.get_wrelation,
            self.db.readonly)


class WitnessOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self,name,person_id=None):
        tool.ToolOptions.__init__(self, name, person_id)
