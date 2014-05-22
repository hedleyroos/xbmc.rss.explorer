# Copyright (C) 2009-2013 Hedley Roos (hedleyroos@gmail.com)
#
# This program is free software; you can redistribute it and/or modify it under the terms 
# of the GNU General Public License as published by the Free Software Foundation; 
# either version 2 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. 
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with this program; 
# if not, see <http://www.gnu.org/licenses/>.

# The GUI is heavily inspired by script.games.rom.collection.browser by Malte
# Loepmann.

import os, sys, re

import xbmcaddon


# Expand sys.path
addon = xbmcaddon.Addon(id='script.rss.explorer')
addon_path = addon.getAddonInfo('path')
resource_path = os.path.join(addon_path, 'resources')
sys.path.append(os.path.join(resource_path, 'lib'))

if __name__ == '__main__':
    import gui
