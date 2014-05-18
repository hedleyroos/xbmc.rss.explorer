# Copyright (C) 2009-2013 Malte Loepmann (maloep@googlemail.com)
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

# The GUI is heavily inspired by script.games.rom.collection.browser.

import os, sys, re

import xbmcaddon


# Shared resources
addonPath = ''
addon = xbmcaddon.Addon(id='script.rss.explorer')

addonPath = addon.getAddonInfo('path')


BASE_RESOURCE_PATH = os.path.join(addonPath, "resources" )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib" ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "pyparsing" ) )
sys.path.append( os.path.join( BASE_RESOURCE_PATH, "lib", "pyscraper" ) )


# append the proper platforms folder to our path, xbox is the same as win32
env = ( os.environ.get( "OS", "win32" ), "win32", )[ os.environ.get( "OS", "win32" ) == "xbox" ]

# Check to see if using a 64bit version of Linux
if re.match("Linux", env):
    try:
        import platform
        env2 = platform.machine()
        if(env2 == "x86_64"):
            env = "Linux64"
    except:
        pass

sys.path.append( os.path.join( BASE_RESOURCE_PATH, "platform_libraries", env ) )

if __name__ == '__main__':
    import gui
