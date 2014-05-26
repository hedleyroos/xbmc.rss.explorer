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
ACTION_MOVE_LEFT = 1
ACTION_MOVE_RIGHT = 2
ACTION_MOVE_UP = 3
ACTION_MOVE_DOWN = 4
ACTION_PAGE_UP = 5
ACTION_PAGE_DOWN = 6
ACTION_NAV_BACK = 92
ACTION_STOP = 13

service_data_path = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/').decode('utf-8')
data_json = os.path.join(service_data_path, 'data.json')
domain_json = os.path.join(service_data_path, 'domain.json')
images_path = os.path.join(service_data_path, 'images')
html_path = os.path.join(service_data_path, 'html')
_articles = {}


class MainWindow(xbmcgui.WindowXML):
        
    def onInit(self):
        self._articles = {}
        self._sorted_articles = []
        self.viewing_detail = False
        self.convertor = util.Convertor()

        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)

        # Hide detail panel
        self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(False)

        # Load articles into navigator
        self.listArticles()
        
        # Focus navigator on start
        ctrl = self.getControlById(CONTROL_LIST_NAVIGATOR)
        if ctrl is not None:
            self.setFocus(ctrl)

    def onClick(self, controlId):
        #print "onClick: " + str(controlId)
        if not self.viewing_detail and (controlId == CONTROL_LIST_NAVIGATOR):
            self.showArticle()

    def onFocus(self, controlId):
        self.selectedControlId = controlId

    @property
    def articles(self):
        global _articles
        if _articles:
            return _articles

        if os.path.exists(data_json):
            fp = open(data_json, 'r')
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

    def listArticles(self):
        self.clearList()
        xbmc.executebuiltin('Notification(Loading articles,,/icon.png)')

        counter = 1
        for di in self.sorted_articles:
            item = xbmcgui.ListItem(di['title'], di['title'])
            item.setProperty('url', di['url'])
            item.setProperty('html_name', di['html_name'])
            if di['image_name']:
                pth = os.path.join(images_path, di['image_name'])
                item.setProperty(util.IMAGE_CONTROL_BACKGROUND, pth)
                item.setProperty(util.IMAGE_CONTROL_ARTICLEINFO_BIG, pth)
            description = self.convertor.html2text(di['url'], di['description'])
            item.setProperty('description', description)
            item.setProperty(
                'date', 
                datetime.datetime.utcfromtimestamp(
                    di['date']
                ).strftime('%d %B %Y %H:%I')
            )
            self.addItem(item)
            counter += 1
        self.writeMsg("")
       
    def onAction(self, action):
        if action == ACTION_STOP:
            self.close()

        elif action == ACTION_PREVIOUS_MENU:
            if self.viewing_detail:
                ctrl = self.getControlById(CONTROL_LIST_NAVIGATOR)
                ctrl.setVisible(True)
                self.setFocus(ctrl)
                self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(False)
                self.viewing_detail = False
            else:
                self.close()

        elif self.viewing_detail and (action == ACTION_MOVE_LEFT):
            # todo: condense and use conditions in xml template
            ctrl = self.getControlById(CONTROL_LIST_NAVIGATOR)
            ctrl.setVisible(True)
            self.setFocus(ctrl)
            self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(False)
            self.viewing_detail = False

        elif not self.viewing_detail and (action == ACTION_MOVE_RIGHT):
            self.showArticle()

    def showArticle(self):
        if not self.getListSize():
            return

        # Load content if required. Loading is deferred because content may be
        # large.
        pos = self.getCurrentListPosition()
        if pos == -1:
            pos = 0
        item = self.getListItem(pos)
        load = False
        if not item.getProperty('content'):
            item.setProperty('content', 'Loading...')
            load = True
        
        # Make detail panel visible, focus control group
        # todo: condense and use conditions in xml template
        self.getControlById(CONTROL_TEXTBOX_DETAIL).setVisible(True)
        ctrl = self.getControlById(CONTROL_GROUP_DETAIL)
        self.setFocus(ctrl)
        self.getControlById(CONTROL_LIST_NAVIGATOR).setVisible(False)
        self.viewing_detail = True

        if load:
            content = self.convertor.file2text(
                item.getProperty('url'),
                os.path.join(html_path, item.getProperty('html_name'))
            )
            item.setProperty('content', content)

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
