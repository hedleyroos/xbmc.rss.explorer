from xml.dom.minidom import parse

import xbmc, xbmcgui, xbmcaddon

import util


# Control ids
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)
CONTROL_GAMES_GROUP_START = 50
CONTROL_LABEL_MSG = 4000

# Action ids
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
        
        # Always set focus on game list on start
        focusControl = self.getControlById(CONTROL_GAMES_GROUP_START)
        if(focusControl != None):
            self.setFocus(focusControl)

    def onClick(self, controlId):
        #print "onClick: " + str(controlId)
        if (controlId in GAME_LISTS):
            self.launchEmu()

    def onFocus(self, controlId):
        self.selectedControlId = controlId
        
    def showGames(self):
        self.clearList()
        self.writeMsg("Loading articles")
        count = 0
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
            # There seems to be a problem with recognizing the scrollbar controls
            if(controlId not in (CONTROL_SCROLLBARS)):
                #print "Control with id: %s could not be found. Check WindowXML file. Error: %s" % (str(controlId), str(exc))
                self.writeMsg(util.localize(35025) % str(controlId))
            return None
        return control
    
    def writeMsg(self, msg, count=0):
        control = self.getControlById(CONTROL_LABEL_MSG)
        if(control == None):
            return
        try:
            control.setLabel(msg)
        except:
            pass
    

ui = UIGameDB('main.xml', util.getAddonInstallPath())
ui.doModal()
del ui
