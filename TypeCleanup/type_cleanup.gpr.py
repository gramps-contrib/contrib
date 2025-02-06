#
# Gramps - a GTK+/GNOME based genealogy program
#
# Copyright (C) 2016      Paul Culley
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
# Type Cleanup tool
#
# ------------------------------------------------------------------------

register(
    TOOL,
    id="typecleanup",
    name=_("Type Cleanup"),
    description=_("Clean up (remove) custom types"),
    version = '1.0.13',
    gramps_target_version="6.0",
    status=STABLE,
    fname="type_cleanup.py",
    authors=["Paul Culley"],
    authors_email=["paulr2787@gmail.com"],
    category=TOOL_UTILS,
    toolclass="TypeCleanup",
    optionclass="TypeCleanupOptions",
    tool_modes=[TOOL_MODE_GUI],
    help_url="Addon:Types_Cleanup_Tool",
)
