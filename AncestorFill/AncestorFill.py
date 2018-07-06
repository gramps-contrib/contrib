#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2000-2007  Donald N. Allingham
# Copyright (C) 2007-2009  Brian G. Matherly
# Copyright (C) 2010       Jakim Friant
# Copyright (C) 2012       Jerome Rapinat
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
# $Id: AncestorFill.py 18915 2012-02-17 16:51:40Z romjerome $

"""Reports/Text Reports/AncestorFill Report"""

#------------------------------------------------------------------------
#
# python modules
#
#------------------------------------------------------------------------
import copy
import os
import gettext
from collections import defaultdict

#------------------------------------------------------------------------
#
# gramps modules
#
#------------------------------------------------------------------------
from gramps.gen.const import GRAMPS_LOCALE as glocale
from gramps.gen.errors import ReportError
from gramps.gen.lib import ChildRefType
from gramps.gen.plug.menu import NumberOption, PersonOption, BooleanOption
from gramps.gen.plug.docgen import (IndexMark, FontStyle, ParagraphStyle,
                                    FONT_SANS_SERIF, INDEX_TYPE_TOC,
                                    PARA_ALIGN_CENTER)
from gramps.gen.plug.report import Report
from gramps.gen.plug.report import MenuReportOptions
from gramps.gen.plug.report import stdoptions
from gramps.gen.plug.report import utils

try:
    _trans = glocale.get_addon_translator(__file__)
except ValueError:
    _trans = glocale.translation
_ = _trans.gettext

#------------------------------------------------------------------------
#
# AncestorFillReport
#
#------------------------------------------------------------------------
class AncestorFillReport(Report):
    """
    AncestorFill Report class
    """
    def __init__(self, database, options, user):
        """
        Create the AncestorFillReport object that produces the AncestorFill report.

        The arguments are:

        database        - the GRAMPS database instance
        options         - instance of the Options class for this report
        user            - a gen.user.User() instance

        This report needs the following parameters (class variables)
        that come in the options class.

        gen       - Maximum number of generations to include.
        name_format   - Preferred format to display names
        Filled_digit     - Number of decimal for the fill percentage

        """
        Report.__init__(self, database, options, user)

        menu = options.menu

        self.set_locale(menu.get_option_by_name('trans').get_value())

        stdoptions.run_name_format_option(self, menu)

        self.trouve = {}
        self.index = defaultdict(list)
        self.gener = defaultdict(lambda : defaultdict(int))
        self.max_generations = menu.get_option_by_name('maxgen').get_value()
        pid = menu.get_option_by_name('pid').get_value()
        self.Filleddigit = menu.get_option_by_name('Filled_digit').get_value()
        self.Collapsedigit = menu.get_option_by_name('Collapsed_digit').get_value()
        self.displayth = menu.get_option_by_name('Display_theoretical').get_value()
        self.center_person = database.get_person_from_gramps_id(pid)
        if self.center_person is None:
            raise ReportError(_("Person %s is not in the Database") % pid )

    def apply_filter(self, person_handle, index, generation=1):
        """
        Recursive function to walk back all parents of the current person.
        When max_generations are hit, we stop the traversal.
        """

        # check for end of the current recursion level. This happens
        # if the person handle is None, or if the max_generations is hit

        if not person_handle or generation > self.max_generations:
            return

        # retrieve the Person instance from the database from the
        # passed person_handle and find the parents from the list.
        # Since this report is for natural parents (birth parents),
        # we have to handle that parents may not

        person = self.database.get_person_from_handle(person_handle)
        grampsid = person.get_gramps_id()

        if grampsid in self.trouve:
            return


        # store the person in the map based off their index number
        # which is passed to the routine.
        father_handle = None
        mother_handle = None
        for family_handle in person.get_parent_family_handle_list():
            family = self.database.get_family_from_handle(family_handle)

            # filter the child_ref_list to find the reference that matches
            # the passed person. There should be exactly one, but there is
            # nothing that prevents the same child in the list multiple times.

            ref = [ c for c in family.get_child_ref_list()
                    if c.get_reference_handle() == person_handle]
            if ref:

                # If the father_handle is not defined and the relationship is
                # BIRTH, then we have found the birth father. Same applies to
                # the birth mother. If for some reason, the we have multiple
                # people defined as the birth parents, we will select based on
                # priority in the list

                if not father_handle and \
                   ref[0].get_father_relation() == ChildRefType.BIRTH:
                    father_handle = family.get_father_handle()
                if not mother_handle and \
                   ref[0].get_mother_relation() == ChildRefType.BIRTH:
                    mother_handle = family.get_mother_handle()

        # Recursively call the function. It is okay if the handle is None,
        # since routine handles a handle of None

        fatherid = False
        motherid = False
        self.index[person_handle] = []
        if father_handle:
            father = self.database.get_person_from_handle(father_handle)
            fatherid = father.get_gramps_id()
            self.index[grampsid].append(fatherid)
            self.apply_filter(father_handle, index*2, generation+1)
        if mother_handle:
            mother = self.database.get_person_from_handle(mother_handle)
            motherid = mother.get_gramps_id()
            self.index[grampsid].append(motherid)
            self.apply_filter(mother_handle, index*2, generation+1)
        if generation == 1:
            if fatherid:
                self.gener[1][fatherid] = 1
            if motherid:
                self.gener[1][motherid] = 1
        self.trouve[grampsid] = 1


    def write_report(self):
        """
        The routine the actually creates the report. At this point, the document
        is opened and ready for writing.
        """

        name = self._name_display.display(self.center_person)
        self.title = self._("AncestorFill for %s") % name
        self.doc.start_paragraph("ANF-Title")
        mark = utils.get_person_mark(self.database, self.center_person)
        self.doc.write_text('', mark)
        mark = IndexMark(self.title, INDEX_TYPE_TOC, 1)
        self.doc.write_text(self.title, mark)
        self.doc.end_paragraph()
        total = 0
        longueur = 1
        gen = 0
        percent = 100
        nbhand = 1
        implexe = 0
        theor = ''
        self.apply_filter(self.center_person.get_handle(), 1)

        strgen = self._("Generation ")
        strfoundanc = self._("Number of Ancestors found ")
        pctfoundanc = self._("percent of Ancestors found ")
        uniqfoundanc = self._("Number of single Ancestors found ")
        strtheoanc = self._("Number of theoretical Ancestors ")
        strimplex = self._("Pedigree Collapse ")

        if self.displayth:
            form = strgen + "%2d\n" + strfoundanc + "%12d\n" + strtheoanc + str(theor) + "\n" + pctfoundanc +" %." + str(self.Filleddigit) + "f%% " + " \n" + uniqfoundanc + " %6d\n" + strimplex + "%3." + str(self.Collapsedigit) + "f%%"
        else:
            form = strgen + "%2d\n" + strfoundanc + "%12d\n" + pctfoundanc +" %." + str(self.Filleddigit) + "f%% " + " \n" + uniqfoundanc + " %6d\n" + strimplex + "%3." + str(self.Collapsedigit) + "f%%"
            text = form % (gen, longueur, percent, nbhand, implexe)
            self.doc.start_paragraph("ANF-Generation")
            self.doc.write_text(text)
            self.doc.end_paragraph()
        for gen in range(0, self.max_generations):
            nextgen = gen + 1
            for gid in self.gener[gen].keys():
                for id2 in self.index[gid]:
                    if id2:
                        self.gener[nextgen][id2] += self.gener[gen][gid]
            longueur = 0
            nbhand = 0
            msg = "GEN  " + str (nextgen)
            for hand in self.gener[nextgen].keys():
                msg = msg + " " + str(hand)
                longueur += self.gener[nextgen][hand]
                nbhand += 1
            theor = 2 ** nextgen
            percent = longueur * 100.0 / theor
            total = total + longueur
            if not nbhand:
                implexe = 0
            else:
                implexe = float(longueur-nbhand)*100.0 / longueur
            if longueur == 0:
                next
            else:
                self.doc.start_paragraph("ANF-Generation")
                if self.displayth:
                    form = strgen + "%2d\n" + strfoundanc + "%12d\n" + strtheoanc + str(theor) + "\n" + pctfoundanc +" %." + str(self.Filleddigit) + "f%% " + " \n" + uniqfoundanc + " %6d\n" + strimplex + "%3." + str(self.Collapsedigit) + "f%%"
                else:
                    form = strgen + "%2d\n" + strfoundanc + "%12d\n" + pctfoundanc +" %." + str(self.Filleddigit) + "f%% " + " \n" + uniqfoundanc + " %6d\n" + strimplex + "%3." + str(self.Collapsedigit) + "f%%"
                text = form % (nextgen, longueur, percent, nbhand, implexe)
                self.doc.write_text(text)
                self.doc.end_paragraph()
        totalnbanc = len(self.trouve)
        timplexe= ( total - totalnbanc) * 100.0 / total
        strtotalanc = self._("Total Number of Ancestors found ")
        form = strtotalanc + "%d\n"
        totaluniqfoundanc = self._("Total Number of single Ancestors found ")
        form2 = totaluniqfoundanc + "%d\n"
        form3 = strimplex + "%3." + str(self.Collapsedigit) + "f%%"
        text = (form % total) + (form2 % totalnbanc) + (form3 % timplexe)
        self.doc.start_paragraph("ANF-Generation")
        self.doc.write_text(text)
        self.doc.end_paragraph()

        name = self._name_display.display_formal(self.center_person)

#------------------------------------------------------------------------
#
# AncestorOptions
#
#------------------------------------------------------------------------
class AncestorFillOptions(MenuReportOptions):

    """
    Defines options and provides handling interface.
    """

    def __init__(self, name, dbase):
        self.__db = dbase
        self.__pid = None
        MenuReportOptions.__init__(self, name, dbase)

    def get_subject(self):
        """ Return a string that describes the subject of the report. """
        from gramps.gen.display.name import displayer as _nd
        gid = self.__pid.get_value()
        person = self.__db.get_person_from_gramps_id(gid)
        return _nd.display(person)

    def add_menu_options(self, menu):
        """
        Add options to the menu for the ancestor report.
        """
        category_name = _("Report Options")

        self.__pid = PersonOption(_("Center Person"))
        self.__pid.set_help(_("The center person for the report"))
        menu.add_option(category_name, "pid", self.__pid)

        maxgen = NumberOption(_("Generations"), 10, 1, 300)
        maxgen.set_help(_("The number of generations to include in the report"))
        menu.add_option(category_name, "maxgen", maxgen)

        Filleddigit = NumberOption(_("Filled digit"), 10, 1, 50)
        Filleddigit.set_help(_("The number of digits after comma to include in the report for the percentage of ancestor found at a given generation"))
        menu.add_option(category_name, "Filled_digit", Filleddigit)

        Collapsedigit = NumberOption(_("Collapsed digit"), 10, 1, 50)
        Collapsedigit.set_help(_("The number of digits after comma to include in the report for the pedigree Collapse"))
        menu.add_option(category_name, "Collapsed_digit", Collapsedigit)

        displayth = BooleanOption(_("Display theoretical"), False)
        displayth.set_help(_("Whether to display the theoretical number of ancestor by generation"))
        menu.add_option(category_name, "Display_theoretical", displayth)

        stdoptions.add_name_format_option(menu, category_name)

        stdoptions.add_localization_option(menu, category_name)

    def make_default_style(self, default_style):
        """
        Make the default output style for the AncestorFill report.

        There are 3 paragraph styles for this report.

        ANF-Title - The title for the report. The options are:

            Font      : Sans Serif
                        Bold
                        16pt
            Paragraph : First level header
                        0.25cm top and bottom margin
                        Centered

        ANF-Generation - Used for the generation header

            Font      : Sans Serif
                        Italic
                        14pt
            Paragraph : Second level header
                        0.125cm top and bottom margins

        ANF - Normal text display for each entry

            Font      : default
            Paragraph : 1cm margin, with first indent of -1cm
                        0.125cm top and bottom margins
        """

        #
        # ANF-Title
        #
        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=16, bold=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(1)
        para.set_top_margin(0.25)
        para.set_bottom_margin(0.25)
        para.set_alignment(PARA_ALIGN_CENTER)
        para.set_description(_('The style used for the title of the page.'))
        default_style.add_paragraph_style("ANF-Title", para)

        #
        # ANF-Generation
        #
        font = FontStyle()
        font.set(face=FONT_SANS_SERIF, size=14, italic=1)
        para = ParagraphStyle()
        para.set_font(font)
        para.set_header_level(2)
        para.set_top_margin(0.125)
        para.set_bottom_margin(0.125)
        para.set_description(_('The style used for the generation header.'))
        default_style.add_paragraph_style("ANF-Generation", para)

        #
        # ANF-Entry
        #
        para = ParagraphStyle()
        para.set(first_indent=-1.0, lmargin=1.0)
        para.set_top_margin(0.125)
        para.set_bottom_margin(0.125)
        para.set_description(_('The basic style used for the text display.'))
        default_style.add_paragraph_style("ANF-Entry", para)
