
import xbmc, xbmcgui, xbmcaddon
import string, glob, time, array, os, sys, shutil, re
from threading import *

from util import *
import util
import dbupdate, helper, launcher, config
import dialogimportoptions, dialogcontextmenu, dialogprogress, dialogmissinginfo
from config import *
from configxmlupdater import *
import wizardconfigxml
from gamedatabase import *


#Action Codes
# See guilib/Key.h
ACTION_CANCEL_DIALOG = (9,10,51,92,110)
ACTION_PLAYFULLSCREEN = (12,79,227)
ACTION_MOVEMENT_LEFT = (1,)
ACTION_MOVEMENT_RIGHT = (2,)
ACTION_MOVEMENT_UP = (3,)
ACTION_MOVEMENT_DOWN = (4,)
ACTION_MOVEMENT = (1, 2, 3, 4, 5, 6, 159, 160)
ACTION_INFO = (11,)
ACTION_CONTEXT = (117,)


#ControlIds
CONTROL_CONSOLES = 500
CONTROL_GENRE = 600
CONTROL_YEAR = 700
CONTROL_PUBLISHER = 800
CONTROL_CHARACTER = 900
FILTER_CONTROLS = (500, 600, 700, 800, 900,)
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)

CONTROL_GAMES_GROUP_START = 50
CONTROL_GAMES_GROUP_END = 59

CONTROL_BUTTON_CHANGE_VIEW = 2
#CONTROL_BUTTON_FAVORITE = 1000
#CONTROL_BUTTON_SEARCH = 1100
CONTROL_BUTTON_VIDEOFULLSCREEN = (2900, 2901,)
NON_EXIT_RCB_CONTROLS = (500, 600, 700, 800, 900, 2, 1000, 1100)

CONTROL_LABEL_MSG = 4000
CONTROL_BUTTON_MISSINGINFODIALOG = 4001

ACTION_PREVIOUS_MENU = 10


class PopupWindow(xbmcgui.Window):

    def __init__(self, *args, **kwargs):
        super(PopupWindow, self).__init__(*args, **kwargs)
        self.url = kwargs.pop('url')
        self.addControl(xbmcgui.ControlLabel(x=190, y=25, width=500, height=25, label="Noooo " + self.url))

    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


class UIGameDB(xbmcgui.WindowXML):
        
    def onInit(self):
        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)
        self.showGames()
        
        #always set focus on game list on start
        focusControl = self.getControlById(CONTROL_GAMES_GROUP_START)
        if(focusControl != None):
            self.setFocus(focusControl)

    def onClick(self, controlId):
        Logutil.log("onClick: " + str(controlId), util.LOG_LEVEL_DEBUG)
        
        if (controlId in GAME_LISTS):
            Logutil.log("onClick: Launch Emu", util.LOG_LEVEL_DEBUG)
            self.launchEmu()

    def onFocus(self, controlId):
        self.selectedControlId = controlId
        
    def showGames(self):
        self.clearList()
        self.writeMsg("Loading articles")
        count = 0
        from xml.dom.minidom import parse, Document, _write_data, Node, Element
        RssFeedsPath = xbmc.translatePath('special://userdata/RssFeeds.xml').decode("utf-8")
        feedsTree = parse(RssFeedsPath)
        feeds = feedsTree.getElementsByTagName('feed')
        for feed in feeds:
            name = feed.firstChild.toxml()
            item = xbmcgui.ListItem(name, name)
            item.setProperty('url', name)
            imagemainViewBackground = u'/home/hedley/emulators/zsnes/artwork/boxfront/Super Adventure Island (US).jpg'
            item.setProperty(util.IMAGE_CONTROL_BACKGROUND, imagemainViewBackground)
            item.setProperty('year', str(count))
            self.addItem(item)
            count +=1
        xbmc.executebuiltin("Container.SortDirection")
        self.writeMsg("")
        
    def launchEmu(self):
        if not self.getListSize():
            return

        pos = self.getCurrentListPosition()
        if pos == -1:
            pos = 0
        selectedGame = self.getListItem(pos)
        
        if not selectedGame:
            return
                    
        url = selectedGame.getProperty('url')
        window = PopupWindow(url=url)
        window.doModal()
        del window
    
    def exit(self):             
        self.close()

    # Helper methods 
    def getControlById(self, controlId):
        try:
            control = self.getControl(controlId)
        except Exception, (exc):
            #HACK there seems to be a problem with recognizing the scrollbar controls
            if(controlId not in (CONTROL_SCROLLBARS)):
                Logutil.log("Control with id: %s could not be found. Check WindowXML file. Error: %s" % (str(controlId), str(exc)), util.LOG_LEVEL_ERROR)
                self.writeMsg(util.localize(35025) % str(controlId))
            return None
        return control
    
    def writeMsg(self, msg, count=0):
        control = self.getControlById(CONTROL_LABEL_MSG)
        if(control == None):
            Logutil.log("RCB_WARNING: control == None in writeMsg", util.LOG_LEVEL_WARNING)
            return
        try:
            control.setLabel(msg)
        except:
            pass
    

def main():
    settings = util.getSettings()
    skin = settings.getSetting(util.SETTING_RCB_SKIN)
    if(skin == "Confluence"):
        skin = "Default"
    ui = UIGameDB("script-Rom_Collection_Browser-main.xml", util.getAddonInstallPath(), skin, "720p")
    ui.doModal()
    del ui

main()
