# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2009  Douglas S. Blank <doug.blank@gmail.com>
# Copyright (C) 2011       Gary Burton
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

# $Id$

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.plug import Gramplet
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.utils.db import get_birth_or_fallback, get_death_or_fallback
from gramps.gen.datehandler import get_date, parser
from gramps.gen.errors import WindowActiveError
from gramps.gen.lib import (Person, FamilyRelType, Family, ChildRef, Place,
                            Event, EventType, EventRef, Source, Citation,
                            Name, NameType, Surname)
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.db import DbTxn
import gramps.gen.lib

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

#------------------------------------------------------------------------
#
# Gramplet class
#
#------------------------------------------------------------------------
class DataEntryGramplet(Gramplet):
    NO_REL     = 0
    AS_PARENT  = 1
    AS_MOTHER  = 2
    AS_FATHER  = 3
    AS_SPOUSE  = 4
    AS_WIFE    = 5
    AS_HUSBAND = 6
    AS_SIBLING = 7
    AS_CHILD   = 8
    def init(self):
        self.de_column_width = 20
        self.de_source_width = 10
        self.show_source = True
        from gi.repository import Gtk
        rows = Gtk.VBox()
        self._dirty = False
        self._dirty_person = None
        self._dirty_family = None
        self.de_widgets = {}
        for items in [("Active person", _("Active person"), None, True,
                       [("Edit person", "", "button", self.edit_person),
                        ("Edit family", _("Family:"), "button", self.edit_family),
                        ("Show sources", _("Sources?"), "checkbox", self.toggle_sources)],
                       False, 0, None),
                      ("APName", _("Surname, Given"), None, False, [], True, 0, None),
                      ("APGender", _("Gender"), [_("female"), _("male"), _("unknown"), _("other")],
                       False, [], True, 2, (_("Source"),
                                            "APSource")),
                      ("APBirth", _("Birth"), None, False, [], True, 0, (_("Source"), "APBirthSource")),
                      ("APDeath", _("Death"), None, False, [], True, 0, (_("Source"), "APDeathSource"))
                     ]:
            pos, text, choices, readonly, callback, dirty, default, source = items
            row = self.make_row(pos, text, choices, readonly, callback, dirty, default, source)
            rows.pack_start(row, False, False, 0)

        # Save and Abandon
        row = Gtk.HBox()
        button = Gtk.Button(_("Save"))
        button.connect("clicked", self.save_data_edit)
        row.pack_start(button, True, True, 0)
        button = Gtk.Button(_("Abandon"))
        button.connect("clicked", self.abandon_data_edit)
        row.pack_start(button, True, True, 0)
        rows.pack_start(row, False, False, 0)

        for items in [("New person", _("New person"), None, True, 0, None),
                      ("NPRelation", _("Add relation"),
                       [_("No relation to active person"),
                        _("Add as a Parent"),
                        _("Add as a Mother"),
                        _("Add as a Father"),
                        _("Add as a Spouse"),
                        _("Add as a Wife"),
                        _("Add as a Husband"),
                        _("Add as a Sibling"),
                        _("Add as a Child")],
                       False, 0, None),
                      ("NPName", _("Surname, Given"), None, False, 0, None),
                      ("NPGender", _("Gender"),
                       [_("female"), _("male"), _("unknown"), _("other")], False, 2, (_("Source"), "NPSource")),
                      ("NPBirth", _("Birth"), None, False, 0, (_("Source"), "NPBirthSource")),
                      ("NPDeath", _("Death"), None, False, 0, (_("Source"), "NPDeathSource"))
                     ]:
            pos, text, choices, readonly, default, source = items
            row = self.make_row(pos, text, choices, readonly, default=default, source=source)
            rows.pack_start(row, False, False, 0)

        # Save, Abandon, Clear
        row = Gtk.HBox()
        button = Gtk.Button(_("Add"))
        button.connect("clicked", self.add_data_entry)
        row.pack_start(button, True, True, 0)
        button = Gtk.Button(_("Copy Active Data"))
        button.connect("clicked", self.copy_data_entry)
        row.pack_start(button, True, True, 0)
        button = Gtk.Button(_("Clear"))
        button.connect("clicked", self.clear_data_entry)
        row.pack_start(button, True, True, 0)
        rows.pack_start(row, False, False, 0)

        self.gui.get_container_widget().remove(self.gui.textview)
        self.gui.get_container_widget().add_with_viewport(rows)
        rows.show_all()
        self.clear_data_entry(None)

    def main(self): # return false finishes
        if self._dirty:
            return
        self.de_widgets["Active person:Edit family"].hide()
        self.de_widgets["Active person:Edit family:Label"].hide()
        active_person = self.get_active_object("Person")
        self._dirty_person = active_person
        self._dirty_family = None
        if active_person:
            self.de_widgets["Active person:Edit person"].show()
            self.de_widgets["Active person:Edit family"].hide()
            self.de_widgets["Active person:Edit family:Label"].hide()
            # Fill in current person edits:
            name = name_displayer.display(active_person)
            self.de_widgets["Active person"].set_text("<i>%s</i> " % name)
            self.de_widgets["Active person"].set_use_markup(True)
            # Name:
            name_obj = active_person.get_primary_name()
            if name_obj:
                self.de_widgets["APName"].set_text("%s, %s" %
                   (name_obj.get_surname(), name_obj.get_first_name()))
            self.de_widgets["APGender"].set_active(active_person.get_gender()) # gender
            # Birth:
            birth = get_birth_or_fallback(self.dbstate.db, active_person)
            birth_text = ""
            if birth:
                sdate = get_date(birth)
                birth_text += sdate + " "
                place_text = place_displayer.display_event(self.dbstate.db, birth)
                if place_text:
                    birth_text += _("in") + " " + place_text

            self.de_widgets["APBirth"].set_text(birth_text)
            # Death:
            death = get_death_or_fallback(self.dbstate.db, active_person)
            death_text = ""
            if death:
                sdate = get_date(death)
                death_text += sdate + " "
                place_text = place_displayer.display_event(self.dbstate.db, death)
                if place_text:
                    death_text += _("in") + " " + place_text
            self.de_widgets["APDeath"].set_text(death_text)
            family_list = active_person.get_family_handle_list()
            if len(family_list) > 0:
                self._dirty_family = self.dbstate.db.get_family_from_handle(family_list[0])
                self.de_widgets["Active person:Edit family"].show()
                self.de_widgets["Active person:Edit family:Label"].show()
            else:
                family_list = active_person.get_parent_family_handle_list()
                if len(family_list) > 0:
                    self._dirty_family = self.dbstate.db.get_family_from_handle(family_list[0])
                    self.de_widgets["Active person:Edit family"].show()
                    self.de_widgets["Active person:Edit family:Label"].show()
            # lookup sources:
            self.de_widgets["APSource"].set_text(self.get_last_source_title(active_person))
            self.de_widgets["APBirthSource"].set_text(self.get_last_source_title(birth))
            self.de_widgets["APDeathSource"].set_text(self.get_last_source_title(death))
        else:
            self.clear_data_edit(None)
            self.de_widgets["Active person:Edit person"].hide()
            self.de_widgets["Active person:Edit family"].hide()
            self.de_widgets["Active person:Edit family:Label"].hide()
        self._dirty = False

    def make_row(self, pos, text, choices=None, readonly=False, callback_list=[],
                 mark_dirty=False, default=0, source=None):
        from gi.repository import Gtk
        # Data Entry: Active Person
        row = Gtk.HBox()
        label = Gtk.Label()
        if readonly:
            label.set_text("<b>%s</b>" % text)
            label.set_width_chars(self.de_column_width)
            label.set_use_markup(True)
            self.de_widgets[pos] = Gtk.Label()
            self.de_widgets[pos].set_alignment(0.0, 0.5)
            self.de_widgets[pos].set_use_markup(True)
            label.set_alignment(0.0, 0.5)
            row.pack_start(label, False, False, 0)
            row.pack_start(self.de_widgets[pos], False, False, 0)
        else:
            label.set_text("%s: " % text)
            label.set_width_chars(self.de_column_width)
            label.set_alignment(1.0, 0.5)
            if choices == None:
                self.de_widgets[pos] = Gtk.Entry()
                if mark_dirty:
                    self.de_widgets[pos].connect("changed", self.mark_dirty)
                row.pack_start(label, False, False, 0)
                row.pack_start(self.de_widgets[pos], True, True, 0)
            else:
                eventBox = Gtk.EventBox()
                self.de_widgets[pos] = Gtk.ComboBoxText()
                eventBox.add(self.de_widgets[pos])
                for add_type in choices:
                    self.de_widgets[pos].append_text(add_type)
                self.de_widgets[pos].set_active(default)
                if mark_dirty:
                    self.de_widgets[pos].connect("changed", self.mark_dirty)
                row.pack_start(label, False, False, 0)
                row.pack_start(eventBox, True, True, 0)
            if source:
                label = Gtk.Label()
                label.set_text("%s: " % source[0])
                label.set_width_chars(self.de_source_width)
                label.set_alignment(1.0, 0.5)
                self.de_widgets[source[1] + ":Label"] = label
                self.de_widgets[source[1]] = Gtk.Entry()
                if mark_dirty:
                    self.de_widgets[source[1]].connect("changed", self.mark_dirty)
                row.pack_start(label, False, False, 0)
                row.pack_start(self.de_widgets[source[1]], True, True, 0)
                if not self.show_source:
                    self.de_widgets[source[1]].hide()
        for name, text, cbtype, callback in callback_list:
            if cbtype == "button":
                label = Gtk.Label()
                label.set_text(text)
                self.de_widgets[pos + ":" + name + ":Label"] = label
                row.pack_start(label, False, False, 0)
                icon = Gtk.STOCK_EDIT
                size = Gtk.IconSize.MENU
                button = Gtk.Button()
                image = Gtk.Image()
                image.set_from_stock(icon, size)
                button.add(image)
                button.set_relief(Gtk.ReliefStyle.NONE)
                button.connect("clicked", callback)
                self.de_widgets[pos + ":" + name] = button
                row.pack_start(button, False, False, 0)
            elif cbtype == "checkbox":
                button = Gtk.CheckButton(text)
                button.set_active(True)
                button.connect("clicked", callback)
                self.de_widgets[pos + ":" + name] = button
                row.pack_start(button, False, False, 0)
        row.show_all()
        return row

    def mark_dirty(self, obj):
        self._dirty = True

    def abandon_data_edit(self, obj):
        self._dirty = False
        self.update()

    def edit_callback(self, person):
        self._dirty = False
        self.update()

    def edit_person(self, obj):
        if self._dirty_person:
            from gramps.gui.editors import EditPerson
            try:
                EditPerson(self.gui.dbstate,
                           self.gui.uistate, [],
                           self._dirty_person,
                           callback=self.edit_callback)
            except WindowActiveError:
                pass
        else:
            return

    def edit_family(self, obj):
        if self._dirty_family:
            from gramps.gui.editors import EditFamily
            try:
                EditFamily(self.gui.dbstate,
                           self.gui.uistate, [],
                           self._dirty_family)
            except WindowActiveError:
                pass
        else:
            return

    def process_dateplace(self, text):
        if text == "": return None, None
        prep_in = _("in") # word or phrase that separates date from place
        text = text.strip()
        if (" %s "  % prep_in) in text:
            date, place = text.split((" %s "  % prep_in), 1)
        elif text.startswith("%s "  % prep_in):
            date, place = text.split(("%s "  % prep_in), 1)
        else:
            date, place = text, ""
        date = date.strip()
        place = place.strip()
        if date != "":
            date = parser.parse(date)
        else:
            date = None
        if place != "":
            newq, place = self.get_or_create_place(place)
        else:
            place = None
        return date, place

    def get_or_create_place(self, place_name):
        if place_name == "": return (-1, None)
        place_list = self.dbstate.db.get_place_handles()
        for place_handle in place_list:
            place = self.dbstate.db.get_place_from_handle(place_handle)
            place_title = place_displayer.display(self.dbstate.db, place)
            if place_title.strip() == place_name:
                return (0, place) # (old, object)
        place = Place()
        place.set_title(place_name)
        self.dbstate.db.add_place(place,self.trans)
        return (1, place) # (new, object)

    def get_or_create_event(self, object, type, date, place):
        """ Add or find a type event on object """
        if date == place == None: return (-1, None)
        # first, see if it exists
        ref_list = object.get_event_ref_list()
        # look for a match, and possible correction
        for ref in ref_list:
            event = self.dbstate.db.get_event_from_handle(ref.ref)
            if event is not None:
                if int(event.get_type()) == type:
                    # Match! Let's update
                    if date:
                        event.set_date_object(date)
                    if place:
                        event.set_place_handle(place.get_handle())
                    self.dbstate.db.commit_event(event, self.trans)
                    return (0, event)
        # else create it:
        event = Event()
        if type:
            event.set_type(EventType(type))
        if date:
            event.set_date_object(date)
        if place:
            event.set_place_handle(place.get_handle())
        self.dbstate.db.add_event(event, self.trans)
        return (1, event)

    def get_or_create_source(self, source_text):
        source_list = self.dbstate.db.get_source_handles()
        for source_handle in source_list:
            source = self.dbstate.db.get_source_from_handle(source_handle)
            if source.get_title() == source_text:
                return (0, source)
        source = Source()
        source.set_title(source_text)
        self.dbstate.db.add_source(source, self.trans)
        return (1, source)

    def get_last_source_title(self, obj):
        if obj:
            citation_list = obj.get_citation_list()
            if len(citation_list) > 0:
                citation_handle = citation_list[-1]
                citation = self.dbstate.db.get_citation_from_handle(citation_handle)
                if citation:
                    source = self.dbstate.db.get_source_from_handle(citation.source_handle)
                    if source:
                        return source.get_title()
        return ""

    def make_event(self, type, date, place):
        if date == place == None: return None
        event = Event()
        event.set_type(EventType(type))
        if date:
            event.set_date_object(date)
        if place:
            event.set_place_handle(place.get_handle())
        self.dbstate.db.add_event(event, self.trans)
        return event

    def make_person(self, firstname, surname, gender):
        person = Person()
        name = Name()
        name.set_type(NameType(NameType.BIRTH))
        name.set_first_name(firstname)
        surname_obj = Surname()
        surname_obj.set_surname(surname)
        name.set_surname_list([surname_obj])
        name.set_primary_surname(0)
        person.set_primary_name(name)
        person.set_gender(gender)
        return person

    def save_data_edit(self, obj):
        if self._dirty:
            # Save the edits ----------------------------------
            person = self._dirty_person
            # First, get the data:
            gender = self.de_widgets["APGender"].get_active()
            if "," in self.de_widgets["APName"].get_text():
                surname, firstname = self.de_widgets["APName"].get_text().split(",", 1)
            else:
                surname, firstname = self.de_widgets["APName"].get_text(), ""
            surname = surname.strip()
            firstname = firstname.strip()
            if person:
                name = person.get_primary_name()
            else:
                return
            # Now, edit it:
            with DbTxn(_("Gramplet Data Edit: %s") %  name_displayer.display(person), self.dbstate.db) as self.trans:
                surname_obj = name.get_primary_surname()
                surname_obj.set_surname(surname)
                name.set_first_name(firstname)
                person.set_gender(gender)
                birthdate, birthplace = self.process_dateplace(self.de_widgets["APBirth"].get_text().strip())
                new, birthevent = self.get_or_create_event(person, EventType.BIRTH, birthdate, birthplace)
                # reference it, if need be:
                birthref = person.get_birth_ref()
                if birthevent:
                    if birthref is None:
                        # need new
                        birthref = EventRef()
                    birthref.set_reference_handle(birthevent.get_handle())
                    person.set_birth_ref(birthref)
                    # Only add if there is an event:
                    source_text = self.de_widgets["APBirthSource"].get_text().strip()
                    if source_text and self.de_widgets["Active person:Show sources"].get_active():
                        new, source = self.get_or_create_source(source_text)
                        self.add_source(birthevent, source)
                        self.dbstate.db.commit_event(birthevent, self.trans)
                deathdate, deathplace = self.process_dateplace(self.de_widgets["APDeath"].get_text().strip())
                new, deathevent = self.get_or_create_event(person, EventType.DEATH, deathdate, deathplace)
                # reference it, if need be:
                deathref = person.get_death_ref()
                if deathevent:
                    if deathref is None:
                        # need new
                        deathref = EventRef()
                    deathref.set_reference_handle(deathevent.get_handle())
                    person.set_death_ref(deathref)
                    # Only add if there is an event:
                    source_text = self.de_widgets["APDeathSource"].get_text().strip()
                    if source_text and self.de_widgets["Active person:Show sources"].get_active():
                        new, source = self.get_or_create_source(source_text)
                        self.add_source(deathevent, source)
                        self.dbstate.db.commit_event(deathevent, self.trans)
                source_text = self.de_widgets["APSource"].get_text().strip()
                if source_text and self.de_widgets["Active person:Show sources"].get_active():
                    new, source = self.get_or_create_source(source_text)
                    self.add_source(person, source)
                self.dbstate.db.commit_person(person,self.trans)
        self._dirty = False
        self.update()

    def add_source(self, obj, source):
        found = 0
        for handle in obj.get_citation_list():
            citation = self.dbstate.db.get_citation_from_handle(handle)
            if citation.get_reference_handle() == source.get_handle():
                found = 1
                break
        if not found:
            citation = Citation()
            citation.set_reference_handle(source.get_handle())
            self.dbstate.db.add_citation(citation, self.trans)
        obj.add_citation(citation.get_handle())

    def add_data_entry(self, obj):
        from gramps.gui.dialog import ErrorDialog
        # First, get the data:
        if "," in self.de_widgets["NPName"].get_text():
            surname, firstname = self.de_widgets["NPName"].get_text().split(",", 1)
        else:
            surname, firstname = self.de_widgets["NPName"].get_text(), ""
        surname = surname.strip()
        firstname = firstname.strip()
        gender = self.de_widgets["NPGender"].get_active()
        if self._dirty:
            current_person = self._dirty_person
        else:
            current_person = self.get_active_object("Person")
        # Pre-check to make sure everything is ok: -------------------------------------------
        if surname == "" and firstname == "":
            ErrorDialog(_("Please provide a name."), _("Can't add new person."))
            return
        if self.de_widgets["NPRelation"].get_active() == self.NO_REL:
            # "No relation to active person"
            pass
        elif self.de_widgets["NPRelation"].get_active() == self.AS_PARENT:
            # "Add as a Parent"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a parent."))
                return
            elif gender == Person.UNKNOWN: # unknown
                ErrorDialog(_("Please set the new person's gender."), _("Can't add new person as a parent."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_MOTHER:
            # "Add as a Mother"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a mother."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_FATHER:
            # "Add as a Father"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a father."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_SPOUSE:
            # "Add as a Spouse"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a spouse."))
                return
            elif (gender == Person.UNKNOWN and
                  current_person.get_gender() == Person.UNKNOWN): # both genders unknown
                ErrorDialog(_("Please set the new person's gender."), _("Can't add new person as a spouse."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_WIFE:
            # "Add as a Wife"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a wife."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_HUSBAND:
            # "Add as a Husband"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a husband."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_SIBLING:
            # "Add as a Sibling"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a sibling."))
                return
        elif self.de_widgets["NPRelation"].get_active() == self.AS_CHILD:
            # "Add as a Child"
            if current_person == None:
                ErrorDialog(_("Please set an active person."), _("Can't add new person as a child."))
                return
        # Start the transaction: ------------------------------------------------------------
        person = self.make_person(firstname, surname, gender)
        with DbTxn(_("Gramplet Data Edit: %s") %  name_displayer.display(person), self.dbstate.db) as self.trans:
            # New person --------------------------------------------------
            # Add birth
            new_birth_date, new_birth_place = self.process_dateplace(self.de_widgets["NPBirth"].get_text().strip())
            birth_event = self.make_event(EventType.BIRTH, new_birth_date, new_birth_place)
            if birth_event:
                # Only add if there is an event:
                source_text = self.de_widgets["NPBirthSource"].get_text().strip()
                if source_text and self.de_widgets["Active person:Show sources"].get_active():
                    new, source = self.get_or_create_source(source_text)
                    self.add_source(birth_event, source)
                    self.dbstate.db.commit_event(birth_event, self.trans)
            # Add death
            new_death_date, new_death_place = self.process_dateplace(self.de_widgets["NPDeath"].get_text())
            death_event = self.make_event(EventType.DEATH, new_death_date, new_death_place)
            if death_event:
                # Only add if there is an event:
                source_text = self.de_widgets["NPDeathSource"].get_text().strip()
                if source_text and self.de_widgets["Active person:Show sources"].get_active():
                    new, source = self.get_or_create_source(source_text)
                    self.add_source(death_event, source)
                    self.dbstate.db.commit_event(death_event, self.trans)
            # Now, create the person and events:
            # New birth for person:
            if birth_event:
                birth_ref = EventRef()
                birth_ref.set_reference_handle(birth_event.get_handle())
                person.set_birth_ref(birth_ref)
            # New death for person:
            if death_event:
                death_ref = EventRef()
                death_ref.set_reference_handle(death_event.get_handle())
                person.set_death_ref(death_ref)
            # Need to add here to get a handle:
            self.dbstate.db.add_person(person, self.trans)
            # All error checking done; just add relation:
            if self.de_widgets["NPRelation"].get_active() == self.NO_REL:
                # "No relation to active person"
                current_person = None
            elif self.de_widgets["NPRelation"].get_active() == self.AS_PARENT:
                # "Add as a Parent"
                # Go through current_person parent families
                added = False
                for family_handle in current_person.get_parent_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        # find one that person would fit as a parent
                        fam_husband_handle = family.get_father_handle()
                        fam_wife_handle = family.get_mother_handle()
                        # can we add person as wife?
                        if fam_wife_handle == None and person.get_gender() == Person.FEMALE:
                            # add the person
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                        elif fam_husband_handle == None and person.get_gender() == Person.MALE:
                            # add the person
                            family.set_father_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    if person.get_gender() == Person.MALE:
                        family.set_father_handle(person.get_handle())
                    elif person.get_gender() == Person.FEMALE:
                        family.set_mother_handle(person.get_handle())
                    family.set_relationship(FamilyRelType.MARRIED)
                    # add curent_person as child
                    childref = ChildRef()
                    childref.set_reference_handle(current_person.get_handle())
                    family.add_child_ref( childref)
                    current_person.add_parent_family_handle(family.get_handle())
                    # finalize
                    person.add_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_MOTHER:
                # "Add as a Mother"
                # Go through current_person parent families
                added = False
                for family_handle in current_person.get_parent_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        fam_wife_handle = family.get_mother_handle()
                        # can we add person as mother?
                        if fam_wife_handle == None:
                            # add the person
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    family.set_mother_handle(person.get_handle())
                    family.set_relationship(FamilyRelType.MARRIED)
                    # add curent_person as child
                    childref = ChildRef()
                    childref.set_reference_handle(current_person.get_handle())
                    family.add_child_ref( childref)
                    current_person.add_parent_family_handle(family.get_handle())
                    # finalize
                    person.add_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_FATHER:
                # "Add as a Father"
                # Go through current_person parent families
                added = False
                for family_handle in current_person.get_parent_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        fam_husband_handle = family.get_father_handle()
                        # can we add person as father?
                        if fam_husband_handle == None:
                            # add the person
                            family.set_father_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    family.set_father_handle(person.get_handle())
                    family.set_relationship(FamilyRelType.MARRIED)
                    # add curent_person as child
                    childref = ChildRef()
                    childref.set_reference_handle(current_person.get_handle())
                    family.add_child_ref( childref)
                    current_person.add_parent_family_handle(family.get_handle())
                    # finalize
                    person.add_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_SPOUSE:
                # "Add as a Spouse"
                added = False
                family = None
                for family_handle in current_person.get_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        fam_husband_handle = family.get_father_handle()
                        fam_wife_handle = family.get_mother_handle()
                        if current_person.get_handle() == fam_husband_handle:
                            # can we add person as wife?
                            if fam_wife_handle == None:
                                if person.get_gender() == Person.FEMALE:
                                    # add the person
                                    family.set_mother_handle(person.get_handle())
                                    family.set_relationship(FamilyRelType.MARRIED)
                                    person.add_family_handle(family.get_handle())
                                    added = True
                                    break
                                elif person.get_gender() == Person.UNKNOWN:
                                    family.set_mother_handle(person.get_handle())
                                    family.set_relationship(FamilyRelType.MARRIED)
                                    person.set_gender(Person.FEMALE)
                                    self.de_widgets["NPGender"].set_active(Person.FEMALE)
                                    person.add_family_handle(family.get_handle())
                                    added = True
                                    break
                        elif current_person.get_handle() == fam_wife_handle:
                            # can we add person as husband?
                            if fam_husband_handle == None:
                                if person.get_gender() == Person.MALE:
                                    # add the person
                                    family.set_father_handle(person.get_handle())
                                    family.set_relationship(FamilyRelType.MARRIED)
                                    person.add_family_handle(family.get_handle())
                                    added = True
                                    break
                                elif person.get_gender() == Person.UNKNOWN:
                                    family.set_father_handle(person.get_handle())
                                    family.set_relationship(FamilyRelType.MARRIED)
                                    person.add_family_handle(family.get_handle())
                                    person.set_gender(Person.MALE)
                                    self.de_widgets["NPGender"].set_active(Person.MALE)
                                    added = True
                                    break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    if person.get_gender() == Person.UNKNOWN:
                        if current_person is None:
                            ErrorDialog(_("Please set Active person."),
                                        _("Can't add new person as a spouse to no one."))
                            return
                        elif current_person.get_gender() == Person.UNKNOWN:
                            ErrorDialog(_("Please set gender on Active or new person."),
                                        _("Can't add new person as a spouse."))
                            return
                        elif current_person.get_gender() == Person.MALE:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(current_person.get_handle())
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.set_gender(Person.FEMALE)
                            self.de_widgets["NPGender"].set_active(Person.FEMALE)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                        elif current_person.get_gender() == Person.FEMALE:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(person.get_handle())
                            family.set_mother_handle(current_person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.set_gender(Person.MALE)
                            self.de_widgets["NPGender"].set_active(Person.MALE)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                    elif person.get_gender() == Person.MALE:
                        if current_person.get_gender() == Person.UNKNOWN:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(person.get_handle())
                            family.set_mother_handle(current_person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            current_person.set_gender(Person.FEMALE)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                        elif current_person.get_gender() == Person.MALE:
                            ErrorDialog(_("Same genders on Active and new person."),
                                        _("Can't add new person as a spouse."))
                            return
                        elif current_person.get_gender() == Person.FEMALE:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(person.get_handle())
                            family.set_mother_handle(current_person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                    elif person.get_gender() == Person.FEMALE:
                        if current_person.get_gender() == Person.UNKNOWN:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(current_person.get_handle())
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(FamilyRelType.MARRIED)
                            current_person.set_gender(gramps.gen.lib.Person.MALE)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                        elif current_person.get_gender() == Person.MALE:
                            family = Family()
                            self.dbstate.db.add_family(family, self.trans)
                            family.set_father_handle(current_person.get_handle())
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(gramps.gen.lib.FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            current_person.add_family_handle(family.get_handle())
                            self.dbstate.db.commit_family(family, self.trans)
                        elif current_person.get_gender() == Person.FEMALE:
                            ErrorDialog(_("Same genders on Active and new person."),
                                        _("Can't add new person as a spouse."))
                            return
            elif self.de_widgets["NPRelation"].get_active() == self.AS_WIFE:
                # "Add as a Wife"
                added = False
                family = None
                for family_handle in current_person.get_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        fam_wife_handle = family.get_mother_handle()
                        # can we add person as wife?
                        if fam_wife_handle == None:
                            # add the person
                            family.set_mother_handle(person.get_handle())
                            family.set_relationship(gramps.gen.lib.FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    family.set_mother_handle(person.get_handle())
                    family.set_father_handle(current_person.get_handle())
                    family.set_relationship(gramps.gen.lib.FamilyRelType.MARRIED)
                    person.add_family_handle(family.get_handle())
                    current_person.add_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_HUSBAND:
                # "Add as a Husband"
                added = False
                family = None
                for family_handle in current_person.get_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        fam_husband_handle = family.get_father_handle()
                        # can we add person as husband?
                        if fam_husband_handle == None:
                            # add the person
                            family.set_father_handle(person.get_handle())
                            family.set_relationship(gramps.gen.lib.FamilyRelType.MARRIED)
                            person.add_family_handle(family.get_handle())
                            added = True
                            break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    family.set_father_handle(person.get_handle())
                    family.set_mother_handle(current_person.get_handle())
                    family.set_relationship(gramps.gen.lib.FamilyRelType.MARRIED)
                    person.add_family_handle(family.get_handle())
                    current_person.add_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_SIBLING and current_person is not None:
                # "Add as a Sibling"
                added = False
                for family_handle in current_person.get_parent_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        childref = ChildRef()
                        childref.set_reference_handle(person.get_handle())
                        family.add_child_ref( childref)
                        person.add_parent_family_handle(family.get_handle())
                        added = True
                        break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    family = Family()
                    self.dbstate.db.add_family(family, self.trans)
                    childref = ChildRef()
                    childref.set_reference_handle(person.get_handle())
                    family.add_child_ref( childref)
                    childref = ChildRef()
                    childref.set_reference_handle(current_person.get_handle())
                    family.add_child_ref( childref)
                    person.add_parent_family_handle(family.get_handle())
                    current_person.add_parent_family_handle(family.get_handle())
                    self.dbstate.db.commit_family(family, self.trans)
            elif self.de_widgets["NPRelation"].get_active() == self.AS_CHILD and current_person is not None:
                # "Add as a Child"
                added = False
                family = None
                for family_handle in current_person.get_family_handle_list():
                    family = self.dbstate.db.get_family_from_handle(family_handle)
                    if family:
                        childref = ChildRef()
                        childref.set_reference_handle(person.get_handle())
                        family.add_child_ref( childref)
                        person.add_parent_family_handle(family.get_handle())
                        added = True
                        break
                if added:
                    self.dbstate.db.commit_family(family, self.trans)
                else:
                    if current_person.get_gender() == Person.UNKNOWN:
                        ErrorDialog(_("Please set gender on Active person."),
                                    _("Can't add new person as a child."))
                        return
                    else:
                        family = Family()
                        self.dbstate.db.add_family(family, self.trans)
                        childref = ChildRef()
                        childref.set_reference_handle(person.get_handle())
                        family.add_child_ref( childref)
                        person.add_parent_family_handle(family.get_handle())
                        current_person.add_family_handle(family.get_handle())
                        if Person.FEMALE:
                            family.set_mother_handle(current_person.get_handle())
                        else:
                            family.set_father_handle(current_person.get_handle())
                        self.dbstate.db.commit_family(family, self.trans)
            # Commit changes -------------------------------------------------
            if current_person: # if related to current person
                self.dbstate.db.commit_person(current_person, self.trans)
            if person:
                source_text = self.de_widgets["NPSource"].get_text().strip()
                if source_text and self.de_widgets["Active person:Show sources"].get_active():
                    new, source = self.get_or_create_source(source_text)
                    self.add_source(person, source)
                self.dbstate.db.commit_person(person, self.trans)

    def copy_data_entry(self, obj):
        self.de_widgets["NPName"].set_text(self.de_widgets["APName"].get_text())
        self.de_widgets["NPBirth"].set_text(self.de_widgets["APBirth"].get_text())
        self.de_widgets["NPDeath"].set_text(self.de_widgets["APDeath"].get_text())
        self.de_widgets["NPGender"].set_active(self.de_widgets["APGender"].get_active())
        self.de_widgets["NPSource"].set_text(self.de_widgets["APSource"].get_text())
        self.de_widgets["NPBirthSource"].set_text(self.de_widgets["APBirthSource"].get_text())
        self.de_widgets["NPDeathSource"].set_text(self.de_widgets["APDeathSource"].get_text())
        self.de_widgets["NPSource"].set_text(self.de_widgets["APSource"].get_text())
        self.de_widgets["NPBirthSource"].set_text(self.de_widgets["APBirthSource"].get_text())
        self.de_widgets["NPDeathSource"].set_text(self.de_widgets["APDeathSource"].get_text())
        # FIXME: put cursor in add surname

    def clear_data_edit(self, obj):
        self.de_widgets["Active person"].set_text("")
        self.de_widgets["APName"].set_text("")
        self.de_widgets["APBirth"].set_text("")
        self.de_widgets["APDeath"].set_text("")
        self.de_widgets["APGender"].set_active(Person.UNKNOWN)
        self.de_widgets["APSource"].set_text("")
        self.de_widgets["APBirthSource"].set_text("")
        self.de_widgets["APDeathSource"].set_text("")

    def clear_data_entry(self, obj):
        self.de_widgets["NPName"].set_text("")
        self.de_widgets["NPBirth"].set_text("")
        self.de_widgets["NPDeath"].set_text("")
        self.de_widgets["NPRelation"].set_active(self.NO_REL)
        self.de_widgets["NPGender"].set_active(Person.UNKNOWN)
        self.de_widgets["NPSource"].set_text("")
        self.de_widgets["NPBirthSource"].set_text("")
        self.de_widgets["NPDeathSource"].set_text("")

    def db_changed(self):
        """
        If person or family changes, the relatives of active person might have
        changed
        """
        self.connect(self.dbstate.db, 'person-add', self.update)
        self.connect(self.dbstate.db, 'person-delete', self.update)
        self.connect(self.dbstate.db, 'person-update', self.update)
        self.connect(self.dbstate.db, 'family-add', self.update)
        self.connect(self.dbstate.db, 'family-delete', self.update)
        self.connect(self.dbstate.db, 'person-rebuild', self.update)
        self.connect(self.dbstate.db, 'family-rebuild', self.update)
        self._dirty = False
        self._dirty_person = None
        self.clear_data_entry(None)

    def active_changed(self, handle):
        self.update()

    def toggle_sources(self, widget):
        if widget.get_active():
            self.de_widgets["NPSource"].show()
            self.de_widgets["NPBirthSource"].show()
            self.de_widgets["NPDeathSource"].show()
            self.de_widgets["APSource"].show()
            self.de_widgets["APBirthSource"].show()
            self.de_widgets["APDeathSource"].show()
            # Labels:
            self.de_widgets["NPSource:Label"].show()
            self.de_widgets["NPBirthSource:Label"].show()
            self.de_widgets["NPDeathSource:Label"].show()
            self.de_widgets["APSource:Label"].show()
            self.de_widgets["APBirthSource:Label"].show()
            self.de_widgets["APDeathSource:Label"].show()
        else:
            self.de_widgets["NPSource"].hide()
            self.de_widgets["NPBirthSource"].hide()
            self.de_widgets["NPDeathSource"].hide()
            self.de_widgets["APSource"].hide()
            self.de_widgets["APBirthSource"].hide()
            self.de_widgets["APDeathSource"].hide()
            # Labels:
            self.de_widgets["NPSource:Label"].hide()
            self.de_widgets["NPBirthSource:Label"].hide()
            self.de_widgets["NPDeathSource:Label"].hide()
            self.de_widgets["APSource:Label"].hide()
            self.de_widgets["APBirthSource:Label"].hide()
            self.de_widgets["APDeathSource:Label"].hide()

    def hidden_widgets(self):
        if not self.de_widgets["Active person:Show sources"].get_active():
            return [self.de_widgets["NPSource"],
                    self.de_widgets["NPBirthSource"],
                    self.de_widgets["NPDeathSource"],
                    self.de_widgets["APSource"],
                    self.de_widgets["APBirthSource"],
                    self.de_widgets["APDeathSource"],
                    # Labels:
                    self.de_widgets["NPSource:Label"],
                    self.de_widgets["NPBirthSource:Label"],
                    self.de_widgets["NPDeathSource:Label"],
                    self.de_widgets["APSource:Label"],
                    self.de_widgets["APBirthSource:Label"],
                    self.de_widgets["APDeathSource:Label"]]
        else:
            return []

