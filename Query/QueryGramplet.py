#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007  Donald N. Allingham
# Copyright (C) 2008  Brian Matherly
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

# $Id$

#import os

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext
from gramps.gui.plug.quick import run_quick_report_by_name

#from gramps.gen.const import USER_PLUGINS
#import os.path.join(USER_PLUGINS, 'PythonGramplet', 'PythonGramplet')

from gramps.gen.plug import Gramplet
import gramps.gen

#------------------------------------------------------------------------
#
# Gramplet class
#
#------------------------------------------------------------------------
class PythonGramplet(Gramplet):
    def init(self):
        import gc
        # gc.DEBUG_OBJECTS not present in python3
        gc.set_debug(gc.DEBUG_UNCOLLECTABLE|gc.DEBUG_SAVEALL)
        self.prompt = ">"
        self.previous = ""
        self.set_tooltip(_("Enter Python expressions"))
        self.gc = gc
        self.env = {"dbstate": self.gui.dbstate,
                    "uistate": self.gui.uistate,
                    "db": self.gui.dbstate.db,
                    "gc": self.gc,
                    "self": self,
                    "Date": gramps.gen.lib.Date,
                    }
        # GUI setup:
        self.gui.textview.set_editable(True)
        self.set_text("Python %s\n%s " % (sys.version, self.prompt))
        self.gui.textview.connect('key-press-event', self.on_key_press)

    def format_exception(self, max_tb_level=10):
        import traceback
        retval = ''
        exceptionType, exceptionValue, exceptionTraceback = sys.exc_info()
        lines = traceback.format_exception(exceptionType,
                                           exceptionValue,
                                           exceptionTraceback)
        retval += "".join(lines)
        return retval

    def process_command(self, command):
        # update states, in case of change:
        self.env["dbstate"] = self.gui.dbstate
        self.env["uistate"] = self.gui.uistate
        self.env["db"] = self.gui.dbstate.db
        _retval = None
        if "_retval" in self.env:
            del self.env["_retval"]
        if self.previous:
            if command:
                self.previous += "\n" + command
                return
            else:
                exp = self.previous
        else:
            exp = command.strip()
        try:
            _retval = eval(exp, self.env)
            self.previous = ""
        except:
            try:
                exec(exp, self.env)
                self.previous = ""
                self.prompt = ">"
            except SyntaxError:
                if command:
                    self.previous = exp
                    self.prompt = "-"
                else:
                    self.previous = ""
                    self.prompt = ">"
                    _retval = self.format_exception()
            except:
                self.previous = ""
                self.prompt = ">"
                _retval = self.format_exception()
        if "_retval" in self.env:
            _retval = self.env["_retval"]
        return _retval

    def on_key_press(self, widget, event):
        from gi.repository import Gtk
        from gi.repository import Gdk
        if (event.keyval == Gdk.keyval_from_name("Home") or
            ((event.keyval == Gdk.keyval_from_name("a") and
              event.get_state() & Gdk.ModifierType.CONTROL_MASK))):
            buffer = widget.get_buffer()
            cursor_pos = buffer.get_property("cursor-position")
            iter = buffer.get_iter_at_offset(cursor_pos)
            line_cnt = iter.get_line()
            start = buffer.get_iter_at_line(line_cnt)
            start.forward_chars(2)
            buffer.place_cursor(start)
            return True
        elif (event.keyval == Gdk.keyval_from_name("End") or
              (event.keyval == Gdk.keyval_from_name("e") and
               event.get_state() & Gdk.ModifierType.CONTROL_MASK)):
            buffer = widget.get_buffer()
            end = buffer.get_end_iter()
            buffer.place_cursor(end)
            return True
        elif event.keyval == Gdk.keyval_from_name("Return"):
            echo = False
            buffer = widget.get_buffer()
            cursor_pos = buffer.get_property("cursor-position")
            iter = buffer.get_iter_at_offset(cursor_pos)
            line_cnt = iter.get_line()
            start = buffer.get_iter_at_line(line_cnt)
            line_len = iter.get_chars_in_line()
            buffer_cnt = buffer.get_line_count()
            if (buffer_cnt - line_cnt) > 1:
                line_len -= 1
                echo = True
            end = buffer.get_iter_at_line_offset(line_cnt, line_len)
            line = buffer.get_text(start, end, True)
            self.append_text("\n")
            if line.startswith(self.prompt):
                line = line[2:]
            else:
                self.append_text("%s " % self.prompt)
                end = buffer.get_end_iter()
                buffer.place_cursor(end)
                return True
            if echo:
                self.append_text(("%s " % self.prompt) + line)
                end = buffer.get_end_iter()
                buffer.place_cursor(end)
                return True
            _retval = self.process_command(line)
            if _retval is not None:
                self.append_text("%s\n" % str(_retval))
            self.append_text("%s " % self.prompt)
            end = buffer.get_end_iter()
            buffer.place_cursor(end)
            return True
        return False

class QueryGramplet(PythonGramplet):
    def init(self):
        self.prompt = "$"
        self.set_tooltip(_("Enter SQL query"))
        # GUI setup:
        self.gui.textview.set_editable(True)
        self.set_text("Structured Query Language\n%s " % self.prompt)
        self.gui.textview.connect('key-press-event', self.on_key_press)

    def process_command(self, command):
        retval = run_quick_report_by_name(self.gui.dbstate,
                                          self.gui.uistate,
                                          'Query Quickview',
                                          command)
        return retval

