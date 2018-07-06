#-------------------------------------------------------------------------
#
# Copyright (C) 2014  Matt Keenan <matt.keenan@gmail.com>
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
#-------------------------------------------------------------------------
register(REPORT,
    id = 'd3-ancestralfanchart',
    name = _('Ancestral Fan Chart'),
    category = CATEGORY_WEB,
    status = STABLE,
    fname = 'AncestralFanChart.py',
    reportclass = 'AncestralFanChartReport',
    optionclass = 'AncestralFanChartOptions',
    report_modes = [REPORT_MODE_GUI, REPORT_MODE_CLI],
    authors = ['Matt Keenan'],
    authors_email = ['matt.keenan@gmail.com'],
    description = _('Generates a web page with a graphical '
                    'representation of ancestors (SVG) '
                    'represented as a Fan Chart from the D3.js '
                    'JavaScript library.'),
    version = '1.0.21',
    gramps_target_version = "5.1",
)
