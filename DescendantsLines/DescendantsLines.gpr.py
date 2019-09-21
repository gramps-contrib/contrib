#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2010 Adam Sampson <ats-familytree@offog.org>
# Copyright (C) 2010 Jerome Rapinat <romjerome@yahoo.fr>
# Copyright (C) 2010, 2012 lcc <lcc.mailaddress@gmail.com>
# Copyright (C) 2015 Don Piercy
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
register(REPORT,
         id    = 'Descendants Lines',
         name  = _("Descendants Lines"),
         description =  _("Produces descendants lines of a person"),
         version = '1.0.23',
         gramps_target_version = "5.1",
         status = STABLE,
         fname = 'DescendantsLines.py',
         category = CATEGORY_DRAW,
         reportclass = 'DescendantsLinesReport',
         optionclass = 'DescendantsLinesOptions',
         report_modes = [REPORT_MODE_GUI, REPORT_MODE_CLI],
         authors = ['Jerome Rapinat', 'lcc', 'Adam Sampson', 'Don Piercy'],
         authors_email = ['romjerome@yahoo.fr', 'lcc.mailaddress@gmail.com', \
                 'ats-familytree@offog.org', ''],
         require_active = True
         )
