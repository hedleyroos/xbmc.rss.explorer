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
IMAGE_CONTROL_GAMELIST = 'gamelist'
IMAGE_CONTROL_GAMELISTSELECTED = 'gamelistselected'
IMAGE_CONTROL_GAMEINFO_BIG = 'gameinfobig'

IMAGE_CONTROL_GAMEINFO_UPPERLEFT = 'gameinfoupperleft'
IMAGE_CONTROL_GAMEINFO_UPPERRIGHT = 'gameinfoupperright'
IMAGE_CONTROL_GAMEINFO_LOWERLEFT = 'gameinfolowerleft'
IMAGE_CONTROL_GAMEINFO_LOWERRIGHT = 'gameinfolowerright'

IMAGE_CONTROL_GAMEINFO_UPPER = 'gameinfoupper'
IMAGE_CONTROL_GAMEINFO_LOWER = 'gameinfolower'
IMAGE_CONTROL_GAMEINFO_LEFT = 'gameinfoleft'
IMAGE_CONTROL_GAMEINFO_RIGHT = 'gameinforight'

IMAGE_CONTROL_1 = 'extraImage1'
IMAGE_CONTROL_2 = 'extraImage2'
IMAGE_CONTROL_3 = 'extraImage3'


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