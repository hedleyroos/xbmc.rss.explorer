import os
import simplejson
import datetime

import xbmc, xbmcgui, xbmcaddon

import util


# Control ids
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)
CONTROL_GAMES_GROUP_START = 50
CONTROL_LABEL_MSG = 4000

# Action ids
ACTION_PREVIOUS_MENU = 10

service_data_path = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/').decode('utf-8')
json_path = os.path.join(service_data_path, 'data.json')
images_path = os.path.join(service_data_path, 'images')
_articles = {}


class PopupWindow(xbmcgui.Window):

    def __init__(self, *args, **kwargs):
        super(PopupWindow, self).__init__(*args, **kwargs)
        #url = kwargs.pop('url')
        #content = util.clean_content(_articles.get(url, {}).get('content'))
        content = "ahaha"
        #self.addControl(xbmcgui.ControlLabel(x=190, y=25, width=500, height=25, label=content))
        ctrl = xbmcgui.ControlLabel(x=190, y=25, width=500, height=25)
        ctrl.setLabel('mmmmmmmmmmm')

        #ctrl = xbmcgui.ControlTextBox(x=0, y=0, width=500, height=200)
        #ctrl.setText('xxxxxxxxxxxx'+content)
        #ctrl.setText("this is text")
        self.addControl(ctrl)



    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            self.close()


class UIGameDB(xbmcgui.WindowXML):
        
    def onInit(self):
        print "ON INIT"
        self._articles = {}
        self._sorted_articles = []

        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)

        self.showArticles()
        
        # Always set focus on game list on start
        ctrl = self.getControlById(CONTROL_GAMES_GROUP_START)
        if ctrl is not None:
            self.setFocus(ctrl)

    def onClick(self, controlId):
        #print "onClick: " + str(controlId)
        if (controlId in GAME_LISTS):
            self.launchEmu()

    def onFocus(self, controlId):
        self.selectedControlId = controlId

    @property
    def articles(self):
        global _articles
        if _articles:
            return _articles

        if os.path.exists(json_path):
            fp = open(json_path, 'r')
            _articles = simplejson.loads(fp.read())
            fp.close()

        # Legacy
        for k, v in _articles.items():
            if 'url' not in v:
                _articles[k]['url'] = k

        return _articles

    @property
    def sorted_articles(self):
        li = self.articles.values()
        li.sort(lambda a,b: cmp(b['date'], a['date']))
        return li

    def showArticles(self):
        self.clearList()
        self.writeMsg("Loading articles...")

        for di in self.sorted_articles:
            item = xbmcgui.ListItem(di['title'], di['title'])
            item.setProperty('url', di['url'])
            if di['image_name']:
                pth = os.path.join(images_path, di['image_name'])
                item.setProperty(util.IMAGE_CONTROL_BACKGROUND, pth)
                item.setProperty(util.IMAGE_CONTROL_GAMEINFO_BIG, pth)
            self.addItem(item)
        #xbmc.executebuiltin("Container.SortDirection")
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

        self.setCurrentListPosition(pos)
    
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
