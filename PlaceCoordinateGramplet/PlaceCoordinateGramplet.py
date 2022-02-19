#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2020 Christian Schulze
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

#------------------------------------------------------------------------
#
# Python modules
#
#------------------------------------------------------------------------

import os
import ctypes
import locale
import logging
_LOG = logging.getLogger("PlaceCoordinateGramplet")
from gi.repository import Gtk
use_geopy = False
try:
    if use_geopy:
        from geopy.geocoders import Nominatim
        STR_CITY_CONFIG = ['town', 'county', 'state', 'country']
        STR_ADDRESS_CONFIG = ['house_number', 'road', 'suburb', 'town', 'county', 'state', 'country']
    else:
        import gi
        gi.require_version('GeocodeGlib', '1.0')
        from gi.repository import GeocodeGlib
        STR_CITY_CONFIG = ['town', 'county', 'state', 'country']
        STR_ADDRESS_CONFIG = ['building', 'street', 'area', 'town', 'county', 'state', 'country']
except:
    pass

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gui.display import display_url
from gramps.gen.plug import Gramplet
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.db import DbTxn
from gramps.gen.config import config
from gramps.gen.utils.place import conv_lat_lon
from gramps.gen.constfunc import win
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext


def generate_address_string(location_information, entries=[
        'building', 'street', 'area', 'town', 'county', 'state', 'country']):
    name = []
    entries_temp = entries.copy() # dont remove items from static default argument!
    if ('building' in entries_temp and 'building' in location_information and
        'street' in entries_temp and 'street' in location_information):
        # geocodeglib
        entries_temp.remove('building')
        entries_temp.remove('street')
        name.append(location_information['street'] +
                    ' ' + location_information['building'])
    elif ('house_number' in entries_temp and 'house_number' in location_information and
        'road' in entries_temp and 'road' in location_information):
        # geopy
        entries_temp.remove('house_number')
        entries_temp.remove('road')
        name.append(location_information['road'] +
                    ' ' + location_information['house_number'])
    if('county' in entries_temp and 'county' in location_information and
       'town' in entries_temp and 'town' in location_information):
        if location_information['town'] in location_information['county']:
            entries_temp.remove('county')

    for entry in entries_temp:
        if entry in location_information:
            name.append(location_information[entry])
    return ", ".join(name)

#------------------------------------------------------------------------
#
# PlaceCoordinateGramplet class
#
#------------------------------------------------------------------------


class PlaceCoordinateGramplet(Gramplet):
    def active_changed(self, handle):
        self.update()

    def init(self):
        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add(self.gui.WIDGET)
        self.gui.WIDGET.show()

    def post_init(self):
        self.connect_signal('Place', self._active_changed)
        #OsmGps.__init__(self)

    def build_gui(self):
        """
        Build the GUI interface.
        """
        self.top = Gtk.Builder()  # IGNORE:W0201
        # Found out that Glade does not support translations for plugins, so
        # have to do it manually.
        base = os.path.dirname(__file__)
        glade_file = base + os.sep + "placecoordinate.glade"
        # This is needed to make gtk.Builder work by specifying the
        # translations directory in a separate 'domain'
        try:
            localedomain = "addon"
            localepath = base + os.sep + "locale"
            if hasattr(locale, 'bindtextdomain'):
                libintl = locale
            elif win():  # apparently wants strings in bytes
                localedomain = localedomain.encode('utf-8')
                localepath = localepath.encode('utf-8')
                libintl = ctypes.cdll.LoadLibrary('libintl-8.dll')
            else:  # mac, No way for author to test this
                libintl = ctypes.cdll.LoadLibrary('libintl.dylib')

            libintl.bindtextdomain(localedomain, localepath)
            libintl.textdomain(localedomain)
            libintl.bind_textdomain_codeset(localedomain, "UTF-8")
            # and finally, tell Gtk Builder to use that domain
            self.top.set_translation_domain("addon")
        except (OSError, AttributeError):
            # Will leave it in English
            _LOG.warn("Localization of PlaceCleanup failed!")

        self.top.add_from_file(glade_file)
        self.view = self.top.get_object("grid")

        # grid.attach(Gtk.Label(_("Search for:")), 1, i, 1, 1)
        self.entry_name = self.top.get_object("entry_name")
        self.searchButton = self.top.get_object("searchButton")  # Go
        self.searchButton.connect("clicked", self.on_searchButton_clicked)

        # grid.attach(Gtk.Label(_("Found place:")), 1, i, 1, 1)
        self.entry_foundName = self.top.get_object("entry_foundName")

        # grid.attach(Gtk.Label(_("Latitude:")), 1, i, 1, 1)
        self.entry_lat = self.top.get_object("entry_lat")
        # grid.attach(Gtk.Label(_("Longitude:")), 3, i, 1, 1)
        self.entry_long = self.top.get_object("entry_long")

        self.showInBrowserButton = self.top.get_object("showInBrowserButton")
        self.showInBrowserButton.connect(
            "clicked", self.on_showInBrowserButton_clicked)

        self.place_id_label = self.top.get_object("place_id_label")

        # grid.attach(Gtk.Label(_("Postal-Code:")), 1, i, 1, 1)
        self.entry_code = self.top.get_object("entry_code")

        # grid.attach(Gtk.Label(_("Latitude:")), 1, i, 1, 1)
        self.entry_lat_db = self.top.get_object("entry_lat_db")
        # grid.attach(Gtk.Label(_("Longitude:")), 3, i, 1, 1)
        self.entry_long_db = self.top.get_object("entry_long_db")

        self.fromMapButton = self.top.get_object("fromMapButton")
        self.fromMapButton.connect("clicked", self.on_fromMapButton_clicked)
        self.fromDBButton = self.top.get_object("fromDBButton")
        self.fromDBButton.connect("clicked", self.on_fromDBButton_clicked)
        self.applyButton = self.top.get_object("applyButton")
        self.applyButton.connect("clicked", self.on_apply_clicked)

        self.helpButton = self.top.get_object("helpButton")
        self.helpButton.connect("clicked", self.on_help_clicked)

        self.view.show_all()
        return self.view

    def on_help_clicked(self, widget):
        display_url("https://www.gramps-project.org/wiki/index.php/PlaceCoordinateGramplet")

    def on_showInBrowserButton_clicked(self, widget):
        if(len(self.entry_lat.get_text()) > 0 and
           len(self.entry_long.get_text()) > 0):
            path = "http://maps.google.com/maps?q=%s,%s" % (
                self.entry_lat.get_text(), self.entry_long.get_text())
            display_url(path)

    def on_searchButton_clicked(self, widget):
        # lat = config.get("geography.center-lat")
        # lon = config.get("geography.center-lon")
        # self.osm.grab_focus()
        if use_geopy:
            geolocator = Nominatim(user_agent="GrampsPlaceCoordinateGramplet")
            try :
                location = geolocator.geocode(self.entry_name.get_text())
                if location:
                    self.entry_lat.set_text("%.10f" % location.latitude)
                    self.entry_long.set_text("%.10f" % location.longitude)
                    self.entry_foundName.set_text(location.address)
                else:
                    self.entry_foundName.set_text(
                        _("The place was not found. "
                        "You may clarify the search keywords."))
            except Exception as e:
                self.entry_foundName.set_text(
                    _("Failed to search for the coordinates due to "
                    "some unexpected error.") + ' ' + str(e))
        else:
            try:
                location_ = GeocodeGlib.Forward.new_for_string(
                    self.entry_name.get_text())
                try:
                    result = location_.search()
                    error_message = "You may clarify the search keywords."
                except Exception as e:
                    result = None
                    error_message = str(e)
                if result:
                    result = result[0]  # use the first result
                    location_information = dict((p.name, result.get_property(
                        p.name)) for p in result.list_properties()
                        if result.get_property(p.name))
                    geo_loc = location_information['location']

                    self.entry_lat.set_text("%.10f" % geo_loc.get_latitude())
                    self.entry_long.set_text("%.10f" % geo_loc.get_longitude())
                    self.entry_foundName.set_text(
                        generate_address_string(location_information, STR_ADDRESS_CONFIG))
                else:
                    self.entry_foundName.set_text(
                        _("The place was not found.") + ' ' + error_message)
            except Exception as e:
                self.entry_foundName.set_text(
                    _("Failed to search for the coordinates due to "
                    "some unexpected error.") + ' ' + str(e))

    def on_fromMapButton_clicked(self, widget):
        latitude = config.get("geography.center-lat")
        longitude = config.get("geography.center-lon")
        if latitude != "" and longitude != "":
            self.entry_lat.set_text("%.8f" % latitude)
            self.entry_long.set_text("%.8f" % longitude)
            # self.osm.grab_focus()

            try:
                loc = GeocodeGlib.Location.new(latitude, longitude, 0)
                obj = GeocodeGlib.Reverse.new_for_location(loc)
                result = GeocodeGlib.Reverse.resolve(obj)

                location_information = dict((p.name, result.get_property(
                    p.name)) for p in result.list_properties()
                    if result.get_property(p.name))
                self.entry_foundName.set_text(
                    generate_address_string(location_information))
            except Exception as e:
                self.entry_foundName.set_text(_("The place was not identified.") + ' ' + str(e))
        else:
            self.entry_foundName.set_text(_("Coordinates were not given."))

    def on_fromDBButton_clicked(self, widget):
        latitude = self.entry_lat_db.get_text()
        longitude = self.entry_long_db.get_text()
        if latitude != "" and longitude != "":
            self.entry_lat.set_text(self.entry_lat_db.get_text())
            self.entry_long.set_text(self.entry_long_db.get_text())
            try:
                latitude, longitude = conv_lat_lon(
                    latitude, longitude, format="D.D8")
                latitude = float(latitude)
                longitude = float(longitude)
            except:
                self.entry_foundName.set_text(
                    _("Failed to interpret the input format."))

            # self.osm.grab_focus()
            try:
                loc = GeocodeGlib.Location.new(latitude, longitude, 0)
                obj = GeocodeGlib.Reverse.new_for_location(loc)
                result = GeocodeGlib.Reverse.resolve(obj)

                location_information = dict((p.name, result.get_property(
                    p.name)) for p in result.list_properties()
                    if result.get_property(p.name))
                self.entry_foundName.set_text(
                    generate_address_string(location_information))
            except Exception as e:
                self.entry_foundName.set_text(_("The place was not identified.") + ' ' + str(e))
        else:
            self.entry_foundName.set_text(_("Coordinates were not given."))

    def on_apply_clicked(self, widget):
        active_handle = self.get_active('Place')
        if active_handle:
            place = self.dbstate.db.get_place_from_handle(active_handle)
            if place:
                place.set_latitude(self.entry_lat.get_text())
                place.set_longitude(self.entry_long.get_text())
                # if (len(self.entry_code.get_text())>0):
                #     place.set_code(self.entry_code.get_text())
                with DbTxn(_("Edit Place (%s)") % place.title,
                           self.dbstate.db) as trans:
                    if not place.get_gramps_id():
                        place.set_gramps_id(
                            self.db.find_next_place_gramps_id())
                    self.dbstate.db.commit_place(place, trans)
                    #self.dbstate.emit("database-changed", ([active_handle],))

    def db_changed(self):
        self.dbstate.db.connect('place-update', self.update)
        self.main()
        if not self.dbstate.db.readonly:
            self.connect_signal('Place', self.update)

    def update_data(self, active_handle):
        if active_handle:
            place = self.dbstate.db.get_place_from_handle(active_handle)
            if place:
                self.place_id_label.set_text(_(
                    "DB entry [{id}] {name}:").format(
                        id=place.gramps_id,
                        name=place_displayer.display(self.dbstate.db, place)))
                descr = place_displayer.display(self.dbstate.db, place)
                self.entry_foundName.set_text(
                    _("Nothing has been searched yet"))
                code = place.get_code()
                if len(place.lat) > 0:
                    self.entry_lat_db.set_text(place.lat)
                else:
                    self.entry_lat_db.set_text("")
                self.entry_lat.set_text("")
                if len(place.long) > 0:
                    self.entry_long_db.set_text(place.long)
                else:
                    self.entry_long_db.set_text("")
                self.entry_long.set_text("")
                if len(code) > 0:
                    self.entry_code.set_text(code)
                else:
                    self.entry_code.set_text("")
                self.entry_name.set_text(descr)  # +", "+code)
                return True
        self.entry_foundName.set_text("")
        self.entry_lat.set_text("")
        self.entry_long.set_text("")
        self.entry_code.set_text("")
        self.entry_name.set_text(_("No place is active"))
        return False

    def get_has_data(self, active_handle):
        """
        Return True if the gramplet has data, else return False.
        """
        if active_handle:
            place = self.dbstate.db.get_place_from_handle(active_handle)
            if place:
                    return True
        return False

    def update_has_data(self):
        """
        Update the has_data indicator when gramplet is not visible.
        """
        active_handle = self.get_active('Place')
        if active_handle:
            self.set_has_data(self.get_has_data(active_handle))
        else:
            self.set_has_data(False)

    def main(self):
        active_handle = self.get_active('Place')
        if active_handle:
            self.set_has_data(self.update_data(active_handle))
        else:
            self.set_has_data(False)
