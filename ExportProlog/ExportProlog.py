# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015       Douglas S. Blank
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

#------------------------------------------------------------------------
#
# GRAMPS modules
#
#------------------------------------------------------------------------
from gramps.gen.plug.utils import OpenFileOrStdout
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.utils.alive import probably_alive

def escape(text):
    return text.replace("'", "\\'")

def exportData(db, filename,
               error_dialog=None, option_box=None, callback=None):
    if not callable(callback):
        callback = lambda percent: None # dummy

    with OpenFileOrStdout(filename) as fp:

        total = (db.get_number_of_notes() +
                 db.get_number_of_people() +
                 db.get_number_of_events() +
                 db.get_number_of_families() +
                 db.get_number_of_repositories() +
                 db.get_number_of_places() +
                 db.get_number_of_media() +
                 db.get_number_of_sources())
        count = 0.0

        # GProlog ISO directives:
        # /number must match the number of arguments to functions:
        fp.write(":- discontiguous(data/2).\n")
        fp.write(":- discontiguous(is_alive/2).\n")
        fp.write(":- discontiguous(parent/2).\n")

        # Rules:
        fp.write("grandparent(X, Y) :- parent(X, Z), parent(Z, Y).\n")
        fp.write("ancestor(X, Y) :- parent(X, Y).\n")
        fp.write("ancestor(X, Y) :- parent(X, Z), ancestor(Z, Y).\n")
        fp.write("sibling(X, Y) :- parent(Z, X), parent(Z, Y), X \\= Y.\n")

        # ---------------------------------
        # Notes
        # ---------------------------------
        for note in db.iter_notes():
            #write_line(fp, "note_details(%s, %s)" % (note.handle, note))
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Event
        # ---------------------------------
        for event in db.iter_events():
            #write_line(fp, "event:", event.handle, event)
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Person
        # ---------------------------------
        for person in db.iter_people():
            gid = person.gramps_id.lower()
            fp.write("data(%s, '%s').\n" % (gid, escape(name_displayer.display(person))))
            fp.write("is_alive(%s, '%s').\n" % (gid, probably_alive(person, database)))
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Family
        # ---------------------------------
        for family in db.iter_families():
            father_handle = family.get_father_handle()
            mother_handle = family.get_mother_handle()
            parents = []
            if mother_handle:
                mother = database.get_person_from_handle(mother_handle)
                if mother:
                    parents.append(mother.gramps_id.lower())
            if father_handle:
                father = database.get_person_from_handle(father_handle)
                if father:
                    parents.append(father.gramps_id.lower())
            children = []
            for child_ref in family.get_child_ref_list():
                child_handle = child_ref.ref
                child = database.get_person_from_handle(child_handle)
                if child:
                    children.append(child.gramps_id.lower())
            for pid in parents:
                for cid in children:
                    fp.write("parent(%s, %s).\n" % (pid, cid))
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Repository
        # ---------------------------------
        for repository in db.iter_repositories():
            #write_line(fp, "repository:", repository.handle, repository)
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Place
        # ---------------------------------
        for place in db.iter_places():
            #write_line(fp, "place:", place.handle, place)
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Source
        # ---------------------------------
        for source in db.iter_sources():
            #write_line(fp, "source:", source.handle, source)
            count += 1
            callback(100 * count/total)

        # ---------------------------------
        # Media
        # ---------------------------------
        for media in db.iter_media():
            #write_line(fp, "media:", media.handle, media)
            count += 1
            callback(100 * count/total)

    return True

def write_line(fp, heading, handle, obj):
    """
    Write a single object to the file.
    """
    fp.write("%s %s %s\n" % (heading, handle.decode(), obj))
