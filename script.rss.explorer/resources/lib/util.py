import os
import sys
import re

import time
import xbmc, xbmcaddon


SCRIPTNAME = 'RSS Explorer'
SCRIPTID = 'script.rss.explorer'
CURRENT_CONFIG_VERSION = '0.1'

__addon__ = xbmcaddon.Addon(id='%s' %SCRIPTID)
__language__ = __addon__.getLocalizedString

# Time that xbmc needs to update controls (before we can rely on position)
WAITTIME_UPDATECONTROLS = 100

LOG_LEVEL_ERROR = 0
LOG_LEVEL_WARNING = 1
LOG_LEVEL_INFO = 2
LOG_LEVEL_DEBUG = 3

CURRENT_LOG_LEVEL = LOG_LEVEL_INFO

IMAGE_CONTROL_BACKGROUND = 'background'
IMAGE_CONTROL_ARTICLEINFO_BIG = 'articleinfobig'


def getEnvironment():
	return (os.environ.get('OS', 'win32'), 'win32',)[os.environ.get('OS', 'win32') == 'xbox']


def localize(id):
	try:
		return __language__(id)
	except:
		return "Sorry. No translation available for string with id: " +str(id)


def getAddonDataPath():
	path = xbmc.translatePath('special://profile/addon_data/%s' %(SCRIPTID))
	if not os.path.exists(path):
		try:
			os.makedirs(path)
		except:
			path = ''	
	return path


def getAddonInstallPath():
	return __addon__.getAddonInfo('path')


def clean_content(content):
    """Convert and strip markup. Bleach pulls in too many dependencies so fall
    back to regex."""
    # Strip linebreaks
    s = content.replace('\n', ' ')
    # Collapse whitespace
    s = re.sub(' +', ' ', s)
    # Make br's linebreaks
    s = s.replace('<br>', '\n')
    s = s.replace('<br />', '\n')
    s = s.replace('<br/>', '\n')
    # Prep paragraphs to become breaks
    s = s.replace('<p', '\n\n<p')
    # Collapse linebreaks
    #s = re.sub('\n+', '\n', s)
    # Strip all tags
    # todo: beautifulsoup is easy to pull in, so perhaps use that
    s = re.sub(r'<[^>]*>', '', s)
    return s.strip()
