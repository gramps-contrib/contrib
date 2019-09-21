#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2015      Nick Hall
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
#

#------------------------------------------------------------------------
#
# GetGOV Gramplet
#
#------------------------------------------------------------------------

register(GRAMPLET,
         id = "GetGOV Gramplet",
         name = _("GetGOV"),
         description = _("Gramplet to get places from the GOV database"),
         status = STABLE,
         version = '1.0.12',
         gramps_target_version = '5.1',
         fname = "getgov.py",
         gramplet = 'GetGOV',
         height = 375,
         detached_width = 510,
         detached_height = 480,
         expand = True,
         gramplet_title = _("GetGOV"),
         help_url="GetGOV Gramplet",
         include_in_listing = True,
        )
