# Copyright (C) 2018 Andrew Vitu <a.p.vitu@gmail.com>
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301  USA

from gramps.gen.plug import Gramplet
from collections import defaultdict
from gramps.gen.const import GRAMPS_LOCALE as glocale
_ = glocale.translation.gettext

class HouseTimelineGramplet(Gramplet):
    def init(self):
        self.house_width = 40
        self.set_tooltip(_("Double-click name for details"))

    def on_load(self):
        self.no_wrap()
        tag = self.gui.buffer.create_tag("fixed")
        tag.set_property("font", "Courier 8")
        # set default house icon style.
        if len(self.gui.data) != 1:
            self.gui.data[:] = ["001", None]

    def db_changed(self):
        self.connect(self.dbstate.db,'person-add', self.update)
        self.connect(self.dbstate.db,'person-update', self.update)
        self.connect(self.dbstate.db,'person-delete', self.update)

    def save_update_options(self, widget=None):
        # saves a specific house icon style.
        style = self.get_option(_("House Icon Style"))
        self.gui.data[:] = [style.get_value()]
        self.update()
    
    def build_options(self):
        # builds a menu dropdown list of options.
        from gramps.gen.plug.menu import EnumeratedListOption
        style_list = EnumeratedListOption(_("House Icon Style"), self.gui.data[0])
        for item in [("001", _("Standard")),
                     ("002", _("Small")),
                     ("003", _("Unicode")),
                     ("004", _("None")),
                     ]:
            style_list.add_item(item[0], item[1])
        self.add_option(style_list)

    def main(self):
        self.set_text(_("Processing...") + "\n")
        yield True
        self.count_dict = defaultdict(int)
        self.residents = {}
        self.sorted_residents = {}
        self.clear_text()
        address_count = 0
        # get details of people dbhandle, name, address
        for p in self.dbstate.db.iter_people():
            person_handle = p.handle
            primary_name = p.get_primary_name()
            person_name = primary_name.get_name()
            person_addr = p.get_address_list()
            if person_addr:
                address_count += 1
                for item in person_addr:
                    # address format from db is:
                    # [0] street, [1] locality, [2] city, [3] pcode, [4] state/county, [5] country, [6] phone
                    location = item.get_text_data_list()
                    date = item.get_date_object()
                    self.build_parent_address_dict(location,date,person_handle,person_name)
        
        if address_count == 0:
            self.set_text(_("There are no individuals with Address data. Please add Address data to people."))
        self.build_house()
        start, end = self.gui.buffer.get_bounds()
        self.gui.buffer.apply_tag_by_name("fixed", start, end)
        self.append_text("", scroll_to="begin")
        yield False

    def build_parent_address_dict(self, address, date, person_handle, person_name):
        """
        Builds self.residents, The address + person_handle object.
        The collection is Address keyed (distinct)
        """
        # TODO: group addresses by locality or city
        address_key = self.format_address_key(address)
        # set resident to index key
        if address_key not in self.residents:
            self.residents[address_key] = {self.count_dict[address_key]: {'address':address,'date':date.get_ymd(),'handle':person_handle,'pname': person_name}}
        elif address_key in self.residents:
            self.residents[address_key][self.count_dict[address_key]] = {'address':address,'date':date.get_ymd(),'handle':person_handle,'pname': person_name}
        self.count_dict[address_key] += 1

    def format_address_key(self, address):
        """
        Builds a formatted Address string that can be used as a Key.
        """
        key = ""
        for k in address:
            if len(k) > 0:
                key += k + " "
        return key

    def build_house(self):
        """
        Outputs sorted details from self.residents.
        """
        gl_location = _("Location")
        gl_time = _("Time In Family")
        gl_first_resident = _("First Resident")
        gl_last_resident = _("Last Resident")
        gl_timeline = _("Timeline")
        gl_unknown = _("Unknown")
        gl_total_residents = _("Total Known Residents")
        for resident in self.residents.items():
            # sort residents by date.
            sorted_dates = sorted(resident[1].items(),key=lambda k: k[1]['date'])
            first_year = 0
            last_year = int(sorted_dates[-1][1]['date'][0])
            for years in sorted_dates:
                date = years[1]['date'][0]
                first_year = date if date != 0 and first_year == 0 else first_year
            time_in_family = last_year - first_year if first_year != 0 else gl_unknown
            self.append_text("=========================\n")
            self.render_house(self.gui.data[0])
            self.append_text("{0}: {1}\n".format(gl_location,resident[0]) +
            ("{0}: {1} years\n".format(gl_time,time_in_family)) +
            ("{0}: {1} - {2}\n".format(gl_first_resident,sorted_dates[0][1]['date'][0],sorted_dates[0][1]['pname'])) +
            ("{0}: {1} - {2}\n".format(gl_last_resident,sorted_dates[-1][1]['date'][0],sorted_dates[-1][1]['pname'])) +
            ("{0}: {1}\n".format(gl_total_residents,len(sorted_dates))) +
            "                        \n")
            self.append_text("{0}:\n".format(gl_timeline))
            # TODO: if duplicate person handles exist, denote as time period of person.
            for item in sorted_dates:
                self.append_text("{0} - ".format(item[1]['date'][0]))
                self.link(item[1]['pname'],"Person",item[1]['handle'])
                self.append_text("\n")

    def render_house(self,house_type):
        """
        Renders various types of ASCII houses.
        """
        if house_type == "001":
            self.append_text(
                "     ~~~\n" +
                " __[]________\n" +
                "/____________\ \n" +
                "|            | \n" +
                "| [)(]  [)(] | \n" +
                "|     __     | \n" +
                "|    |  |    | \n" +
                "|____|__|____| \n" +
                "                        \n"
            )
        elif house_type == "002":
            self.append_text(
                " .___. \n" +
                "/ \___\ \n" +
                "|_|_#_| \n" +
                "                        \n"
            )
        elif house_type == "003":
            self.append_text(
                "⌂ \n"
            )