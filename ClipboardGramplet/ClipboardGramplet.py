#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010  Doug Blank <doug.blank@gmail.com>
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

# $Id: $

#-------------------------------------------------------------------------
#
# Python modules
#
#-------------------------------------------------------------------------
import pickle
from binascii import hexlify, unhexlify
#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
from gramps.gen.plug import Gramplet
from gramps.gui.clipboard import (MultiTreeView, ClipboardListModel,
                                  ClipboardListView, ClipText)

#-------------------------------------------------------------------------
#
# Local Functions
#
#-------------------------------------------------------------------------
def escape(data):
    """
    Remove newlines from text.
    """
    if isinstance(data, bytes):
        data = data.replace(b"0x0a", b"\\n")
    elif data:
        data = data.replace(chr(10), "\\n")
    return data

def unescape(data):
    """
    Replace newlines with \n text.
    """
    if isinstance(data, bytes):
        data = data.replace(b"\\n", b"0x0a")
    elif data:
        data = data.replace("\\n", "\\x0a")
    return data


#-------------------------------------------------------------------------
#
# ClipboardGramplet class
#
#-------------------------------------------------------------------------
class ClipboardGramplet(Gramplet):
    """
    A clipboard-like gramplet, that support group collections for data entry
    """
    def init(self):
        self.object_list = ClipboardListView(self.dbstate,
                 MultiTreeView(self.dbstate, self.uistate,
                 lambda: _("Clipboard Gramplet: %s") % self.gui.get_title()))
        self.otree = ClipboardListModel()
        self.object_list.set_model(self.otree)
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.object_list._widget)
        self.object_list._widget.show()
        self.save_data = []

    def db_changed(self):
        if self.dbstate.is_open():
            self.gui.data = self.save_data
            model = self.object_list._widget.get_model()
            if model:
                for o in model:
                    if isinstance(o[1], ClipText):
                        # type, timestamp, text, preview
                        data = pickle.dumps(("TEXT", escape(o[1]._obj)))
                    else:
                        # pickled: type, timestamp, handle, value
                        data = o[1]._pickle
                    if not escape(o[1]._value) in self.gui.data:
                        self.gui.data.append(hexlify(data).decode("ascii"))
                        self.gui.data.append(escape(o[1]._title))
                        self.gui.data.append(escape(o[1]._value))
                        self.gui.data.append(escape(o[1]._dbid))
                        self.gui.data.append(escape(o[1]._dbname))
            self.on_load()

    def on_load(self):
        try:
            i = 0
            while i < len(self.gui.data):
                data = unhexlify(self.gui.data[i])
                i += 1
                title = unescape(self.gui.data[i])
                i += 1
                value = unescape(self.gui.data[i])
                i += 1
                dbid = unescape(self.gui.data[i])
                i += 1
                dbname = unescape(self.gui.data[i])
                i += 1
                try:
                    # pickled bytes?
                    tuple_data = pickle.loads(data)
                    #data = eval(data)
                except:
                    tuple_data = ("TEXT", data)
                drag_type = tuple_data[0]
                # model = self.object_list._widget.get_model()
                class Selection(object):
                    def __init__(self, data):
                        self.data = data
                    def get_data(self):
                        return self.data
                class Target():
                    def name(self):
                        return drag_type
                class Context(object):
                    def list_targets(self):
                        return [Target()]
                    def get_actions(self):
                        return 1  # action = 1
                if self.dbstate.is_open():
                    if drag_type == "TEXT":
                        text = tuple_data[1]
                        # it could be bytes
                        if isinstance(text, bytes):
                            text = str(text, "utf-8")
                        self.object_list.object_drag_data_received(
                            self.object_list._widget,  # widget
                            Context(),        # drag type and action
                            0, 0,             # x, y
                            Selection(text),  # text
                            None,             # info (not used)
                            -1,               # time
                            dbname=dbname, dbid=dbid)
                    else:
                        try:
                            self.object_list.object_drag_data_received(
                                self.object_list._widget,  # widget
                                Context(),        # drag type and action
                                0, 0,             # x, y
                                Selection(data),  # pickled data
                                None,             # info (not used)
                                -1, title=title, value=value, dbid=dbid,
                                dbname=dbname
                                )  # time, data
                        except:
                            pass
        except:
            print("Invalid Collections Clipboard Gramplet data on load; skipping...")
            return
        if not self.dbstate.is_open():
            self.save_data = self.gui.data
            self.gui.data = []
            return

    def on_save(self):
        if not self.dbstate.is_open():
            self.gui.data = self.save_data
        else:
            self.gui.data = []  # clear out old data: data, title, value
        model = self.object_list._widget.get_model()
        if model:
            for o in model:
                # [0]: obj_type
                # [1]: Clipboard object, [1]._obj: pickle.dumps(data)
                # [2]: tooltip callback
                # [5]: dbid
                # [6]: dbname
                if isinstance(o[1], ClipText):
                    # type, timestamp, text, preview
                    data = pickle.dumps(("TEXT", escape(o[1]._obj)))
                else:
                    # pickled: type, timestamp, handle, value
                    data = o[1]._pickle
                if not escape(o[1]._value) in self.gui.data:
                    self.gui.data.append(hexlify(data).decode("ascii"))
                    self.gui.data.append(escape(o[1]._title))
                    self.gui.data.append(escape(o[1]._value))
                    self.gui.data.append(escape(o[1]._dbid))
                    self.gui.data.append(escape(o[1]._dbname))
