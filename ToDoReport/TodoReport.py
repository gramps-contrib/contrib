#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2007-2008 Brian G. Matherly
# Copyright (C) 2009      Gary Burton
# Copyright (C) 2010      Jakim Friant
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

"""Reports/Text Reports/Todo Report"""

#------------------------------------------------------------------------
#
# Gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.display.name import displayer as name_displayer
from gramps.gen.display.place import displayer as place_displayer
from gramps.gen.plug import docgen
import gramps.gen.datehandler
from gramps.gen.filters import GenericFilterFactory
from gramps.gen.filters import rules
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import Report
from gramps.gen.errors import ReportError
import gramps.gen.plug.report.utils as ReportUtils
from gramps.gen.plug.menu import EnumeratedListOption, BooleanOption
from gramps.gen.const import GRAMPS_LOCALE as glocale
try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

_REF_HANDLE_POS = 0
_NOTE_HANDLE_POS = 1

_PLACEHOLDER = "_" * 12

#------------------------------------------------------------------------
#
# TodoReport
#
#------------------------------------------------------------------------
class TodoReport(Report):
    """Produce a report listing all notes with a given marker.

    Based on the Marker report, but starting with the notes flagged with a
    particular marker (chosen at run-time).  The records that the note
    references are included in the report so you do not have to duplicate
    that information in the note.

    """

    def __init__(self, database, options, user):
        """
        Create the Report object that produces the report.

        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gramps.gen.user.User() instance

        """
        Report.__init__(self, database, options, user)
        menu = options.menu
        self.tag = menu.get_option_by_name('tag').get_value()
        if not self.tag:
            raise ReportError(_('ToDo Report'),
                _('You must first create a tag before running this report.'))
        self.can_group = menu.get_option_by_name('can_group').get_value()

    def write_report(self):
        """
        Generate the report document
        """
        self.doc.start_paragraph("TR-Title")
        title = _("Report on Notes Tagged %s") % self.tag
        mark = docgen.IndexMark(title, docgen.INDEX_TYPE_TOC, 1)
        self.doc.write_text(title, mark)
        self.doc.end_paragraph()

        # get all the notes in the database tagged Todo
        nlist = self.database.get_note_handles()
        FilterClass = GenericFilterFactory('Note')
        my_filter = FilterClass()
        my_filter.add_rule(rules.note.HasTag([self.tag]))
        note_list = my_filter.apply(self.database, nlist)

        if self.can_group:
            self._write_grouped_notes(note_list)
        else:
            self._write_sorted_notes(note_list)

    def _write_grouped_notes(self, note_list):
        """
        Return a dictionary of notes keyed by the referenced object's class name
        """
        # now group the notes by type
        note_groups = dict()
        for note_handle in note_list:
            refs = self.database.find_backlink_handles(note_handle)
            try:
                # grouping by the first reference
                (class_name, r_handle) = list(refs)[0]
                if class_name in note_groups:
                    note_groups[class_name].append((r_handle, note_handle))
                else:
                    note_groups[class_name] = [(r_handle, note_handle)]
            except IndexError:
                # no back-links were found
                pass
        for k in sorted(note_groups.keys(), reverse=True):
            # now sort the handles based on the class name, if we don't find
            # a match, the data will not be sorted.
            if k == "Family":
                note_list = sorted(note_groups[k], key=self.getFamilyKey)
            elif k == "Person":
                note_list = sorted(note_groups[k], key=self.getPersonKey)
            elif k == "Event":
                note_list = sorted(note_groups[k], key=self.getEventKey)
            elif k == "Place":
                note_list = sorted(note_groups[k], key=self.getPlaceKey)
            else:
                note_list = note_groups[k]
            self._write_notes(note_list, k)

    def _write_sorted_notes(self, note_list):
        all_notes = []
        for note_handle in note_list:
            refs = self.database.find_backlink_handles(note_handle)
            # grouping by the first reference
            try:
                (class_name, r_handle) = list(refs)[0]
                if class_name == "Family":
                    key = self.getFamilyKey((r_handle,))
                elif class_name == "Person":
                    key = self.getPersonKey((r_handle,))
                elif class_name == "Event":
                    key = self.getEventKey((r_handle,))
                elif class_name == "Place":
                    key = self.getPlaceKey((r_handle,))
                else:
                    note = self.database.get_note_from_handle(note_handle)
                    key = note.get_gramps_id()
                all_notes.append((key, note_handle))
            except IndexError:
                # no back-link references were found, so we'll use the note ID
                # as the key
                note = self.database.get_note_from_handle(note_handle)
                key = note.get_gramps_id()
        self._write_notes(sorted(all_notes))

    def _write_references(self, note_handle):
        """
        Find the primary references attached the note and add them to the report
        """
        refs = self.database.find_backlink_handles(note_handle)
        for (class_name, r_handle) in refs:
            if class_name == "Family":
                self._write_family(r_handle)
            elif class_name == "Person":
                self._write_person(r_handle)
            elif class_name == "Event":
                self._write_event(r_handle)
            elif class_name == "Place":
                self._write_place(r_handle)

    def _write_notes(self, note_list, title=None):
        """
        Generate a table for the list of notes
        """
        if not note_list:
            return

        if title is not None:
            self.doc.start_paragraph("TR-Heading")
            header = _(title)
            mark = docgen.IndexMark(header, docgen.INDEX_TYPE_TOC, 2)
            self.doc.write_text(header, mark)
            self.doc.end_paragraph()

        self.doc.start_table('NoteTable','TR-Table')

        self.doc.start_row()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal-Bold')
        self.doc.write_text(_("Id"))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell', 3)
        self.doc.start_paragraph('TR-Normal-Bold')
        self.doc.write_text(_("Text"))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

        for handles in note_list:
            note_handle = handles[_NOTE_HANDLE_POS]
            note = self.database.get_note_from_handle(note_handle)

            self.doc.start_row()

            self.doc.start_cell('TR-TableCell')
            self.doc.start_paragraph('TR-Normal')
            self.doc.write_text(note.get_gramps_id())
            self.doc.end_paragraph()
            self.doc.end_cell()

            self.doc.start_cell('TR-TableCell', 3)
            self.doc.write_styled_note(note.get_styledtext(),
                                       note.get_format(), 'TR-Note')
            self.doc.end_cell()

            self.doc.end_row()

            self._write_references(note_handle)

            self.doc.start_row()

            self.doc.start_cell('TR-BorderCell', 4)
            self.doc.start_paragraph('TR-Normal')
            self.doc.write_text('')
            self.doc.end_paragraph()
            self.doc.end_cell()

            self.doc.end_row()

        self.doc.end_table()

    def _write_person(self, person_handle):
        """
        Generate a table row for a person record
        """
        person = self.database.get_person_from_handle(person_handle)

        self.doc.start_row()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(person.get_gramps_id())
        self.doc.end_paragraph()
        self.doc.end_cell()

        name = name_displayer.display(person)
        mark = ReportUtils.get_person_mark(self.database, person)
        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(name, mark)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        birth_ref = person.get_birth_ref()
        if birth_ref:
            event = self.database.get_event_from_handle(birth_ref.ref)
            self.doc.write_text("b. " + gramps.gen.datehandler.get_date( event ))
        else:
            self.doc.write_text("b. " + "_" * 12)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        death_ref = person.get_death_ref()
        if death_ref:
            event = self.database.get_event_from_handle(death_ref.ref)
            self.doc.write_text("d. " + gramps.gen.datehandler.get_date( event ))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

    def _write_family(self, family_handle):
        """
        Generate a table row for this family record
        """
        family = self.database.get_family_from_handle(family_handle)

        self.doc.start_row()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(family.get_gramps_id())
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        father_handle = family.get_father_handle()
        if father_handle:
            father = self.database.get_person_from_handle(father_handle)
            mark = ReportUtils.get_person_mark(self.database, father)
            self.doc.write_text(name_displayer.display(father), mark)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        mother_handle = family.get_mother_handle()
        if mother_handle:
            mother = self.database.get_person_from_handle(mother_handle)
            mark = ReportUtils.get_person_mark(self.database, mother)
            self.doc.write_text(name_displayer.display(mother), mark)
        self.doc.end_paragraph()
        self.doc.end_cell()

        # see if we can find a relationship event to include
        relationship_date = _PLACEHOLDER
        for evt_ref in family.get_event_ref_list():
            evt_handle = evt_ref.get_reference_handle()
            evt = self.database.get_event_from_handle(evt_handle)
            # FIXME: where are the event types defined in Gramps,
            # and are these the only important ones?
            #print repr(evt.get_type().string)
            if evt.get_type().string in ["Marriage", "Civil Union"]:
                relationship_date = gramps.gen.datehandler.get_date(evt)
        rel_msg = _("%(relationship_type)s on %(relationship_date)s") % {'relationship_type': family.get_relationship(),
                                                                         'relationship_date': relationship_date}

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(rel_msg)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

    def _write_event(self, event_handle):
        """
        Generate a table row for this event record
        """
        event = self.database.get_event_from_handle(event_handle)

        self.doc.start_row()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(event.get_gramps_id())
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        date = gramps.gen.datehandler.get_date(event)
        if date:
            self.doc.write_text(date)
        else:
            self.doc.write_text(_("date: ") + _PLACEHOLDER)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        place_handle = event.get_place_handle()
        place = ReportUtils.place_name(self.database, place_handle)
        if place:
            self.doc.write_text(place)
        else:
            self.doc.write_text(_("place: ") + _PLACEHOLDER)
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        descr = event.get_description()
        if descr:
            self.doc.write_text( descr )
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

    def _write_place(self, place_handle):
        """
        Generate a table row with the place record information.
        """
        place = self.database.get_place_from_handle(place_handle)

        self.doc.start_row()

        self.doc.start_cell('TR-TableCell')
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(place.get_gramps_id())
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.start_cell('TR-TableCell', 3)
        self.doc.start_paragraph('TR-Normal')
        self.doc.write_text(place_displayer.display(self.database, place))
        self.doc.end_paragraph()
        self.doc.end_cell()

        self.doc.end_row()

    #
    # Sort Functions
    #
    def getPersonKey(self, group_entry):
        """
        Return a string of the persons name (last, first) as the key
        """
        per_handle = group_entry[_REF_HANDLE_POS]
        person = self.database.get_person_from_handle(per_handle)
        sort_key = person.get_primary_name().get_name()
        return sort_key.upper()

    def getFamilyKey(self, group_entry):
        """
        Return a string with the father's or mother's name (in that order) as the key
        """
        sort_key = ""
        person = None
        family_handle = group_entry[_REF_HANDLE_POS]
        family = self.database.get_family_from_handle(family_handle)
        if family:
            father_handle = family.get_father_handle()
            if father_handle:
                person = self.database.get_person_from_handle(father_handle)
            else:
                mother_handle = family.get_mother_handle()
                if mother_handle:
                    person = self.database.get_person_from_handle(mother_handle)
        if person is not None:
            sort_key = person.get_primary_name().get_name()
        return sort_key.upper()

    def getEventKey(self, group_entry):
        """Return the event date as a string to use for sorting the events.

        I'm returning the date with 'zz' prefixed so it will sort at the bottom
        when not using grouping.

        """
        evt_handle = group_entry[_REF_HANDLE_POS]
        event = self.database.get_event_from_handle(evt_handle)
        date = event.get_date_object()
        return "zz" + str(date)

    def getPlaceKey(self, group_entry):
        """
        Return the place description to use when sorting the place records.
        """
        p_handle = group_entry[_REF_HANDLE_POS]
        place = self.database.get_place_from_handle(p_handle)
        title = place_displayer.display(self.database, place)
        return title.upper()

#------------------------------------------------------------------------
#
# MarkerOptions
#
#------------------------------------------------------------------------
class TodoOptions(MenuReportOptions):
    """Set up the options dialog for this report"""

    def __init__(self, name, dbase):
        """Create the object and initialize the parent class"""
        self.__db = dbase
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the marker report.
        """
        category_name = _("Report Options")

        all_tags = []
        for handle in self.__db.get_tag_handles():
            tag = self.__db.get_tag_from_handle(handle)
            all_tags.append(tag.get_name())

        if len(all_tags) > 0:
            tag_option = EnumeratedListOption(_('Tag'), all_tags[0])
            for tag_name in all_tags:
                tag_option.add_item(tag_name, tag_name)
        else:
            tag_option = EnumeratedListOption(_('Tag'), '')
            tag_option.add_item('', '')

        tag_option.set_help( _("The tag to use for the report"))
        menu.add_option(category_name, "tag", tag_option)

        can_group = BooleanOption(_("Group by reference type"), False)
        can_group.set_help( _("Group notes by Family, Person, Place, etc."))
        menu.add_option(category_name, "can_group", can_group)

    def make_default_style(self, default_style):
        """Make the default output style for the Todo Report."""
        # Paragraph Styles
        font = docgen.FontStyle()
        font.set_size(16)
        font.set_type_face(docgen.FONT_SANS_SERIF)
        font.set_bold(1)
        para = docgen.ParagraphStyle()
        para.set_header_level(1)
        para.set_bottom_border(1)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_font(font)
        para.set_alignment(docgen.PARA_ALIGN_CENTER)
        para.set_description(_("The style used for the title of the page."))
        default_style.add_paragraph_style("TR-Title", para)

        font = docgen.FontStyle()
        font.set(face=docgen.FONT_SANS_SERIF, size=14, italic=1)
        para = docgen.ParagraphStyle()
        para.set_font(font)
        para.set_header_level(2)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_description(_('The style used for the section headers.'))
        default_style.add_paragraph_style("TR-Heading", para)

        font = docgen.FontStyle()
        font.set_size(12)
        para = docgen.ParagraphStyle()
        para.set(first_indent=-0.75, lmargin=.75)
        para.set_font(font)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("TR-Normal", para)

        font = docgen.FontStyle()
        font.set_size(12)
        font.set_bold(True)
        para = docgen.ParagraphStyle()
        para.set(first_indent=-0.75, lmargin=.75)
        para.set_font(font)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_description(_('The basic style used for table headings.'))
        default_style.add_paragraph_style("TR-Normal-Bold", para)

        para = docgen.ParagraphStyle()
        para.set(first_indent=-0.75, lmargin=.75)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_description(_('The basic style used for the note display.'))
        default_style.add_paragraph_style("TR-Note", para)

        #Table Styles
        cell = docgen.TableCellStyle()
        default_style.add_cell_style('TR-TableCell', cell)

        cell = docgen.TableCellStyle()
        cell.set_bottom_border(1)
        default_style.add_cell_style('TR-BorderCell', cell)

        table = docgen.TableStyle()
        table.set_width(100)
        table.set_columns(4)
        table.set_column_width(0, 10)
        table.set_column_width(1, 30)
        table.set_column_width(2, 30)
        table.set_column_width(3, 30)
        default_style.add_table_style('TR-Table', table)
