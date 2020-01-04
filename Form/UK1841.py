#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2019-2020 Steve Youngs
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

# ------------------------------------------------------------------------
#
# Gramps modules
#
# ------------------------------------------------------------------------
from gramps.gen.datehandler import displayer as date_displayer
from gramps.gen.db import DbTxn
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.lib import (Date, Event, EventType, EventRef, EventRoleType,
                            Name, Person)
from gramps.gen.utils.db import get_participant_from_event

# ------------------------------------------------------------------------
#
# Gramplet modules
#
# ------------------------------------------------------------------------
import actionutils

# ------------------------------------------------------------------------
#
# Internationalisation
#
# ------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation

_ = _trans.gettext


def get_actions(dbstate, citation, form_event):
    """
    return a list of all actions that this module can provide for the given citation and form
    each list entry is a string, describing the action category, and a list of actions that can be performed.
    """
    actions = []
    actions.append(PrimaryNameCitation.get_actions(
        dbstate, citation, form_event))
    actions.append(AlternateName.get_actions(dbstate, citation, form_event))
    actions.append(BirthEvent.get_actions(dbstate, citation, form_event))
    actions.append(OccupationEvent.get_actions(dbstate, citation, form_event))
    actions.append(ResidenceEvent.get_actions(dbstate, citation, form_event))
    return actions


class PrimaryNameCitation:
    @staticmethod
    def get_actions(dbstate, citation, form_event):
        db = dbstate.db
        actions = []
        for (person, attr) in actionutils.get_form_person_attr(db, form_event.get_handle(), 'Name'):
            actions.append((name_displayer.display(person), attr.get_value(), actionutils.CANNOT_EDIT_DETAIL,
                            lambda dbstate, uistate, track, edit_detail, callback, citation_handle=citation.handle, person_handle=person.handle: PrimaryNameCitation.command(dbstate, uistate, track, edit_detail, callback, citation_handle, person_handle)))
        return (_("Add Primary Name citation"), actions)

    @staticmethod
    def command(dbstate, uistate, track, edit_detail, callback, citation_handle, person_handle):
        db = dbstate.db
        person = db.get_person_from_handle(person_handle)
        person.get_primary_name().add_citation(citation_handle)
        with DbTxn(_("Add Person ({name})").format(name=name_displayer.display(person)), db) as trans:
            db.commit_person(person, trans)
        if callback:
            callback()

class AlternateName:
    @staticmethod
    def get_actions(dbstate, citation, form_event):
        db = dbstate.db
        actions = []
        for (person, attr) in actionutils.get_form_person_attr(db, form_event.get_handle(), 'Name'):
            alternate = Name()
            alternate.set_first_name(attr.get_value())
            alternate.add_citation(citation.handle)
            detail = _('Given Name: {name}').format(name=attr.get_value())
            actions.append((name_displayer.display(person), detail, actionutils.MUST_EDIT_DETAIL,
                            lambda dbstate, uistate, track, edit_detail, callback, person_handle=person.handle, alternate_=alternate: AlternateName.command(dbstate, uistate, track, edit_detail, callback, person_handle, alternate_)))
        return (_("Add alternate name"), actions)

    @staticmethod
    def command(dbstate, uistate, track, edit_detail, callback, person_handle, alternate):
        db = dbstate.db
        person = db.get_person_from_handle(person_handle)
        person.add_alternate_name(alternate)
        with DbTxn(_("Add Person ({name})").format(name=name_displayer.display(person)), db) as trans:
            db.commit_person(person, trans)
        if callback:
            callback()


class BirthEvent:
    @staticmethod
    def get_actions(dbstate, citation, form_event):
        db = dbstate.db
        actions = []
        # if there is no date on the form, no actions can be performed
        if form_event.get_date_object():
            for (person, attr) in actionutils.get_form_person_attr(db, form_event.get_handle(), 'Age'):
                age_string = attr.get_value()
                if age_string:
                    birth_date = None
                    if actionutils.represents_int(age_string):
                        age = int(age_string)
                        if age:
                            birth_date = form_event.get_date_object() - age
                            birth_date.make_vague()
                            # Age was rounded down to the nearest five years for those aged 15 or over
                            # In practice this rule was not always followed by enumerators
                            if age < 15:
                                # no adjustment required
                                birth_date.set_modifier(Date.MOD_ABOUT)
                            elif not birth_date.is_compound():
                                # in theory, birth_date will never be compound since 1841 census date was 1841-06-06. Let's handle it anyway.
                                # create a compound range spanning the possible birth years
                                birth_range = (birth_date - 5).get_dmy() + \
                                    (False,) + birth_date.get_dmy() + (False,)
                                birth_date.set(Date.QUAL_NONE, Date.MOD_RANGE, birth_date.get_calendar(
                                ), birth_range, newyear=birth_date.get_new_year())
                            birth_date.set_quality(Date.QUAL_CALCULATED)
                            detail = _('Age: {age}\nDate: {date}').format(
                                age=age_string, date=date_displayer.display(birth_date))
                    else:
                        detail = _('Age: {age}').format(age=age_string)
                    actions.append((name_displayer.display(person), detail, actionutils.CAN_EDIT_DETAIL if birth_date else actionutils.MUST_EDIT_DETAIL,
                                    lambda dbstate, uistate, track, edit_detail, callback, citation_handle=citation.handle, person_handle=person.handle, birth_date_=birth_date: actionutils.add_event_to_person(dbstate, uistate, track, edit_detail, callback, person_handle, EventType.BIRTH, birth_date_, None, citation_handle, EventRoleType.PRIMARY)))
        return (_("Add Birth event"), actions)


class OccupationEvent:
    @staticmethod
    def get_actions(dbstate, citation, form_event):
        db = dbstate.db
        actions = []
        for (person, attr) in actionutils.get_form_person_attr(db, form_event.get_handle(), 'Occupation'):
            occupation = attr.get_value()
            if (occupation):
                actions.append((name_displayer.display(person), _('Description: {occupation}').format(occupation=occupation), actionutils.CAN_EDIT_DETAIL,
                                lambda dbstate, uistate, track, edit_detail, callback, citation_handle=citation.handle, person_handle=person.handle, occupation_=occupation: actionutils.add_event_to_person(dbstate, uistate, track, edit_detail, callback, person_handle, EventType.OCCUPATION, form_event.get_date_object(), occupation_, citation_handle, EventRoleType.PRIMARY)))
        return (_("Add Occupation event"), actions)


class ResidenceEvent:
    @staticmethod
    def get_actions(dbstate, citation, form_event):
        db = dbstate.db
        # build a list of all the people referenced in the form. For 1841, all people have a PRIMARY event role
        people = []
        for item in db.find_backlink_handles(form_event.get_handle(), include_classes=['Person']):
            handle = item[1]
            person = db.get_person_from_handle(handle)
            for event_ref in person.get_event_ref_list():
                if event_ref.ref == form_event.get_handle():
                    people.append((person.get_handle(), EventRoleType.PRIMARY))
        actions = []
        if people:
            detail = None
            if form_event.get_place_handle():
                place = place_displayer.display(
                    db, db.get_place_from_handle(form_event.get_place_handle()))
                detail = _('Place: {place}').format(place=place)
            actions.append((get_participant_from_event(db, form_event.get_handle()), detail, actionutils.MUST_EDIT_DETAIL,
                            lambda dbstate, uistate, track, edit_detail, callback, citation_handle=citation.handle, people_handles=people: ResidenceEvent.command(dbstate, uistate, track, edit_detail, callback, citation_handle, form_event.get_date_object(), form_event.get_place_handle(), people_handles)))
        return (_("Add Residence event"), actions)

    @staticmethod
    def command(dbstate, uistate, track, edit_detail, callback, citation_handle, event_date_object, event_place_handle, people_handles):
        db = dbstate.db
        # create the RESIDENCE event
        event = Event()
        event.set_type(EventType.RESIDENCE)
        event.set_date_object(event_date_object)
        event.set_place_handle(event_place_handle)
        event.add_citation(citation_handle)
        with DbTxn(_("Add Event ({id})").format(id=event.get_gramps_id()), db) as trans:
            db.add_event(event, trans)

        # and reference the event from all people
        event_ref = EventRef()
        event_ref.ref = event.get_handle()
        for (person_handle, role) in people_handles:
            event_ref.set_role(role)
            person = db.get_person_from_handle(person_handle)
            person.add_event_ref(event_ref)
            with DbTxn(_("Add Event ({name})").format(name=name_displayer.display(person)), db) as trans:
                db.commit_person(person, trans)
        if callback:
            callback()
