#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2008       Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2011-2012  Doug Blank <doug.blank@gmail.com>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

# $Id: $

"""Tools/Database Processing/Fix Capitalization of Given Names"""

#-------------------------------------------------------------------------
#
# gnome/gtk
#
#-------------------------------------------------------------------------
from gi.repository import GObject
from gi.repository import Gtk

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.db import DbTxn
from gramps.gen.const import URL_MANUAL_PAGE
from gramps.gui.utils import ProgressMeter
from gramps.gui.display import display_help
from gramps.gui.managedwindow import ManagedWindow

from gramps.gui.dialog import OkDialog
from gramps.gui.plug import tool
from gramps.gen.constfunc import lin
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
from gramps.gui.glade import Glade

#-------------------------------------------------------------------------
#
# constants
#
#-------------------------------------------------------------------------


WIKI_HELP_PAGE = '%s_-_Tools' % URL_MANUAL_PAGE
WIKI_HELP_SEC = _('manual|Fix_Capitalization_of_Given_Names...')

def capitalize(given):
    """
    Takes a given name and returns a proper-case version of it.
    """
    retval = ""
    previous = None
    for char in given:
        if previous is None or not previous.isalpha():
            retval += char.upper()
        else:
            retval += char.lower()
        previous = char
    return retval

#-------------------------------------------------------------------------
#
# ChangeGivenNames
#
#-------------------------------------------------------------------------
class ChangeGivenNames(tool.BatchTool, ManagedWindow):

    def __init__(self, dbstate, user, options_class, name, callback=None):
        uistate = user.uistate
        self.label = _('Capitalization changes')
        self.dbstate = dbstate
        self.uistate = uistate
        self.cb = callback

        ManagedWindow.__init__(self,uistate,[],self.__class__)
        self.set_window(Gtk.Window(),Gtk.Label(),'')

        tool.BatchTool.__init__(self, dbstate, user, options_class, name)
        if self.fail:
            return

        given_name_dict = self.get_given_name_dict()

        self.progress = ProgressMeter(_('Checking Given Names'),'',
                                      parent=uistate.window)
        self.progress.set_pass(_('Searching given names'),
                               len(given_name_dict.keys()))
        self.name_list = []

        for name in given_name_dict.keys():
            if name != capitalize(name):
                self.name_list.append((name, given_name_dict[name]))

            if uistate:
                self.progress.step()

        if self.name_list:
            self.display()
        else:
            self.progress.close()
            self.close()
            OkDialog(_('No modifications made'),
                     _("No capitalization changes were detected."),
                     parent=uistate.window)

    def get_given_name_dict(self):
        givennames = {}
        self.name_map = {}
        for person in self.db.iter_people():
            allnames = [person.get_primary_name()] + person.get_alternate_names()
            allnames = set(name.get_first_name().strip() for name in allnames)
            for givenname in allnames:
                givennames[givenname] = givennames.get(givenname, 0) + 1
                self.name_map[givenname] = self.name_map.get(givenname, set([]))
                self.name_map[givenname].add(person.handle)
        return givennames

    def display(self):

        if lin():
            import locale, os
            locale.setlocale(locale.LC_ALL, '')
            # This is needed to make gtk.Builder work by specifying the
            # translations directory
            base = os.path.dirname(__file__)
            locale.bindtextdomain("addon", base + "/locale")

            self.glade = Gtk.Builder()
            self.glade.set_translation_domain("addon")

            path = base + "/changenames.glade"
            self.glade.add_from_file(path)

            #from gi.repository import GObject
            GObject.GObject.__init__(self.glade)

            self.top = self.glade.get_object('changenames')

            self.glade.connect_signals({
                "destroy_passed_object" : self.close,
                "on_ok_clicked" : self.on_ok_clicked,
                "on_help_clicked" : self.on_help_clicked,
                "on_edit_clicked" : self.on_edit_clicked,
                "on_delete_event"   : self.close,
                })

            self.list = self.glade.get_object("list")
            self.set_window(self.top, self.glade.get_object('title'), self.label)

        else:
            self.top = Glade("changenames.glade")

            window = self.top.toplevel
            self.top.connect_signals({
                "destroy_passed_object" : self.close,
                "on_ok_clicked" : self.on_ok_clicked,
                "on_help_clicked" : self.on_help_clicked,
                "on_edit_clicked" : self.on_edit_clicked,
                "on_delete_event"   : self.close,
                })

            self.list = self.top.get_object("list")
            self.set_window(window,self.top.get_object('title'),self.label)

        # selected, original name, changed, count
        self.model = Gtk.ListStore(GObject.TYPE_BOOLEAN, GObject.TYPE_STRING,
                                   GObject.TYPE_STRING, GObject.TYPE_INT)
        self.handles = {}

        r = Gtk.CellRendererToggle()
        r.connect('toggled',self.toggled)
        c = Gtk.TreeViewColumn(_('Select'),r,active=0)
        self.list.append_column(c)

        c = Gtk.TreeViewColumn(_('Original Name'),
                               Gtk.CellRendererText(),text=1)
        self.list.append_column(c)

        c = Gtk.TreeViewColumn(_('Capitalization Change'),
                               Gtk.CellRendererText(),text=2)
        self.list.append_column(c)

        c = Gtk.TreeViewColumn(_('Affected Names'),
                               Gtk.CellRendererText(),text=3)
        self.list.append_column(c)

        self.list.set_model(self.model)

        self.iter_list = []
        self.progress.set_pass(_('Building display'),len(self.name_list))
        for name, count in self.name_list:
            handle = self.model.append()
            self.model.set_value(handle,0, False)
            self.model.set_value(handle,1, name)
            namecap = capitalize(name)
            self.model.set_value(handle,2, namecap)
            self.model.set_value(handle,3, count)
            self.iter_list.append(handle)
            self.progress.step()
        self.progress.close()

        self.show()

    def toggled(self,cell,path_string):
        path = tuple(map(int, path_string.split(':')))
        row = self.model[path]
        row[0] = not row[0]

    def build_menu_names(self, obj):
        return (self.label,None)

    def on_help_clicked(self, obj):
        """Display the relevant portion of GRAMPS manual"""
        display_help(WIKI_HELP_PAGE , WIKI_HELP_SEC)

    def on_edit_clicked(self, button):
        """Edit the selected person"""
        from gramps.gui.editors import EditPerson
        selection = self.list.get_selection()
        store, paths = selection.get_selected_rows()
        tpath = paths[0] if len(paths) > 0 else None
        node = store.get_iter(tpath) if tpath else None
        if node:
            name = store.get_value(node, 1)
            for handle in self.name_map[name]:
                person = self.dbstate.db.get_person_from_handle(handle)
                EditPerson(self.dbstate, self.uistate, [], person)

    def on_ok_clicked(self, obj):
        with DbTxn(_("Capitalization changes"), self.db, batch=True
                   ) as self.trans:
            self.db.disable_signals()
            changelist = set(self.model.get_value(node,1)
                             for node in self.iter_list
                                if self.model.get_value(node,0))

            for handle in self.db.get_person_handles(False):
                person = self.db.get_person_from_handle(handle)
                change = False
                for name in [person.get_primary_name()] + person.get_alternate_names():
                    if name.first_name in changelist:
                        change = True
                        fname = capitalize(name.first_name)
                        name.set_first_name(fname)
                if change:
                    self.db.commit_person(person, self.trans)

        self.db.enable_signals()
        self.db.request_rebuild()
        self.close()
        self.cb()

#------------------------------------------------------------------------
#
#
#
#------------------------------------------------------------------------
class ChangeGivenNamesOptions(tool.ToolOptions):
    """
    Defines options and provides handling interface.
    """

    def __init__(self, name,person_id=None):
        tool.ToolOptions.__init__(self, name,person_id)
