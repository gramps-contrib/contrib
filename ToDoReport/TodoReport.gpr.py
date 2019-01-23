#
# Gramps - a GTK+/GNOME based genealogy program
#
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
register(REPORT,
    id   = 'TodoReport',
    name = _('Todo Report'),
    description = _("Produces a list of all the notes with a given tag along with the records that it references, the Person, Family, Event, etc."),
    version = '1.2.29',
    gramps_target_version = "5.1",
    status = STABLE,
    fname = 'TodoReport.py',
    authors = ["Jakim Friant"],
    authors_email = ["jakim@friant.org"],
    category = CATEGORY_TEXT,
    reportclass = 'TodoReport',
    optionclass = 'TodoOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_BKI, REPORT_MODE_CLI],
    require_active = False
    )
