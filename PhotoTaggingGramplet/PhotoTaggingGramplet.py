#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2013 Artem Glebov <artem.glebov@gmail.com>
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

#-------------------------------------------------------------------------
#
# Standard python modules
#
#-------------------------------------------------------------------------
import sys
import os
import pickle
import logging

LOG = logging.getLogger(".PhotoTaggingGramplet")

#-------------------------------------------------------------------------
#
# GTK/Gnome modules
#
#-------------------------------------------------------------------------
from gi.repository import Gtk
from gi.repository import Gdk
from gi.repository import GdkPixbuf

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.utils.file import media_path_full
from gramps.gen.errors import WindowActiveError
from gramps.gen.config import config
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.plug import Gramplet, MenuOptions
from gramps.gen.lib import MediaRef, Person
from gramps.gui.editors.editperson import EditPerson
from gramps.gui.selectors import SelectorFactory
from gramps.gen.plug.menu import BooleanOption, NumberOption
from gramps.gui.plug import PluginWindows
from gramps.gui.widgets import SelectionWidget, Region
from gramps.gui.ddtargets import DdTargets

from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _ = glocale.get_addon_translator(__file__).gettext
except ValueError:
    _ = glocale.translation.gettext

#-------------------------------------------------------------------------
#
# face detection module
#
#-------------------------------------------------------------------------
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
import facedetection

#-------------------------------------------------------------------------
#
# configuration
#
#-------------------------------------------------------------------------

GRAMPLET_CONFIG_NAME = "phototagginggramplet"
CONFIG = config.register_manager(GRAMPLET_CONFIG_NAME)
CONFIG.register("detection.box_size", (50, 50))
CONFIG.register("detection.inside_existing_boxes", False)
CONFIG.register("detection.sensitivity", 10)
CONFIG.register("selection.replace_without_asking", False)
CONFIG.load()
CONFIG.save()

MIN_FACE_SIZE = CONFIG.get("detection.box_size")
REPLACE_WITHOUT_ASKING = CONFIG.get("selection.replace_without_asking")
DETECT_INSIDE_EXISTING_BOXES = CONFIG.get("detection.inside_existing_boxes")
SENSITIVITY = CONFIG.get("detection.sensitivity")

def save_config():
    CONFIG.set("detection.box_size", MIN_FACE_SIZE)
    CONFIG.set("detection.inside_existing_boxes", DETECT_INSIDE_EXISTING_BOXES)
    CONFIG.set("detection.sensitivity", SENSITIVITY)
    CONFIG.set("selection.replace_without_asking", REPLACE_WITHOUT_ASKING)
    CONFIG.save()

#-------------------------------------------------------------------------
#
# Gramplet Options
#
#-------------------------------------------------------------------------

THUMBNAIL_IMAGE_SIZE = (50, 50)

class PhotoTaggingOptions(MenuOptions):

    def __init__(self):
        MenuOptions.__init__(self)

    def add_menu_options(self, menu):
        category_name = _("Selection")
        self.replace_without_asking = BooleanOption(
                                 _("Replace existing references to the person "
                                   "being assigned without asking"),
                                 REPLACE_WITHOUT_ASKING)

        menu.add_option(category_name, "replace_without_asking",
                        self.replace_without_asking)

        category_name = _("Face detection")
        width, height = MIN_FACE_SIZE
        sensitivity = SENSITIVITY
        self.min_face_width = NumberOption(_("Minimum face width (px)"),
                                           width, 1, 1000, 1)
        self.min_face_height = NumberOption(_("Minimum face height (px)"),
                                            height, 1, 1000, 1)
        self.detect_inside_existing_boxes = BooleanOption(
                                       _("Detect faces inside existing boxes"),
                                       DETECT_INSIDE_EXISTING_BOXES)
        self.sensitivity = NumberOption(_("Sensitivity (1 min .. 20 max)"),
                                        sensitivity, 1, 20, 1)

        menu.add_option(category_name, "min_face_width", self.min_face_width)
        menu.add_option(category_name, "min_face_height", self.min_face_height)
        menu.add_option(category_name, "sensitivity", self.sensitivity)
        menu.add_option(category_name, "detect_inside_existing_boxes",
                        self.detect_inside_existing_boxes)

    def update_settings(self):
        global REPLACE_WITHOUT_ASKING
        global DETECT_INSIDE_EXISTING_BOXES
        global MIN_FACE_SIZE
        global SENSITIVITY
        REPLACE_WITHOUT_ASKING = self.replace_without_asking.get_value()
        DETECT_INSIDE_EXISTING_BOXES = self.detect_inside_existing_boxes.get_value()
        width = self.min_face_width.get_value()
        height = self.min_face_height.get_value()
        MIN_FACE_SIZE = (width, height)
        SENSITIVITY = self.sensitivity.get_value()
        save_config()

#-------------------------------------------------------------------------
#
# Settings Dialog
#
#-------------------------------------------------------------------------

class SettingsDialog(PluginWindows.ToolManagedWindowBase):

    def __init__(self, dbstate, uistate, title, options):
        self.dbstate = dbstate
        self.uistate = uistate
        self.title = title
        self.options = options

        PluginWindows.ToolManagedWindowBase.__init__(self, dbstate, uistate,
                                                     None, "SettingsDialog")

        self.ok.set_use_stock(True)
        self.ok.set_label("gtk-ok")

    def get_title(self):
        return self.title

    def on_ok_clicked(self, obj):
        self.options.update_settings()
        self.close()

#-------------------------------------------------------------------------
#
# Photo Tagging Gramplet
#
#-------------------------------------------------------------------------

class PhotoTaggingGramplet(Gramplet):
    def init(self):
        self.regions = []

        self.build_context_menu()

        self.gui.WIDGET = self.build_gui()
        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(self.gui.WIDGET)
        self.top.show_all()

    def on_save(self):
        CONFIG.save()

    # ======================================================
    # building the GUI
    # ======================================================

    def build_gui(self):
        """
        Build the GUI interface.
        """
        self.top = Gtk.VBox()

        hpaned = Gtk.HPaned()

        button_panel = Gtk.HBox()

        self.button_index = Gtk.ToolButton(Gtk.STOCK_INDEX)
        self.button_add = Gtk.ToolButton(Gtk.STOCK_ADD)
        self.button_del = Gtk.ToolButton(Gtk.STOCK_REMOVE)
        self.button_clear = Gtk.ToolButton(Gtk.STOCK_CLEAR)
        self.button_edit = Gtk.ToolButton(Gtk.STOCK_EDIT)
        self.button_zoom_in = Gtk.ToolButton(Gtk.STOCK_ZOOM_IN)
        self.button_zoom_out = Gtk.ToolButton(Gtk.STOCK_ZOOM_OUT)
        # set custom icon for face detect button
        self.button_detect = Gtk.ToolButton()
        theme = Gtk.IconTheme.get_default()
        face_detect_icon = theme.lookup_icon('gramps-face-detection', 24,
                                             Gtk.IconLookupFlags.FORCE_SVG)
        if face_detect_icon is not None:
            self.button_detect.set_icon_name('gramps-face-detection')
        else:
            img = Gtk.Image()
            path, filename = os.path.split(__file__)
            face_detect_icon = os.path.join(path, 'gramps-face-detection.svg')
            img.set_from_file(face_detect_icon)
            self.button_detect.set_icon_widget(img)
        self.button_settings = Gtk.ToolButton(Gtk.STOCK_PREFERENCES)

        self.button_index.connect("clicked", self.sel_person_clicked)
        self.button_add.connect("clicked", self.add_person_clicked)
        self.button_del.connect("clicked", self.clear_ref_clicked)
        self.button_clear.connect("clicked", self.del_region_clicked)
        self.button_edit.connect("clicked", self.edit_person_clicked)
        self.button_zoom_in.connect("clicked", self.zoom_in_clicked)
        self.button_zoom_out.connect("clicked", self.zoom_out_clicked)
        self.button_detect.connect("clicked", self.detect_faces_clicked)
        self.button_settings.connect("clicked", self.settings_clicked)

        button_panel.pack_start(self.button_index,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_add,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_del,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_clear,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_edit,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_zoom_in,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_zoom_out,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_detect,
                                expand=False, fill=False, padding=5)
        button_panel.pack_start(self.button_settings,
                                expand=False, fill=False, padding=5)

        self.button_index.set_tooltip_text(_("Select Person"))
        self.button_add.set_tooltip_text(_("Add Person"))
        self.button_del.set_tooltip_text(_("Clear Reference"))
        self.button_clear.set_tooltip_text(_("Remove Selection"))
        self.button_edit.set_tooltip_text(_("Edit referenced Person"))
        self.button_zoom_in.set_tooltip_text(_("Zoom In"))
        self.button_zoom_out.set_tooltip_text(_("Zoom Out"))

        if facedetection.computer_vision_available:
            text = _("Detect faces")
        else:
            text = _("Detect faces (OpenCV module required)")
        self.button_detect.set_tooltip_text(text)

        self.button_settings.set_tooltip_text(_("Settings"))

        self.top.pack_start(button_panel, expand=False, fill=True, padding=5)

        self.selection_widget = SelectionWidget()
        self.selection_widget.set_size_request(200, -1)
        self.selection_widget.connect("region-modified", self.region_modified)
        self.selection_widget.connect("region-created", self.region_created)
        self.selection_widget.connect("region-selected", self.region_selected)
        self.selection_widget.connect("selection-cleared",
                                      self.selection_cleared)
        self.selection_widget.connect("right-button-clicked",
                                      self.right_button_clicked)
        self.selection_widget.connect("zoomed-in", self.zoomed)
        self.selection_widget.connect("zoomed-out", self.zoomed)

        # Can drop a PERSON here:
        tglist = Gtk.TargetList.new([])
        tglist.add(DdTargets.PERSON_LINK.atom_drag_type,
                   DdTargets.PERSON_LINK.target_flags,
                   DdTargets.PERSON_LINK.app_id)
        # Can drop a LIST of HANDLES here:
        tglist.add(DdTargets.HANDLE_LIST.atom_drag_type,
                   DdTargets.HANDLE_LIST.target_flags,
                   DdTargets.HANDLE_LIST.app_id)

        # Drag and Drop for selection widget:
        self.selection_widget.event_box.drag_dest_set(
            Gtk.DestDefaults.MOTION |
            Gtk.DestDefaults.DROP,
            [],
            Gdk.DragAction.COPY)
        self.selection_widget.event_box.drag_dest_set_target_list(tglist)
        self.selection_widget.event_box.connect(
            'drag_data_received',
            lambda *args: self.drag_data_received(*args, on_image=True))
        # End Drag and Drop for selection widget

        hpaned.pack1(self.selection_widget, resize=True, shrink=False)

        self.treestore = Gtk.TreeStore(int, GdkPixbuf.Pixbuf, str)

        self.treeview = Gtk.TreeView(self.treestore)
        self.treeview.set_size_request(400, -1)
        self.treeview.connect("cursor-changed", self.cursor_changed)
        self.treeview.connect("row-activated", self.row_activated)
        self.treeview.connect("button-press-event", self.row_mouse_click)
        column1 = Gtk.TreeViewColumn(_(''))
        column2 = Gtk.TreeViewColumn(_('Preview'))
        column3 = Gtk.TreeViewColumn(_('Person'))
        self.treeview.append_column(column1)
        self.treeview.append_column(column2)
        self.treeview.append_column(column3)

        cell1 = Gtk.CellRendererText()
        cell2 = Gtk.CellRendererPixbuf()
        cell3 = Gtk.CellRendererText()
        column1.pack_start(cell1, expand=True)
        column1.add_attribute(cell1, 'text', 0)
        column2.pack_start(cell2, expand=True)
        column2.add_attribute(cell2, 'pixbuf', 1)
        column3.pack_start(cell3, expand=True)
        column3.add_attribute(cell3, 'text', 2)

        self.treeview.set_search_column(0)
        column1.set_sort_column_id(0)
        column3.set_sort_column_id(2)

        # Drag and Drop for tree view:
        self.treeview.drag_dest_set(Gtk.DestDefaults.MOTION |
                                    Gtk.DestDefaults.DROP,
                                    [],
                                    Gdk.DragAction.COPY)
        self.treeview.drag_dest_set_target_list(tglist)
        self.treeview.connect('drag_data_received',
                              self.drag_data_received)
        # End Drag and Drop for tree_view

        scrolled_window2 = Gtk.ScrolledWindow()
        scrolled_window2.add(self.treeview)
        scrolled_window2.set_size_request(400, -1)
        scrolled_window2.set_policy(Gtk.PolicyType.AUTOMATIC,
                                    Gtk.PolicyType.AUTOMATIC)

        hpaned.pack2(scrolled_window2, resize=False, shrink=False)

        self.top.pack_start(hpaned, True, True, 5)

        self.enable_buttons()

        return self.top

    def drag_data_received(self, widget, context, x, y,
                           sel_data, info, time, on_image=None):
        """
        Receive a dropped person onto the treeview.
        """
        if sel_data:
            pickled_data = sel_data.get_data()
            if not pickled_data:
                return
            data = pickle.loads(pickled_data)
            # Perhaps allow multiple person drops
            # Sometimes, more than one person could be in a selected area
            people = []
            # Just get the first one for now:, if a list:
            if sel_data.get_data_type() == DdTargets.HANDLE_LIST.atom_drag_type:
                if data[0][0] == "Person":
                    handle = data[0][1]
                    person = self.dbstate.db.get_person_from_handle(handle)
                    if person:
                        people.append(person)
                elif data[0][0] == "Event":
                    # get first, primary person of event:
                    event_handle = data[0][1]
                    event = self.dbstate.db.get_event_from_handle(event_handle)
                    for obj_class, handle in event.get_referenced_handles():
                        if obj_class == "Person":
                            person = self.dbstate.db.get_person_from_handle(handle)
                            if person:
                                people.append(person)
                                break
            elif sel_data.get_data_type() == DdTargets.PERSON_LINK.atom_drag_type:
                (drag_type, idval, handle, val) = data
                person = self.dbstate.db.get_person_from_handle(handle)
                if person:
                    people.append(person)
            else: # other formats work like this:
                handle = None
                try:
                    (drag_type, idval, handle, val) = data
                except:
                    pass
                if handle:
                    person = self.dbstate.db.get_person_from_handle(handle)
                    if person:
                        people.append(person)
                else:
                    LOG.warn("Can't handle this type of drop: '%s'"
                             % sel_data.get_data_type())
                    return
            for person in people:
                if on_image: # drop on image
                    region = self.selection_widget.find_region(x, y)
                    current = self.selection_widget.get_current()
                    if region and (current is None or current == region):
                        self.ask_and_set_person(region, person)
                        self.selection_widget.clear_selection()
                        self.refresh()
                        self.enable_buttons()
                else: # drop on list
                    drop_info = self.treeview.get_dest_row_at_pos(x, y)
                    if drop_info:
                        #path, position = drop_info
                        #self.treeview.set_cursor(path)
                        self.set_current_person(person)
                        self.selection_widget.clear_selection()
                        self.refresh()
                        self.enable_buttons()

    def build_context_menu(self):
        self.context_menu = Gtk.Menu()
        self.context_menu.set_reserve_toggle_size(False)

        self.context_button_active = Gtk.MenuItem.new_with_mnemonic(
                                                     _("Set as active person"))
        self.context_button_active.connect("activate", self.set_active_person)

        self.context_button_select = Gtk.MenuItem.new_with_mnemonic(_("_Select"))
        self.context_button_select.connect("activate", self.sel_person_clicked)

        self.context_button_add = Gtk.MenuItem.new_with_mnemonic(_("_Add"))
        self.context_button_add.connect("activate", self.add_person_clicked)

        self.context_button_clear = Gtk.MenuItem.new_with_mnemonic(_("_Clear"))
        self.context_button_clear.connect("activate", self.clear_ref_clicked)

        self.context_button_remove = Gtk.MenuItem.new_with_mnemonic(_("_Remove"))
        self.context_button_remove.connect("activate", self.del_region_clicked)

        self.context_menu.append(self.context_button_active)
        self.context_menu.append(self.context_button_select)
        self.context_menu.append(self.context_button_add)
        self.context_menu.append(self.context_button_clear)
        self.context_menu.append(self.context_button_remove)

        self.additional_items = []

    def refresh(self):
        self.selection_widget.refresh()
        self.refresh_list()
        self.refresh_selection()

    # ======================================================
    # gramplet event handlers
    # ======================================================

    def db_changed(self):
        self.connect(self.dbstate.db, 'media-update', self.update)
        self.connect_signal('Media', self.update)

    def main(self):
        media = self.get_current_object()
        self.top.hide()
        if media and media.mime.startswith("image"):
            self.load_image(media)
        else:
            self.selection_widget.show_missing()
        self.refresh_list()
        self.enable_buttons()
        self.top.show()

    # ======================================================
    # loading the image
    # ======================================================

    def load_image(self, media):
        self.regions = []
        image_path = media_path_full(self.dbstate.db, media.get_path())
        self.selection_widget.load_image(image_path)
        self.retrieve_backrefs()
        self.selection_widget.set_regions(self.regions)

    def retrieve_backrefs(self):
        """
        Finds the media references pointing to the current image
        """
        backrefs = self.dbstate.db.find_backlink_handles(self.get_current_handle())
        for (reftype, ref) in backrefs:
            if reftype == "Person":
                person = self.dbstate.db.get_person_from_handle(ref)
                gallery = person.get_media_list()
                for mediaref in gallery:
                    referenced_handles = mediaref.get_referenced_handles()
                    if len(referenced_handles) == 1:
                        handle_type, handle = referenced_handles[0]
                        if handle_type == "Media" and handle == self.get_current_handle():
                            rect = mediaref.get_rectangle()
                            if rect is None:
                                rect = (0, 0, 100, 100)
                            coords = self.selection_widget.proportional_to_real_rect(rect)
                            region = Region(*coords)
                            region.person = person
                            region.mediaref = mediaref
                            self.regions.append(region)

    # ======================================================
    # managing regions
    # ======================================================

    def check_and_translate_to_proportional(self, mediaref, rect):
        if mediaref:
            return mediaref.get_rectangle()
        else:
            return self.selection_widget.real_to_proportional_rect(rect)

    def intersects_any(self, region):
        for r in self.regions:
            if r.intersects(region):
                return True
        return False

    def enclosing_region(self, region):
        for r in self.regions:
            if r.contains_rect(region):
                return r
        return None

    def regions_referencing_person(self, person):
        result = []
        for r in self.regions:
            if r.person == person:
                result.append(r)
        return result

    def all_referenced_persons(self):
        result = []
        for r in self.regions:
            if r.person is not None:
                result.append(r.person)
        return result

    # ======================================================
    # utility functions for retrieving properties
    # ======================================================

    def get_current_handle(self):
        return self.get_active('Media')

    def get_current_object(self):
        try:
            return self.dbstate.db.get_media_from_handle(self.get_current_handle())
        except:
            return None

    # ======================================================
    # helpers for updating database objects
    # ======================================================

    def add_reference(self, person, rect):
        """
        Add a reference to the media object to the specified person.
        """
        mediaref = MediaRef()
        mediaref.ref = self.get_current_handle()
        mediaref.set_rectangle(rect)
        person.add_media_reference(mediaref)
        self.commit_person(person)
        return mediaref

    def remove_reference(self, person, mediaref):
        """
        Removes the reference to the media object from the person.
        """
        if mediaref in person.get_media_list():
            person.get_media_list().remove(mediaref)
            self.commit_person(person)

    def commit_person(self, person):
        """
        Save the modifications made to a Person object to the database.
        """
        with DbTxn('', self.dbstate.db) as trans:
            self.dbstate.db.commit_person(person, trans)
            msg = _("Edit Person (%s)") % name_displayer.display(person)
            trans.set_description(msg)

    # ======================================================
    # managing toolbar buttons
    # ======================================================
    def enable_buttons(self):
        selected = self.selection_widget.get_current()
        self.button_index.set_sensitive(selected is not None)
        self.button_add.set_sensitive(selected is not None)
        self.button_del.set_sensitive(
          selected is not None and
          selected.person is not None)
        self.button_clear.set_sensitive(selected is not None)
        self.button_edit.set_sensitive(
          selected is not None and
          selected.person is not None)
        self.button_zoom_in.set_sensitive(
          self.selection_widget.is_image_loaded() and
          self.selection_widget.can_zoom_in())
        self.button_zoom_out.set_sensitive(
          self.selection_widget.is_image_loaded() and
          self.selection_widget.can_zoom_out())
        self.button_detect.set_sensitive(
          self.selection_widget.is_image_loaded() and
          facedetection.computer_vision_available)

    # ======================================================
    # managing context menu buttons
    # ======================================================

    def prepare_context_menu(self):
        selected = self.selection_widget.get_current()
        has_person = selected is not None and selected.person is not None

        self.context_button_active.set_sensitive(has_person)
        self.context_button_add.set_sensitive(selected is not None)
        self.context_button_select.set_sensitive(selected is not None)
        self.context_button_clear.set_sensitive(has_person)
        self.context_button_remove.set_sensitive(selected is not None)

        # clear temporary items
        for item in self.additional_items:
            self.context_menu.remove(item)

        self.additional_items = []

        # populate the context menu
        persons = self.all_referenced_persons()
        if selected is not None and selected.person is not None:
            persons.remove(selected.person)
        if persons:
            self.additional_items.append(Gtk.SeparatorMenuItem())
            sorted_persons = sorted(list(persons), key=name_displayer.display)
            for person in sorted_persons:
                item = Gtk.MenuItem(
                    _("Replace to {0}").format(name_displayer.display(person)))
                item.connect("activate", self.replace_reference, person)
                self.additional_items.append(item)
            for item in self.additional_items:
                self.context_menu.append(item)

    def show_context_menu(self):
        """
        Show popup menu using different functions according to Gtk version.
        """
        self.prepare_context_menu()
        self.context_menu.show_all()
        if (Gtk.MAJOR_VERSION >= 3) and (Gtk.MINOR_VERSION > 22):
            self.context_menu.popup_at_pointer(None)
        else:
            self.context_menu.popup(None, None, None, None, 0, 0)

    # ======================================================
    # selection event handlers
    # ======================================================

    def region_modified(self, sender):
        region = self.selection_widget.get_current()
        person = region.person
        mediaref = region.mediaref
        if person and mediaref:
            selection = self.selection_widget.get_selection()
            rect = self.selection_widget.real_to_proportional_rect(selection)
            mediaref.set_rectangle(rect)
            self.commit_person(person)
        self.enable_buttons()
        self.refresh_list()
        self.refresh_selection()

    def region_created(self, sender):
        self.enable_buttons()
        self.refresh_list()
        self.refresh_selection()
        self.show_context_menu()

    def right_button_clicked(self, sender):
        self.show_context_menu()

    def region_selected(self, sender):
        self.enable_buttons()
        self.refresh_selection()

    def selection_cleared(self, sender):
        self.enable_buttons()
        self.refresh_selection()

    def zoomed(self, sender):
        self.enable_buttons()

    # ======================================================
    # toolbar button event handles
    # ======================================================
    def add_person_clicked(self, event):
        if self.selection_widget.get_current():
            person = Person()
            EditPerson(self.dbstate, self.uistate, self.track, person,
                       self.new_person_added)

    def sel_person_clicked(self, event):
        if self.selection_widget.get_current():
            SelectPerson = SelectorFactory('Person')
            sel = SelectPerson(self.dbstate, self.uistate, self.track,
                               _("Select Person"))
            person = sel.run()
            if person:
                self.set_current_person(person)
                self.selection_widget.clear_selection()
                self.refresh()
                self.enable_buttons()

    def del_region_clicked(self, event):
        if self.selection_widget.get_current():
            self.delete_region(self.selection_widget.get_current())
            self.selection_widget.clear_selection()
            self.refresh()
            self.enable_buttons()

    def clear_ref_clicked(self, event):
        if self.clear_ref(self.selection_widget.get_current()):
            self.refresh()

    def edit_person_clicked(self, event):
        person = self.selection_widget.get_current().person
        if person:
            EditPerson(self.dbstate, self.uistate, self.track, person)
            self.refresh()

    def zoom_in_clicked(self, event):
        self.selection_widget.zoom_in()

    def zoom_out_clicked(self, event):
        self.selection_widget.zoom_out()

    def detect_faces_clicked(self, event):
        self.uistate.push_message(self.dbstate, _("Detecting faces..."))
        media = self.get_current_object()
        image_path = media_path_full(self.dbstate.db, media.get_path())
        faces, img_size = facedetection.detect_faces(image_path, MIN_FACE_SIZE,
                                                     SENSITIVITY)
        # verify and enlarge found faces regions
        for (x, y, width, height) in faces:
            # calculate enlarged region
            new_x1 = x - width/5
            new_y1 = y - height/3
            new_x2 = x + width*6/5
            new_y2 = y + height*7/5
            # prevent overflow image size
            new_y1 = 0 if new_y1 < 0 else new_y1
            new_y2 = img_size[0] if img_size[0] < new_y2 else new_y2
            new_x1 = 0 if new_x1 < 0 else new_x1
            new_x2 = img_size[1] if img_size[1] < new_x2 else new_x2

            region = Region(new_x1, new_y1, new_x2, new_y2)

            if (DETECT_INSIDE_EXISTING_BOXES
                    or self.enclosing_region(region) is None):
                self.regions.append(region)

        self.refresh()
        self.uistate.push_message(self.dbstate, _("Detection finished"))

    def settings_clicked(self, event):
        try:
            SettingsDialog(self.gui.dbstate, self.gui.uistate,
                           _("Settings"), PhotoTaggingOptions())
        except WindowActiveError:
            pass

    def set_active_person(self, event):
        """
        Set selected person as active.
        """
        person = self.selection_widget.get_current().person
        if person:
            person_handle = person.get_handle()
            self.set_active('Person', person_handle)

    # ======================================================
    # helpers for toolbar event handlers
    # ======================================================

    def delete_region(self, region):
        self.regions.remove(region)
        if region.person is not None:
            self.remove_reference(region.person, region.mediaref)

    def delete_regions(self, regions):
        for r in regions:
            self.delete_region(r)

    def new_person_added(self, person):
        self.set_current_person(person)
        self.selection_widget.clear_selection()
        self.refresh()
        self.enable_buttons()

    def set_current_person(self, person):
        self.ask_and_set_person(self.selection_widget.get_current(), person)

    def ask_and_set_person(self, region, person):
        if region and person:
            other_references = self.regions_referencing_person(person)
            ref_count = len(other_references)
            if ref_count > 0:
                person = other_references[0].person
                if REPLACE_WITHOUT_ASKING:
                    self.delete_regions(other_references)
                else:
                    if ref_count == 1:
                        text = _("Another region of this image "
                                 "is associated with {name}. Remove it?")
                    else:
                        text = _("{count} other regions of this image "
                                 "are associated with {name}. Remove them?")
                    message = text.format(name=name_displayer.display(person),
                                          count=ref_count)
                    dialog = Gtk.MessageDialog(parent=None,
                                               type=Gtk.MessageType.QUESTION,
                                               buttons=Gtk.ButtonsType.YES_NO,
                                               message_format=message)
                    response = dialog.run()
                    dialog.destroy()
                    if response == Gtk.ResponseType.YES:
                        self.delete_regions(other_references)
            self.set_person(region, person)

    def set_person(self, region, person):
        rect = self.check_and_translate_to_proportional(region.mediaref,
                                                        region.coords())
        self.clear_ref(region)
        mediaref = self.add_reference(person, rect)
        region.person = person
        region.mediaref = mediaref

    def clear_ref(self, region):
        if region:
            if region.person:
                self.remove_reference(region.person, region.mediaref)
                region.person = None
                region.mediaref = None
                return True
        return False

    # ======================================================
    # context menu event handles
    # ======================================================

    def replace_reference(self, event, person):
        other_references = self.regions_referencing_person(person)
        self.delete_regions(other_references)
        self.set_person(self.selection_widget.get_current(), person)
        self.selection_widget.clear_selection()
        self.refresh()
        self.enable_buttons()

    # ======================================================
    # list event handles
    # ======================================================

    def cursor_changed(self, treeview):
        selected = self.get_selected_region()
        self.selection_widget.select(selected)
        self.enable_buttons()

    def row_activated(self, treeview, path, view_column):
        self.edit_person_clicked(None)

    def row_mouse_click(self, treeview, event):
        """
        Handle right mouse click on treeview.
        Show popup menu for row the same as for region.
        """
        button = event.get_button()[1]
        # right mouse button
        if button == 3:
            # change cursor position to apply row selection
            pthinfo = self.treeview.get_path_at_pos(event.x, event.y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                self.treeview.grab_focus()
                self.treeview.set_cursor(path, col, 0)
                self.show_context_menu()

    # ======================================================
    # helpers for list event handlers
    # ======================================================

    def get_selected_region(self):
        selection = self.treeview.get_selection()
        if selection:
            (model, pathlist) = selection.get_selected_rows()
            for path in pathlist:
                tree_iter = model.get_iter(path)
                i = model.get_value(tree_iter, 0)
                try:
                    return self.regions[i - 1]
                except:
                    return None
        return None

    # ======================================================
    # refreshing the list
    # ======================================================

    def refresh_list(self):
        self.treestore.clear()
        for (i, region) in enumerate(self.regions, start=1):
            name = name_displayer.display(region.person) if region.person else ""
            thumbnail = self.selection_widget.get_thumbnail(region,
                                                            THUMBNAIL_IMAGE_SIZE)
            self.treestore.append(None, (i, thumbnail, name))

    def refresh_selection(self):
        current = self.selection_widget.get_current()
        selection = self.treeview.get_selection()
        if current and current in self.regions:
            selection.select_path(self.regions.index(current),)
        else:
            selection.unselect_all()
