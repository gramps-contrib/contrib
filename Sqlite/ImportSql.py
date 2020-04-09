#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2009 Douglas S. Blank <doug.blank@gmail.com>
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
# $Id: ImportSql.py 189 2010-02-13 07:08:48Z dsblank $

"Import from SQLite Database"

#-------------------------------------------------------------------------
#
# Standard Python Modules
#
#-------------------------------------------------------------------------
import sqlite3 as sqlite
import time
from collections import abc

#------------------------------------------------------------------------
#
# Set up logging
#
#------------------------------------------------------------------------
import logging
log = logging.getLogger(".ImportSql")

#-------------------------------------------------------------------------
#
# Gramps modules
#
#-------------------------------------------------------------------------
from gramps.gen.lib import (Person, Family, Note, Media, Place, Citation,
                            Source, Tag, Event, Repository, Name, Location,
                            PlaceType)
from gramps.gen.lib.placetype import DM_NAME
from gramps.gen.db import DbTxn
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    trans = glocale.get_addon_translator(__file__)
except ValueError:
    trans = glocale.translation
_ = trans.gettext
ngettext = trans.ngettext


#-------------------------------------------------------------------------
#
# Import functions
#
#-------------------------------------------------------------------------
def lookup(handle, event_ref_list):
    """
    Find the handle in a unserialized event_ref_list and return code.
    """
    if handle is None:
        return -1
    else:
        count = 0
        for event_ref in event_ref_list:
            (_private, _note_list, _attribute_list, ref, _role) = event_ref
            if handle == ref:
                return count
            count += 1
        return -1


#-------------------------------------------------------------------------
#
# SQLite DB Class
#
#-------------------------------------------------------------------------
class Database(object):
    """
    The db connection.
    """
    def __init__(self, database):
        self.database = database
        self.db = sqlite.connect(self.database)
        self.cursor = self.db.cursor()

    def query(self, q, *args):
        if q.strip().upper().startswith("DROP"):
            try:
                self.cursor.execute(q, args)
                self.db.commit()
            except:
                "WARN: no such table to drop: '%s'" % q
        else:
            try:
                self.cursor.execute(q, args)
                self.db.commit()
            except:
                print("ERROR: query :", q)
                print("ERROR: values:", args)
                raise
            return self.cursor.fetchall()

    def close(self):
        """ Closes and writes out tables """
        self.cursor.close()
        self.db.close()


#-------------------------------------------------------------------------
#
# SQL Reader
#
#-------------------------------------------------------------------------
class SQLReader(object):
    def __init__(self, db, filename, user):
        if isinstance(user.callback, abc.Callable):  # is really callable
            callback = user.callback
        else:
            callback = self.dummy_callback  # dummy
        self.db = db
        self.filename = filename
        self.callback = callback
        self.debug = 0

    def openSQL(self):
        try:
            from gramps.gui.dialog import ErrorDialog
        except:
            ErrorDialog = print
        sql = None
        try:
            sql = Database(self.filename)
        except IOError as msg:
            errmsg = _("%s could not be opened\n") % self.filename
            ErrorDialog(errmsg, msg)
            return None
        return sql

    # -----------------------------------------------
    # Get methods to retrieve data from the tables
    # -----------------------------------------------

    def get_address_list(self, sql, from_type, from_handle, with_parish):
        results = self.get_links(sql, from_type, from_handle, "address")
        retval = []
        for handle in results:
            result = sql.query("select * from address where handle = ?;",
                               handle)
            retval.append(self.pack_address(sql, result[0], with_parish))
        return retval

    def get_attribute_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "attribute")
        retval = []
        for handle in handles:
            rows = sql.query("select * from attribute where handle = ?;",
                             handle)
            for row in rows:
                (handle, the_type0, the_type1, value, private) = row
                citation_list = self.get_citation_list(sql, "attribute",
                                                       handle)
                note_list = self.get_note_list(sql, "attribute", handle)
                retval.append((bool(private), citation_list, note_list,
                               (the_type0, the_type1), value))
        return retval

    def get_child_ref_list(self, sql, from_type, from_handle):
        results = self.get_links(sql, from_type, from_handle, "child_ref")
        retval = []
        for handle in results:
            rows = sql.query("select * from child_ref where handle = ?;",
                             handle)
            for row in rows:
                (handle, ref, frel0, frel1, mrel0, mrel1, private) = row
                citation_list = self.get_citation_list(sql, "child_ref",
                                                       handle)
                note_list = self.get_note_list(sql, "child_ref", handle)
                retval.append((bool(private), citation_list, note_list, ref,
                               (frel0, frel1), (mrel0, mrel1)))
        return retval

    def get_datamap_list(self, sql, _from_type, from_handle):
        datamap = []
        rows = sql.query("select * from datamap where from_handle = ?;",
                         from_handle)
        for row in rows:
            (from_handle,
             the_type0,
             the_type1,
             value_field,
             private) = row
            datamap.append((private, (the_type0, the_type1), value_field))
        return datamap

    def get_event_ref_list(self, sql, from_type, from_handle):
        results = self.get_links(sql, from_type, from_handle, "event_ref")
        retval = []
        for handle in results:
            result = sql.query("select * from event_ref where handle = ?;",
                               handle)
            retval.append(self.pack_event_ref(sql, result[0]))
        return retval

    def get_family_list(self, sql, from_type, from_handle):
        return self.get_links(sql, from_type, from_handle, "family")

    def get_parent_family_list(self, sql, from_type, from_handle):
        return self.get_links(sql, from_type, from_handle, "parent_family")

    def get_person_ref_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "person_ref")
        retval = []
        for ref_handle in handles:
            rows = sql.query("select * from person_ref where handle = ?;",
                             ref_handle)
            for row in rows:
                (handle,
                 ref,
                 description,
                 private) = row
                citation_list = self.get_citation_list(sql, "person_ref",
                                                       handle)
                note_list = self.get_note_list(sql, "person_ref", handle)
                retval.append((bool(private),
                               citation_list,
                               note_list,
                               ref,
                               description))
        return retval

    def get_location_list(self, sql, from_type, from_handle, with_parish):
        handles = self.get_links(sql, from_type, from_handle, "location")
        results = []
        for handle in handles:
            results += sql.query("select * from location where handle = ?;",
                                 handle)
        return [self.pack_location(sql, result, with_parish) for
                result in results]

    def get_lds_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "lds")
        results = []
        for handle in handles:
            results += sql.query("""select * from lds where handle = ?;""",
                                 handle)
        return [self.pack_lds(sql, result) for result in results]

    def get_media_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "media_ref")
        results = []
        for handle in handles:
            results += sql.query("select * from media_ref where handle = ?;",
                                 handle)
        return [self.pack_media_ref(sql, result) for result in results]

    def get_surname_list(self, sql, handle):
        results = sql.query(
            "select s.* from surname s inner join link l ON l.to_handle = "
            "s.handle where l.from_handle = ?;", handle)
        return [self.pack_surnames(sql, result) for result in results]

    def get_note_list(self, sql, from_type, from_handle):
        return self.get_links(sql, from_type, from_handle, "note")

    def get_repository_ref_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "repository_ref")
        results = []
        for handle in handles:
            results += sql.query(
                """select * from repository_ref where handle = ?;""", handle)
        return [self.pack_repository_ref(sql, result) for result in results]

    def get_citation_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "citation")
        return handles

    def get_url_list(self, sql, from_type, from_handle):
        handles = self.get_links(sql, from_type, from_handle, "url")
        results = []
        for handle in handles:
            results += sql.query("""select * from url where handle = ?;""",
                                 handle)
        return [self.pack_url(sql, result) for result in results]

    # ---------------------------------
    # Helpers
    # ---------------------------------

    def pack_address(self, sql, data, with_parish):
        (handle, private) = data
        citation_list = self.get_citation_list(sql, "address", handle)
        date_handle = self.get_link(sql, "address", handle, "date")
        date = self.get_date(sql, date_handle)
        note_list = self.get_note_list(sql, "address", handle)
        location = self.get_location(sql, "address", handle, with_parish)
        return (bool(private), citation_list, note_list, date, location)

    def pack_lds(self, sql, data):
        (handle, type_, place, famc, temple, status, private) = data
        citation_list = self.get_citation_list(sql, "lds", handle)
        note_list = self.get_note_list(sql, "lds", handle)
        date_handle = self.get_link(sql, "lds", handle, "date")
        date = self.get_date(sql, date_handle)
        return (citation_list, note_list, date, type_, place,
                famc, temple, status, bool(private))

    def pack_surnames(self, _sql, data):
        (_handle,
         surname,
         prefix,
         primary_surname,
         origin_type0,
         origin_type1,
         connector) = data
        return (surname, prefix, bool(primary_surname),
                (origin_type0, origin_type1), connector)

    def pack_media_ref(self, sql, data):
        (handle,
         ref,
         role0,
         role1,
         role2,
         role3,
         private) = data
        citation_list = self.get_citation_list(sql, "media_ref", handle)
        note_list = self.get_note_list(sql, "media_ref", handle)
        attribute_list = self.get_attribute_list(sql, "media_ref", handle)
        if role0 == role1 == role2 == role3 == -1:
            role = None
        else:
            role = (role0, role1, role2, role3)
        return (bool(private), citation_list, note_list, attribute_list,
                ref, role)

    def pack_repository_ref(self, sql, data):
        (handle,
         ref,
         call_number,
         source_media_type0,
         source_media_type1,
         private) = data
        note_list = self.get_note_list(sql, "repository_ref", handle)
        return (note_list,
                ref,
                call_number,
                (source_media_type0, source_media_type1),
                bool(private))

    def pack_url(self, _sql, data):
        (_handle,
         path,
         desc,
         type0,
         type1,
         private) = data
        return (bool(private), path, desc, (type0, type1))

    def pack_event_ref(self, sql, data):
        (handle,
         ref,
         role0,
         role1,
         private) = data
        note_list = self.get_note_list(sql, "event_ref", handle)
        attribute_list = self.get_attribute_list(sql, "event_ref", handle)
        role = (role0, role1)
        return (bool(private), note_list, attribute_list, ref, role)

    def pack_citation(self, sql, data):
        (handle,
         ref,
         confidence,
         page,
         private) = data
        date_handle = self.get_link(sql, "citation", handle, "date")
        date = self.get_date(sql, date_handle)
        note_list = self.get_note_list(sql, "citation", handle)
        return (date, bool(private), note_list, confidence, ref, page)

    def pack_source(self, sql, data):
        (handle,
         gid,
         title,
         author,
         pubinfo,
         abbrev,
         change,
         private) = data
        note_list = self.get_note_list(sql, "source", handle)
        media_list = self.get_media_list(sql, "source", handle)
        reporef_list = self.get_repository_ref_list(sql, "source", handle)
        datamap = self.get_datamap_list(sql, "source", handle)
        return (handle, gid, title,
                author, pubinfo,
                note_list,
                media_list,
                abbrev,
                change, datamap,
                reporef_list,
                bool(private))

    def get_location(self, sql, from_type, from_handle, with_parish):
        handle = self.get_link(sql, from_type, from_handle, "location")
        if handle:
            results = sql.query("""select * from location where handle = ?;""",
                                handle)
            if len(results) == 1:
                return self.pack_location(sql, results[0], with_parish)

    def get_names(self, sql, from_type, from_handle, primary):
        handles = self.get_links(sql, from_type, from_handle, "name")
        names = []
        for handle in handles:
            results = sql.query(
                "select * from name where handle = ? and primary_name = ?;",
                handle, primary)
            if len(results) > 0:
                names += results
        result = [self.pack_name(sql, name) for name in names]
        if primary:
            if len(result) == 1:
                return result[0]
            elif len(result) == 0:
                return Name().serialize()
            else:
                raise Exception("too many primary names")
        else:
            return result

    def pack_name(self, sql, data):
        # unpack name from SQL table:
        (handle, _primary_name, private, first_name, suffix, title, name_type0,
         name_type1, group_as, sort_as, display_as, call, nick, famnick) = data
        # build up a GRAMPS object:
        surname_list = self.get_surname_list(sql, handle)
        citation_list = self.get_citation_list(sql, "name", handle)
        note_list = self.get_note_list(sql, "name", handle)
        date_handle = self.get_link(sql, "name", handle, "date")
        date = self.get_date(sql, date_handle)
        return (bool(private), citation_list, note_list, date,
                first_name, surname_list, suffix, title,
                (name_type0, name_type1),
                group_as, sort_as, display_as, call, nick, famnick)

    def pack_location(self, _sql, data, with_parish):
        (_handle, street, locality, city, county, state, country, postal,
         phone, parish) = data
        if with_parish:
            return ((street, locality, city, county, state, country, postal,
                     phone), parish)
        else:
            return (street, locality, city, county, state, country, postal,
                    phone)

    def get_place_from_handle(self, sql, ref_handle):
        if ref_handle:
            place_row = sql.query("select * from place where handle = ?;",
                                  ref_handle)
            if len(place_row) == 1:
                # return just the handle here:
                return place_row[0][0]
            elif len(place_row) == 0:
                print("ERROR: get_place_from_handle('%s'), no such handle." %
                      (ref_handle, ))
            else:
                print("ERROR: get_place_from_handle('%s') should be unique;"
                      " returned %d records." % (ref_handle, len(place_row)))
        return ''

    def get_place_name_list(self, sql, handle):
        place_name_list = sql.query(
            """select * from place_name where from_handle = ?;""", handle)
        retval = []
        for place_name_data in place_name_list:
            ref_handle, handle, value, lang = place_name_data
            date_handle = self.get_link(sql, "place_name", ref_handle, "date")
            date = self.get_date(sql, date_handle)
            abbr_list = self.get_place_abbr_list(sql, ref_handle)
            citation_list = self.get_citation_list(sql, "place_name",
                                                   ref_handle)
            retval.append((value, date, lang, abbr_list, citation_list))
        return retval

    def get_place_abbr_list(self, sql, handle):
        place_abbr_list = sql.query(
            """select * from place_abbrev where from_handle = ?;""", handle)
        retval = []
        for place_abbr_data in place_abbr_list:
            _r_handle, handle, value, abbr_type0, abbr_type1 = place_abbr_data
            retval.append((value, (abbr_type0, abbr_type1)))
        return retval

    def get_place_ref_list(self, sql, handle):
        # place_ref_list = Enclosed by:  [('4ECKQCWCLO5YIHXEXC', None)]
        # [(handle, date)...]
        place_ref_list = sql.query(
            """select * from place_ref where from_place_handle = ?;""", handle)
        retval = []
        for ref_data in place_ref_list:
            ref_handle, handle, to_place_handle, h_type0, h_type1 = ref_data
            date_handle = self.get_link(sql, "place_ref", ref_handle, "date")
            date = self.get_date(sql, date_handle)
            citation_list = self.get_citation_list(sql, "place_ref",
                                                   ref_handle)
            retval.append((to_place_handle, date, citation_list,
                           (h_type0, h_type1)))
        return retval

    def get_place_type_list(self, sql, handle):
        place_type_list = sql.query(
            """select * from place_type where from_handle = ?;""",
            handle)
        retval = []
        for place_type_data in place_type_list:
            ref_handle, handle, type0, type1 = place_type_data
            date_handle = self.get_link(sql, "place_type", ref_handle, "date")
            date = self.get_date(sql, date_handle)
            citation_list = self.get_citation_list(sql, "place_type",
                                                   ref_handle)
            retval.append((type0, date, citation_list))
            if type0 in PlaceType.DATAMAP:
                # if the number is already there, we are done
                continue
            if type0 < PlaceType.CUSTOM:
                # number is not definitive, check for already there by name
                for tup in PlaceType.DATAMAP.values():
                    if type1.lower() == tup[DM_NAME].lower():
                        break
                else:
                    PlaceType.DATAMAP[type0] = (type1,
                                                PlaceType.G_PLACE,  # groups
                                                True)               # visible
            else:
                # not found, so store the new definition
                PlaceType.DATAMAP[type0] = (type1,
                                            PlaceType.G_PLACE,  # groups
                                            True)               # visible
        return retval

    def get_main_location(self, sql, from_handle, with_parish):
        ref_handle = self.get_link(sql, "place_main", from_handle, "location")
        if ref_handle:
            place_row = sql.query("select * from location where handle = ?;",
                                  ref_handle)
            if len(place_row) == 1:
                return self.pack_location(sql, place_row[0], with_parish)
            elif len(place_row) == 0:
                print("ERROR: get_main_location('%s'), no such handle." %
                      (ref_handle, ))
            else:
                print("ERROR: get_main_location('%s') should be unique; "
                      "returned %d records." % (ref_handle, len(place_row)))
        return Location().serialize()

    def get_link(self, sql, from_type, from_handle, to_link):
        """
        Return a link, and return handle.
        """
        if from_handle is None:
            return
        assert type(from_handle) == str, \
            ("from_handle is wrong type: %s is %s" %
             (from_handle, type(from_handle)))
        rows = self.get_links(sql, from_type, from_handle, to_link)
        if len(rows) == 1:
            return rows[0]
        elif len(rows) > 1:
            print("ERROR: too many links %s:%s -> %s (%d)" %
                  (from_type, from_handle, to_link, len(rows)))
        return None

    def get_links(self, sql, from_type, from_handle, to_link):
        """
        Return a list of handles (possibly none).
        """
        results = sql.query(
            """select to_handle from link where from_type = ? and """
            """from_handle = ? and to_type = ?;""",
            from_type, from_handle, to_link)
        return [result[0] for result in results]

    def get_date(self, sql, handle):
        assert type(handle) in [str, type(None)], ("handle is wrong type: %s" %
                                                   handle)
        if handle:
            rows = sql.query("select * from date where handle = ?;", handle)
            if len(rows) == 1:
                (handle,
                 calendar,
                 modifier,
                 quality,
                 day1,
                 month1,
                 year1,
                 slash1,
                 day2,
                 month2,
                 year2,
                 slash2,
                 text,
                 sortval,
                 newyear) = rows[0]
                dateval = (day1, month1, year1, bool(slash1), day2, month2,
                           year2, bool(slash2))
                if day2 == month2 == year2 == 0 and not slash2:
                    dateval = day1, month1, year1, bool(slash1)
                return (calendar, modifier, quality, dateval, text, sortval,
                        newyear)
            elif len(rows) == 0:
                return None
            else:
                print(Exception("ERROR, wrong number of dates: %s" % rows))

    def process(self):
        sql = self.openSQL()
        total = (sql.query("select count(*) from note;")[0][0] +
                 sql.query("select count(*) from person;")[0][0] +
                 sql.query("select count(*) from event;")[0][0] +
                 sql.query("select count(*) from family;")[0][0] +
                 sql.query("select count(*) from repository;")[0][0] +
                 sql.query("select count(*) from place;")[0][0] +
                 sql.query("select count(*) from media;")[0][0] +
                 sql.query("select count(*) from tag;")[0][0] +
                 sql.query("select count(*) from citation;")[0][0] +
                 sql.query("select count(*) from source;")[0][0])
        with DbTxn(_("CSV import"), self.db, batch=True) as self.trans:
            self.db.disable_signals()
            count = 0.0
            self.t = time.time()
            self._process(count, total, sql)
        sql.db.commit()
        sql.db.close()
        return None

    def _process(self, count, total, sql):
        # ---------------------------------
        # Process note
        # ---------------------------------
        notes = sql.query("""select * from note;""")
        for note in notes:
            (handle,
             gid,
             text,
             _format,
             note_type1,
             note_type2,
             change,
             private) = note
            styled_text = [text, []]
            markups = sql.query("""select * from link where from_handle = ? """
                                """and to_type = 'markup';""",
                                handle)
            for markup_link in markups:
                _from_type, _from_handle, _to_type, to_handle = markup_link
                markup_detail = sql.query(
                    """select * from markup where handle = ?;""", to_handle)
                for markup in markup_detail:
                    (_mhandle,
                     markup0,
                     markup1,
                     value,
                     start_stop_list) = markup
                    ss_list = eval(start_stop_list)
                    styled_text[1] += [((markup0, markup1), value, ss_list)]

            tags = self.get_links(sql, "note", handle, "tag")

            g_note = Note()
            g_note.unserialize((handle, gid, styled_text, _format,
                                (note_type1, note_type2), change,
                                tags, bool(private)))
            self.db.add_note(g_note, self.trans)
            count += 1
            self.callback(100 * count / total)

        # ---------------------------------
        # Process event
        # ---------------------------------
        events = sql.query("""select * from event;""")
        for event in events:
            (handle, gid, the_type0, the_type1, description, change,
             private) = event

            note_list = self.get_note_list(sql, "event", handle)
            citation_list = self.get_citation_list(sql, "event", handle)
            media_list = self.get_media_list(sql, "event", handle)
            attribute_list = self.get_attribute_list(sql, "event", handle)

            date_handle = self.get_link(sql, "event", handle, "date")
            date = self.get_date(sql, date_handle)

            place_handle = self.get_link(sql, "event", handle, "place")
            place = self.get_place_from_handle(sql, place_handle)

            tags = self.get_links(sql, "event", handle, "tag")
            data = (handle, gid, (the_type0, the_type1), date, description,
                    place, citation_list, note_list, media_list,
                    attribute_list, change, tags, bool(private))

            g_event = Event()
            g_event.unserialize(data)
            self.db.add_event(g_event, self.trans)

            count += 1
            self.callback(100 * count / total)

        # ---------------------------------
        # Process person
        # ---------------------------------
        people = sql.query("""select * from person;""")
        for person in people:
            if person is None:
                continue
            (handle,             # 0
             gid,                # 1
             gender,             # 2
             death_ref_handle,   # 5
             birth_ref_handle,   # 6
             change,             # 17
             private,            # 19
             ) = person
            primary_name = self.get_names(sql, "person", handle, True)  # one
            alternate_names = self.get_names(sql, "person", handle, False)
            event_ref_list = self.get_event_ref_list(sql, "person", handle)
            family_list = self.get_family_list(sql, "person", handle)
            parent_family_list = self.get_parent_family_list(sql, "person",
                                                             handle)
            media_list = self.get_media_list(sql, "person", handle)
            address_list = self.get_address_list(sql, "person", handle,
                                                 with_parish=False)
            attribute_list = self.get_attribute_list(sql, "person", handle)
            urls = self.get_url_list(sql, "person", handle)
            lds_ord_list = self.get_lds_list(sql, "person", handle)
            pcitation_list = self.get_citation_list(sql, "person", handle)
            pnote_list = self.get_note_list(sql, "person", handle)
            person_ref_list = self.get_person_ref_list(sql, "person", handle)
            death_ref_index = lookup(death_ref_handle, event_ref_list)
            birth_ref_index = lookup(birth_ref_handle, event_ref_list)
            tags = self.get_links(sql, "person", handle, "tag")

            data = (
                handle,             # 0
                gid,                # 1
                gender,             # 2
                primary_name,       # 3
                alternate_names,    # 4
                death_ref_index,    # 5
                birth_ref_index,    # 6
                event_ref_list,     # 7
                family_list,        # 8
                parent_family_list,  # 9
                media_list,         # 10
                address_list,       # 11
                attribute_list,     # 12
                urls,               # 13
                lds_ord_list,       # 14
                pcitation_list,     # 15
                pnote_list,         # 16
                change,             # 17
                tags,
                bool(private),      # 19
                person_ref_list,)   # 20

            g_pers = Person()
            g_pers.unserialize(data)
            self.db.add_person(g_pers, self.trans)
            count += 1
            self.callback(100 * count / total)
        # ---------------------------------
        # Process family
        # ---------------------------------
        families = sql.query("""select * from family;""")
        for family in families:
            (handle, gid, father_handle, mother_handle, the_type0, the_type1,
             change, private) = family

            child_ref_list = self.get_child_ref_list(sql, "family", handle)
            event_ref_list = self.get_event_ref_list(sql, "family", handle)
            media_list = self.get_media_list(sql, "family", handle)
            attribute_list = self.get_attribute_list(sql, "family", handle)
            lds_seal_list = self.get_lds_list(sql, "family", handle)
            citation_list = self.get_citation_list(sql, "family", handle)
            note_list = self.get_note_list(sql, "family", handle)
            tags = self.get_links(sql, "family", handle, "tag")

            data = (handle, gid, father_handle, mother_handle, child_ref_list,
                    (the_type0, the_type1), event_ref_list, media_list,
                    attribute_list, lds_seal_list, citation_list, note_list,
                    change, tags, private)
            g_fam = Family()
            g_fam.unserialize(data)
            self.db.add_family(g_fam, self.trans)

            count += 1
            self.callback(100 * count / total)
        # ---------------------------------
        # Process repository
        # ---------------------------------
        repositories = sql.query("""select * from repository;""")
        for repo in repositories:
            (handle, gid, the_type0, the_type1, name, change, private) = repo

            note_list = self.get_note_list(sql, "repository", handle)
            address_list = self.get_address_list(sql, "repository", handle,
                                                 with_parish=False)
            urls = self.get_url_list(sql, "repository", handle)
            tags = self.get_links(sql, "repository", handle, "tag")
            data = (handle, gid,
                    (the_type0, the_type1),
                    name, note_list,
                    address_list, urls, change,
                    tags, private)
            g_rep = Repository()
            g_rep.unserialize(data)
            self.db.add_repository(g_rep, self.trans)
            count += 1
            self.callback(100 * count / total)
        # ---------------------------------
        # Process place
        # ---------------------------------
        places = sql.query("""select * from place;""")
        for place in places:
            count += 1
            (handle, gid, title, long, lat, change, private) = place

            # We could look this up by "place_main", but we have the handle:
            #main_loc = self.get_main_location(sql, handle, with_parish=True)
            alt_loc_list = self.get_location_list(sql, "place_alt", handle,
                                                  with_parish=True)
            urls = self.get_url_list(sql, "place", handle)
            media_list = self.get_media_list(sql, "place", handle)
            citation_list = self.get_citation_list(sql, "place", handle)
            note_list = self.get_note_list(sql, "place", handle)
            tags = self.get_links(sql, "place", handle, "tag")
            place_type_list = self.get_place_type_list(sql, handle)
            place_name_list = self.get_place_name_list(sql, handle)
            place_ref_list = self.get_place_ref_list(sql, handle)
            eventref_list = self.get_event_ref_list(sql, "place", handle)
            attr_list = self.get_attribute_list(sql, "place", handle)
            data = (handle, gid, title, long, lat, place_ref_list,
                    place_name_list, place_type_list, eventref_list,
                    alt_loc_list, urls, media_list, citation_list, note_list,
                    change, tags, private, attr_list)
            g_plac = Place()
            g_plac.unserialize(data)
            self.db.commit_place(g_plac, self.trans)
            self.callback(100 * count / total)

        # ---------------------------------
        # Process citation
        # ---------------------------------
        citations = sql.query("""select * from citation;""")
        for citation in citations:
            (handle, gid, confidence, page, source_handle, change,
             private) = citation
            date_handle = self.get_link(sql, "citation", handle, "date")
            date = self.get_date(sql, date_handle)
            note_list = self.get_note_list(sql, "citation", handle)
            media_list = self.get_media_list(sql, "citation", handle)
            datamap = self.get_datamap_list(sql, "citation", handle)
            tags = self.get_links(sql, "citation", handle, "tag")
            data = (handle, gid, date, page, confidence, source_handle,
                    note_list, media_list, datamap, change, tags, private)
            g_cit = Citation()
            g_cit.unserialize(data)
            self.db.commit_citation(g_cit, self.trans)
            count += 1
            self.callback(100 * count / total)

        # ---------------------------------
        # Process source
        # ---------------------------------
        sources = sql.query("""select * from source;""")
        for source in sources:
            (handle, gid, title, author, pubinfo, abbrev, change,
             private) = source
            note_list = self.get_note_list(sql, "source", handle)
            media_list = self.get_media_list(sql, "source", handle)
            datamap = self.get_datamap_list(sql, "source", handle)
            reporef_list = self.get_repository_ref_list(sql, "source", handle)
            tags = self.get_links(sql, "source", handle, "tag")

            data = (handle, gid, title, author, pubinfo, note_list,
                    media_list, abbrev, change, datamap, reporef_list,
                    tags, private)
            g_src = Source()
            g_src.unserialize(data)
            self.db.commit_source(g_src, self.trans)
            count += 1
            self.callback(100 * count / total)
        # ---------------------------------
        # Process media
        # ---------------------------------
        media = sql.query("""select * from media;""")
        for med in media:
            (handle, gid, path, mime, desc, checksum, change, private) = med

            attribute_list = self.get_attribute_list(sql, "media", handle)
            citation_list = self.get_citation_list(sql, "media", handle)
            note_list = self.get_note_list(sql, "media", handle)

            date_handle = self.get_link(sql, "media", handle, "date")
            date = self.get_date(sql, date_handle)
            tags = self.get_links(sql, "media", handle, "tag")

            data = (handle, gid, path, mime, desc, checksum, attribute_list,
                    citation_list, note_list, change, date, tags, private)
            g_med = Media()
            g_med.unserialize(data)
            self.db.commit_media(g_med, self.trans)
            count += 1
            self.callback(100 * count / total)
        # ---------------------------------
        # Process tag
        # ---------------------------------
        tags = sql.query("""select * from tag;""")
        for tag in tags:
            (handle, name, color, priority, change) = tag

            data = (handle, name, color, priority, change)
            g_tag = Tag()
            g_tag.unserialize(data)
            self.db.commit_tag(g_tag, self.trans)
            count += 1
            self.callback(100 * count / total)

    def cleanup(self):
        self.t = time.time() - self.t
        msg = ngettext('Import Complete: %d second',
                       'Import Complete: %d seconds', self.t) % self.t
        self.db.enable_signals()
        self.db.request_rebuild()
        print(msg)


def importData(db, filename, user):
    g = SQLReader(db, filename, user)
    g.process()
    g.cleanup()
    return _("Import finished...")
