import os
import simplejson
import datetime

import xbmc, xbmcgui, xbmcaddon

import util


# Control ids
CONTROL_LIST_NAVIGATOR = 52
CONTROL_SCROLLBARS = (61, 8889)
CONTROL_LABEL_MSG = 4000
CONTROL_GROUP_DETAIL = 201
CONTROL_TEXTBOX_DETAIL = 8888

# Action ids
# https://github.com/xbmc/xbmc/blob/master/xbmc/guilib/Key.h
ACTION_PREVIOUS_MENU = 10
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGE_UP = 5
ACTION_PAGE_DOWN = 6

service_data_path = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/').decode('utf-8')
json_path = os.path.join(service_data_path, 'data.json')
images_path = os.path.join(service_data_path, 'images')
_articles = {}


class MainWindow(xbmcgui.WindowXML):
        
    def onInit(self):
        self._articles = {}
        self._sorted_articles = []
        self.viewing_detail = False

        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)

        # Hide detail panel
        self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(False)

        # Load articles into navigator
        self.showArticles()
        
        # Focus navigator on start
        ctrl = self.getControlById(CONTROL_LIST_NAVIGATOR)
        if ctrl is not None:
            self.setFocus(ctrl)

    def onClick(self, controlId):
        #print "onClick: " + str(controlId)
        if controlId == CONTROL_LIST_NAVIGATOR:
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
        xbmc.executebuiltin('Notification(Loading articles,,/icon.png)')

        for di in self.sorted_articles:
            item = xbmcgui.ListItem(di['title'], di['title'])
            item.setProperty('url', di['url'])
            if di['image_name']:
                pth = os.path.join(images_path, di['image_name'])
                item.setProperty(util.IMAGE_CONTROL_BACKGROUND, pth)
                item.setProperty(util.IMAGE_CONTROL_ARTICLEINFO_BIG, pth)
            content = util.clean_content(di['content'])
            item.setProperty('content', content)
            description = util.clean_content(di['description'])
            item.setProperty('description', description)
            item.setProperty(
                'date', 
                datetime.datetime.utcfromtimestamp(
                    di['date']
                ).strftime('%d %B %Y %H:%I')
            )
            self.addItem(item)
        #xbmc.executebuiltin("Container.SortDirection")
        self.writeMsg("")
       
    def onAction(self, action):
        if action == ACTION_PREVIOUS_MENU:
            if self.viewing_detail:
                ctrl = self.getControlById(CONTROL_LIST_NAVIGATOR)
                ctrl.setVisible(True)
                self.setFocus(ctrl)
                self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(False)
                self.viewing_detail = False
            else:
                self.close()

    def launchEmu(self):
        if not self.getListSize():
            return

        # Make detail panel visible, focus control group
        self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(True)
        ctrl = self.getControlById(CONTROL_GROUP_DETAIL)
        self.setFocus(ctrl)
        self.getControlById(CONTROL_LIST_NAVIGATOR).setVisible(False)
        self.viewing_detail = True

    def getControlById(self, controlId):
        try:
            control = self.getControl(controlId)
        except Exception, (exc):
            # getControl ignores scrollbar controls
            if (controlId not in (CONTROL_SCROLLBARS)):
                raise
            return None
        return control
    
    def writeMsg(self, msg, count=0):
        control = self.getControlById(CONTROL_LABEL_MSG)
        if control is None:
            return
        try:
            control.setLabel(msg)
        except:
            pass
    

window = MainWindow('main.xml', util.getAddonInstallPath())
window.doModal()
del window
