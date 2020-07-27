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

"Set Attribute Tool"

#-------------------------------------------------
#
# python modules
#
#-------------------------------------------------
# import time

#-------------------------------------------------
#
# GRAMPS modules
#
#-------------------------------------------------
from gramps.gui.plug import MenuToolOptions, PluginWindows
from gramps.gen.plug.menu import StringOption, FilterOption, PersonOption, \
    BooleanOption
import gramps.gen.lib
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
import gramps.gen.plug.report.utils as ReportUtils

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


#-------------------------------------------------
#
# Tool Classes
#
#-------------------------------------------------
class SetAttributeOptions(MenuToolOptions):
    """ Set Attribute options  """
    def __init__(self, name, person_id=None, dbstate=None):
        self.__db = dbstate.get_database()
        MenuToolOptions.__init__(self, name, person_id, dbstate)

    def add_menu_options(self, menu):

        """ Add the options """
        category_name = _("Options")

        self.__filter = FilterOption(_("Person Filter"), 0)
        self.__filter.set_help(_("Select filter to restrict people"))
        menu.add_option(category_name, "filter", self.__filter)
        self.__filter.connect('value-changed', self.__filter_changed)

        self.__pid = PersonOption(_("Filter Person"))
        self.__pid.set_help(_("The center person for the filter"))
        menu.add_option(category_name, "pid", self.__pid)
        self.__pid.connect('value-changed', self.__update_filters)

        attribute_text = StringOption(_("Attribute"), "")
        attribute_value = StringOption(_("Value"), "")

        attribute_text.set_help(_("Attribute type to add or edit"))
        attribute_value.set_help(_("Attribute value to add or edit"))

        menu.add_option(category_name, "attribute_text", attribute_text)
        menu.add_option(category_name, "attribute_value", attribute_value)
        self.__attribute_text = attribute_text
        self.__attribute_value = attribute_value

        remove = BooleanOption(_("Remove"), False)
        remove.set_help(_("Remove attribute type and value set"))
        menu.add_option(category_name, "remove", remove)

        self.__update_filters()

    def __update_filters(self):
        """
        Update the filter list based on the selected person
        """
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        filter_list = ReportUtils.get_person_filters(person, False)
        self.__filter.set_filters(filter_list)

    def __filter_changed(self):
        """
        Handle filter change. If the filter is not specific to a person,
        disable the person option
        """
        filter_value = self.__filter.get_value()
        if filter_value in [1, 2, 3, 4]:
            # Filters 0, 2, 3, 4 and 5 rely on the center person
            self.__pid.set_available(True)
        else:
            # The rest don't
            self.__pid.set_available(False)


class SetAttributeWindow(PluginWindows.ToolManagedWindowBatch):
    def get_title(self):
        return _("Set Attribute")

    def initial_frame(self):
        return _("Options")

    def run(self):
        self.remove = self.options.menu.get_option_by_name(
            'remove').get_value()
        attribute_text = self.options.handler.options_dict['attribute_text']
        self.add_results_frame(_("Results"))
        if not attribute_text:
            self.results_write(_("Cannot save attribute") + '\n' +
                               _("The attribute type cannot be empty"))
            return
        attribute_value = self.options.handler.options_dict['attribute_value']
        specified_type = gramps.gen.lib.AttributeType()
        specified_type.set(attribute_text)

        self.db.disable_signals()

        self.filter_option = self.options.menu.get_option_by_name('filter')
        self.filter = self.filter_option.get_filter()  # the actual filter

        people = self.filter.apply(self.db, self.db.iter_person_handles())

        num_people = self.db.get_number_of_people()

        if not self.remove:
            with DbTxn(_("Set Attribute"), self.db, batch=True) as self.trans:
                self.results_write(_("Processing...\n"))
                self.progress.set_pass(_('Setting attributes...'),
                                       num_people)
                count = 0
                self.results_write(
                    _("Setting '%s' attributes to '%s'...\n\n") %
                    (attribute_text, attribute_value))
                for person_handle in people:
                    count += 1
                    self.progress.step()
                    person = self.db.get_person_from_handle(person_handle)
                    done = False
                    for attr in person.get_attribute_list():
                        if attr.get_type() == specified_type:
                            self.results_write("  %d) Changed" % count)
                            self.results_write_link(
                                name_displayer.display(person),
                                person, person_handle)
                            self.results_write(" from '%s'\n" %
                                               attr.get_value())
                            attr.set_value(attribute_value)
                            done = True
                            break
                    if not done:
                        attr = gramps.gen.lib.Attribute()
                        attr.set_type(specified_type)
                        attr.set_value(attribute_value)
                        person.add_attribute(attr)
                        # Update global attribute list:
                        if attr.type.is_custom() and str(attr.type):
                            self.db.individual_attributes.update(
                                [str(attr.type)])
                        self.results_write("  %d) Added attribute to" % count)
                        self.results_write_link(name_displayer.display(person),
                                                person, person_handle)
                        self.results_write("\n")
                    self.db.commit_person(person, self.trans)
            self.results_write(_("\nSet %d '%s' attributes to '%s'\n") %
                               (count, attribute_text, attribute_value))
        else:
            with DbTxn(_("Remove Attribute"), self.db,
                       batch=True) as self.trans:
                self.results_write(_("Processing...\n"))
                self.progress.set_pass(_('Removing attributes...'),
                                       num_people)
                count = 0
                for person_handle in people:
                    count += 1
                    self.progress.step()
                    person = self.db.get_person_from_handle(person_handle)
                    done = False
                    for attr in person.get_attribute_list():
                        if (attr.get_type() == specified_type and
                            (attribute_value == '' or
                             attr.get_value() == attribute_value)):
                            person.remove_attribute(attr)
                            # Update global attribute list:
                            self.db.individual_attributes.update(
                                [str(attr.type)])
                            self.results_write(
                                "  %d) Changed" % count)
                            self.results_write_link(
                                name_displayer.display(person),
                                person, person_handle)
                            self.results_write(
                                " from '%s'\n" % attr.get_value())
                            done = True
                            break
                    if done:
                        self.results_write(
                            _("\nRemoving %d '%s' attributes to '%s'\n") %
                            (count, attribute_text, attribute_value))
                        self.db.commit_person(person, self.trans)
        self.db.enable_signals()
        self.db.request_rebuild()
        self.results_write(_("Done!\n"))
