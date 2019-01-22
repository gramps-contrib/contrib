#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2006-2007  Alex Roitman
# Copyright (C) 2008-2009  Gary Burton
# Copyright (C) 2007-2016  Jerome Rapinat
# Copyright (C) 2009  Brian G. Matherly
# Copyright (C) 2010  Douglas S. Blank
# Copyright (C) 2016  Paul Franklin
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

"""
Display Sources related to repositories
"""

#-------------------------------------------------------------------------
#
# python modules
#
#-------------------------------------------------------------------------

import os
import gettext

#-------------------------------------------------------------------------
#
# gramps modules
#
#-------------------------------------------------------------------------

from gramps.gen.const import USER_PLUGINS
from gramps.gen.plug.menu import FilterOption, BooleanOption, EnumeratedListOption
from gramps.gen.plug.report import Report
import gramps.gen.plug.report.utils as ReportUtils
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.const import GRAMPS_LOCALE as glocale
import gramps.gen.proxy
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                             TableStyle, TableCellStyle,
                             FONT_SANS_SERIF, FONT_SERIF,
                             INDEX_TYPE_TOC, PARA_ALIGN_CENTER)

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

LOCALEDIR = os.path.join(USER_PLUGINS, 'RepositoriesReport', 'locale')
LOCALEDOMAIN = 'addon'

space = " "

class RepositoryReportAlt(Report):
    """
    Repository Report class
    """
    def __init__(self, database, options, user):
        """
        Create the RepositoryReport object produces the Repositories report.

        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.

        incintern    - Whether to include urls for repository.
        incaddres    - Whether to include addresses for repository.
        incauthor    - Whether to include author of source.
        incabbrev    - Whether to include abbreviation of source.
        incpublic    - Whether to include publication information of source.
        incdatamp    - Whether to include data keys and values of source.
        inclunote    - Whether to include notes of source or repository.
        inclmedia    - Whether to include media of source.
        inclcitat    - Whether to include citations of source.
        incprivat    - Whether to include private records.
        incempty     - Whether to include empty lines with keys for filling.
        trans        - Select translation

        """

        Report.__init__(self, database, options, user)

        self.user = user

        menu = options.menu
        get_option_by_name = menu.get_option_by_name
        get_value = lambda name: get_option_by_name(name).get_value()

        self.inc_intern = get_value('incintern')
        self.inc_addres = get_value('incaddres')
        self.inc_author = get_value('incauthor')
        self.inc_abbrev = get_value('incabbrev')
        self.inc_public = get_value('incpublic')
        self.inc_datamp = get_value('incdatamp')
        self.inclu_note = get_value('inclunote')
        self.incl_media = get_value('inclmedia')
        self.incl_citat = get_value('inclcitat')
        self.inc_privat = get_value('incprivat')
        self.incl_empty = get_value('incempty')

        language = get_value('trans')
        locale = self.set_locale(language)

        filter_option = get_option_by_name('filter')
        self.filter = filter_option.get_filter()

    def write_report(self):
        """
        The routine the actually creates the report. At this point, the document
        is opened and ready for writing.
        """

        # Write the title line. Set in INDEX marker so that this section will be
        # identified as a major category if this is included in a Book report.

        if not self.inc_privat:
            self.database = gramps.gen.proxy.PrivateProxyDb(self.database)

        title = self._('Repositories Report')
        mark = IndexMark(title, INDEX_TYPE_TOC, 1)
        self.doc.start_paragraph('REPO-ReportTitle')
        self.doc.write_text(title, mark)
        self.doc.end_paragraph()
        self.__write_all_repositories()

    def __write_all_repositories(self):
        """
        This procedure writes out all repositories.
        """

        if self.filter.get_name() != '':
            # Use the selected filter to provide a list of repository handles
            repofilterlist = self.database.iter_repository_handles()
            rlist = self.filter.apply(self.database, repofilterlist)
        else:
            rlist = self.database.get_repository_handles()

        for handle in rlist:
            self.__write_repository(handle)
            self.__write_referenced_sources(handle)

    def __write_repository(self, handle):
        """
        This procedure writes out the details of a single repository.
        """

        self.black_list = []
        repository = self.database.get_repository_from_handle(handle)

        self.doc.start_paragraph('REPO-RepositoryTitle')

        self.doc.write_text(('%(repository)s (%(type)s)') %
                                {'repository' : repository.get_name(),
                                'type' : repository.get_type()})
        self.doc.end_paragraph()

        # display notes and allows markups

        if repository.get_referenced_handles() and self.inclu_note:
            notelist = repository.get_referenced_handles()
            for note_handle in notelist:

                # on tuple : [0] = classname ; [1] = handle

                note_handle = note_handle[1]
                self.__write_referenced_notes(note_handle)

        # additional repository informations

        child_list = repository.get_text_data_child_list()
        addresses = repository.get_handle_referents()
        for address_handle in addresses:
            address = ReportUtils.get_address_str(address_handle)

            if self.inc_intern or self.inc_addres:
                self.doc.start_paragraph('REPO-Section2')

                #if self.inc_intern:
                    #self.doc.write_text(self._('Internet:'))
                    #self.doc.write_text(internet)
                if self.inc_addres or self.incl_empty:
                    self.doc.write_text(self._('Address:') + space)
                    self.doc.write_text(address)

                self.doc.end_paragraph()

    def __write_referenced_sources(self, handle):
        """
        This procedure writes out each of the sources related to the repository.
        """

        repository = self.database.get_repository_from_handle(handle)
        repository_handles = [handle for (object_type, handle) in \
                         self.database.find_backlink_handles(handle,['Source'])]

        source_nbr = 0

        for source_handle in repository_handles:
            src = self.database.get_source_from_handle(source_handle)

            # Get the list of references from this source to our repo
            # (can be more than one, technically)

            for reporef in src.get_reporef_list():
                if reporef.ref == repository.handle:
                    source_nbr += 1
                    self.doc.start_paragraph('REPO-Section')

                    title = (('%(nbr)s. %(name)s (%(type)s) : %(call)s') %
                                    {'nbr' : source_nbr,
                                     'name' : src.get_title(),
                                     'type' : str(reporef.get_media_type()),
                                     'call' : reporef.get_call_number()})
                    self.doc.write_text(title)
                    self.doc.end_paragraph()

                    # additional source informations

                    author = src.get_author()
                    abbrev = src.get_abbreviation()
                    public = src.get_publication_info()

                    # keys and values into a list []

                    data = ' '

                    if len(src.serialize()[9]) > 1:
                        for i in range(len(src.serialize()[9])):
                            key = str(src.serialize()[9][i][1][1])
                            value = str(src.serialize()[9][i][2])
                            data += " " + key + " = " + value + ", "

                    if len(src.serialize()[9]) == 1:
                        key = str(src.serialize()[9][0][1][1])
                        value = str(src.serialize()[9][0][2])
                        data = key + " = " + value + ", "

                    # if need, generates child section

                    if self.inc_author or self.inc_abbrev or self.inc_public or self.inc_datamp:
                        if self.inc_author and author != "" or self.incl_empty:
                            self.doc.start_paragraph('REPO-Section2')
                            self.doc.write_text(self._('Author:') + space)
                            self.doc.write_text(author)
                            self.doc.end_paragraph()
                        if self.inc_abbrev and abbrev != "" or self.incl_empty:
                            self.doc.start_paragraph('REPO-Section2')
                            self.doc.write_text(self._('Abbreviation:') + space)
                            self.doc.write_text(abbrev)
                            self.doc.end_paragraph()
                        if self.inc_public and public != "" or self.incl_empty:
                            self.doc.start_paragraph('REPO-Section2')
                            self.doc.write_text(self._('Publication information:') + space)
                            self.doc.write_text(public)
                            self.doc.end_paragraph()
                        if self.inc_datamp and data != "" or self.incl_empty:
                            self.doc.start_paragraph('REPO-Section2')
                            self.doc.write_text(self._('Data:') + space)
                            self.doc.write_text(data)
                            self.doc.end_paragraph()

                    # display notes and allows markups

                    if src.get_referenced_handles() and self.inclu_note:
                        notelist = src.get_referenced_handles()
                        for note_handle in notelist:

                            # on tuple : [0] = classname ; [1] = handle

                            note_handle = note_handle[1]
                            self.__write_referenced_notes(note_handle)

                    if src.get_citation_child_list() and self.incl_media:
                        medialist = src.get_citation_child_list()
                        for media_handle in medialist:
                            if media_handle not in self.black_list:
                                photos = src.get_media_list()
                                self.__write_referenced_media(photos, media_handle)
                            self.black_list.append(media_handle)

            for (object_type, citationref) in self.database.find_backlink_handles(source_handle):
                if self.incl_citat:
                    self.__write_referenced_citations(citationref)

    def __write_referenced_notes(self, note_handle):
        """
        This procedure writes out each of the notes related to the repository or source.
        """

        note = self.database.get_note_from_handle(note_handle)
        if note:
            self.doc.write_styled_note(note.get_styledtext(),
                                       note.get_format(), 'REPO-Note')

    def __write_referenced_media(self, photos, media_handle):
        """
        This procedure writes out each of the media related to the source.
        """

        # see indivcomplete textual report

        self.doc.start_table("images", 'REPO-MediaTab')
        cells = 3 # the GalleryTable has 3 cells
        self.doc.start_row()

        count = 0
        total = len(photos)

        for image in photos[0:3]: # only one line
            count += 1

            # check if not multiple references (citations) ???
            # TOFIX

            self.doc.start_cell('REPO-MediaCell')
            if image not in self.black_list:
                ReportUtils.insert_image(self.database, self.doc, image, self.user)
                self.black_list.append(image)
            self.doc.end_cell()

        self.doc.end_row()
        self.doc.end_table()

    def __write_referenced_citations(self, handle):
        """
        This procedure writes out citation data related to the source.
        """

        self.doc.start_paragraph('REPO-Section')
        self.doc.end_paragraph()

        citation = self.database.get_citation_from_handle(handle)

        page = citation.get_page()
        quay = citation.get_confidence_level()
        date = citation.serialize()[2]

        if quay != 2 or self.incl_empty: # default quality = 2
            self.doc.start_paragraph('REPO-Section2')
            self.doc.write_text(self._('Confidence level:') + space)
            self.doc.write_text(str(quay))
            self.doc.end_paragraph()
        else:
            self.doc.start_paragraph('REPO-Section2')
            self.doc.write_text(self._('Citation:') + space)
            self.doc.end_paragraph()

        if date:
            if date[4] != "" or self.incl_empty:
                self.doc.start_paragraph('REPO-Section2')
                self.doc.write_text(self._('Date:') + space)
                self.doc.write_text(date[4])
                self.doc.end_paragraph()

        if page != "" or self.incl_empty:
            self.doc.start_paragraph('REPO-Section2')
            self.doc.write_text(self._('Page:') + space)
            self.doc.write_text(page)
            self.doc.end_paragraph()

        if citation.get_citation_child_list() and self.incl_media:
            medialist = citation.get_citation_child_list()
            for media_handle in medialist:
                if media_handle not in self.black_list:
                    photos = citation.get_media_list()
                    self.__write_referenced_media(photos, media_handle)
                self.black_list.append(media_handle)

#------------------------------------------------------------------------
#
# RepositoryOptions
#
#------------------------------------------------------------------------

class RepositoryOptionsAlt(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        MenuReportOptions.__init__(self, name, dbase)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the place report.
        """

        common_name = _('Report Options')
        repository_name = _('Repositories')
        source_name = _('Sources')

        # Reload filters to pick any new ones
        CustomFilters = None
        from gramps.gen.filters import CustomFilters, GenericFilter

        opt = FilterOption(_("Select using filter"), 0)
        opt.set_help(_("Selection with a filter"))
        filter_list = []
        filter_list.append(GenericFilter())
        filter_list.extend(CustomFilters.get_filters('Repository'))
        opt.set_filters(filter_list)
        menu.add_option(repository_name, "filter", opt)

        from functools import partial
        addopt = partial(menu.add_option, common_name)
        raddopt = partial(menu.add_option, repository_name)
        saddopt = partial(menu.add_option, source_name)

        incintern = BooleanOption(_("Include repository's urls"), False)
        incintern.set_help(_('Whether to include urls on repository.'))
        raddopt('incintern', incintern)

        incaddres = BooleanOption(_("Include repository's address"), False)
        incaddres.set_help(_('Whether to include addresses on repository.'))
        raddopt('incaddres', incaddres)

        incauthor = BooleanOption(_("Include source's author"), False)
        incauthor.set_help(_('Whether to include author.'))
        saddopt('incauthor', incauthor)

        incabbrev = BooleanOption(_("Include source's abbreviation"), False)
        incabbrev.set_help(_('Whether to include abbreviation.'))
        saddopt('incabbrev', incabbrev)

        incpublic = BooleanOption(_("Include source's publication information"), False)
        incpublic.set_help(_('Whether to include publication information.'))
        saddopt('incpublic', incpublic)

        incdatamp = BooleanOption(_("Include source's data"), False)
        incdatamp.set_help(_('Whether to include keys and values.'))
        saddopt('incdatamp', incdatamp)

        inclunote = BooleanOption(_('Include notes'), False)
        inclunote.set_help(_('Whether to include notes on repositories and sources.'))
        addopt('inclunote', inclunote)

        inclmedia = BooleanOption(_('Include media'), False)
        inclmedia.set_help(_('Whether to include media.'))
        addopt('inclmedia', inclmedia)

        inclcitat = BooleanOption(_('Include citations'), False)
        inclcitat.set_help(_('Whether to include citations on sources.'))
        saddopt('inclcitat', inclcitat)

        incprivat = BooleanOption(_('Include private records'), False)
        incprivat.set_help(_('Whether to include repositories and sources marked as private.'))
        addopt('incprivat', incprivat)

        incempty = BooleanOption(_('Display empty values'), False)
        incempty.set_help(_('Whether to include key records with empty values.'))
        addopt('incempty', incempty)

        stdoptions.add_localization_option(menu, common_name)

    def make_default_style(self, default_style):
        """
        Make the default output style for the report.
        """

        self.default_style = default_style
        self.__report_title_style()
        self.__repository_title_style()
        self.__section_style()
        self.__child_section_style()
        self.__note_style()
        self.__media_style()

    def __report_title_style(self):
        """
        Define the style used for the report title
        """

        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=20, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(1)
        para.set_bottom_border(1)
        para.set_top_margin(ReportUtils.pt2cm(20))
        para.set_bottom_margin(ReportUtils.pt2cm(20))
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_('The style used for the title of the report.'))
        self.default_style.add_paragraph_style('REPO-ReportTitle', para)

    def __repository_title_style(self):
        """
        Define the style used for the repository title
        """

        font = FontStyle()
        font.set(face=FONT_SERIF, size=14, italic=0, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_top_margin(ReportUtils.pt2cm(10))
        para.set_bottom_margin(ReportUtils.pt2cm(7))
        para.set_description(_('The style used for repository title.'))
        self.default_style.add_paragraph_style('REPO-RepositoryTitle', para)

    def __section_style(self):
        """
        Define the style used for primary section
        """

        font = FontStyle()
        font.set(face=FONT_SERIF, size=10, italic=0, bold=0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0, lmargin=0.5)
        para.set_top_margin(ReportUtils.pt2cm(7))
        para.set_bottom_margin(ReportUtils.pt2cm(5))
        para.set_description(_('The style used for each section.'))
        self.default_style.add_paragraph_style('REPO-Section', para)

    def __child_section_style(self):
        """
        Define the style used for secondary section
        """

        font = FontStyle()
        font.set(face=FONT_SERIF, size=10, italic=1, bold=0)
        para = ParagraphStyle()
        para.set_font(font)
        para.set(first_indent=0, lmargin=1)
        para.set_top_margin(ReportUtils.pt2cm(1))
        para.set_bottom_margin(ReportUtils.pt2cm(1))
        para.set_description(_('The style used for child section.'))
        self.default_style.add_paragraph_style('REPO-Section2', para)

    def __note_style(self):
        """
        Define the style used for note
        """

        para = ParagraphStyle()
        para.set(first_indent=0.75, lmargin=.75)
        para.set_top_margin(ReportUtils.pt2cm(3))
        para.set_bottom_margin(ReportUtils.pt2cm(3))
        para.set_description(_('The basic style used for the note display.'))
        self.default_style.add_paragraph_style("REPO-Note", para)

    def __media_style(self):
        """
        Define the style used for media
        """

        tbl = TableStyle()
        tbl.set_width(100)
        tbl.set_columns(3)
        tbl.set_column_width(0, 32.3)
        tbl.set_column_width(1, 32.3)
        tbl.set_column_width(2, 32.3)
        self.default_style.add_table_style('REPO-MediaTab', tbl)

        cell = TableCellStyle()
        cell.set_padding(0.5)
        cell.set_top_border(1)
        cell.set_bottom_border(1)
        cell.set_right_border(0.5)
        cell.set_left_border(0.5)
        self.default_style.add_cell_style("REPO-MediaCell", cell)
