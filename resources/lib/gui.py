import os
import urllib2
import threading
import simplejson
import datetime
from xml.dom.minidom import parse
from time import sleep, mktime

import BeautifulSoup
import feedparser

import xbmc, xbmcgui, xbmcaddon

import util


# Control ids
GAME_LISTS = (50, 51, 52, 53, 54, 55, 56, 57, 58)
CONTROL_SCROLLBARS = (2200, 2201, 60, 61, 62)
CONTROL_GAMES_GROUP_START = 50
CONTROL_LABEL_MSG = 4000

# Action ids
ACTION_PREVIOUS_MENU = 10

USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:26.0) Gecko/20100101 Firefox/26.0"

_articles = {}


class FetchThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        self.feeds_path = xbmc.translatePath('special://userdata/RssFeeds.xml').decode('utf-8')
        self.json_path = xbmc.translatePath('special://userdata/RssExplorer.json').decode('utf-8')
        self._running = True
        super(FetchThread, self).__init__(*args, **kwargs)

    def run(self):
        global _articles
        print "RUN RUN RUN %s" % self.feeds_path
        while self._running:
            articles = {}
            for feed in parse(self.feeds_path).getElementsByTagName('feed'):
                url = feed.firstChild.toxml()
                print url
                parsed = feedparser.parse(url, agent=USER_AGENT)
                for entry in parsed.entries:
                    print entry.link

                    # Have we already processed this item?
                    if entry.link in _articles:
                        articles[entry.link] = _articles[entry.link]
                        continue

                    # Fetch the link
                    request = urllib2.Request(
                        entry.link, headers={'User-Agent': USER_AGENT}
                    )
                    try:
                        response = urllib2.urlopen(request)
                    except urllib2.HTTPError:
                        continue

                    # Extract content
                    more_soup = BeautifulSoup.BeautifulSoup(response.read())
                    #node = more_soup.select(feed.css_content_selector)
                    node = more_soup
                    if not node:
                        continue
                    content = node[0].renderContents()

                    # Add
                    print entry
                    date = getattr(entry, 'published_parsed', None) \
                        or getattr(entry, 'updated_parsed', None) \
                        or now_struct
                    date = mktime(date)
                    articles[entry.link] = {
                        'url': entry.link,
                        'date': date, 
                        'title': entry.title, 
                        'description': entry.description, 
                        'content': content
                    }

            # Write to file
            fp = open(window.json_path, 'w')
            try:
                fp.write(simplejson.dumps(articles))
            finally:
                fp.close()

            # Sleep
            #sleep(600)
            self._running = False

    def kill(self):
        self._running = False


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
        print "ON INIT"
        self.feeds_path = xbmc.translatePath('special://userdata/RssFeeds.xml').decode('utf-8')
        self.json_path = xbmc.translatePath('special://userdata/RssExplorer.json').decode('utf-8')
        self._articles = {}
        self._sorted_articles = []

        xbmc.sleep(util.WAITTIME_UPDATECONTROLS)

        #self.cache_articles()

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

    def cache_articles(self):
        now_struct = datetime.datetime.now().timetuple()
        articles = {}
        for feed in parse(self.feeds_path).getElementsByTagName('feed'):
            url = feed.firstChild.toxml()
            parsed = feedparser.parse(url, agent=USER_AGENT)
            for entry in parsed.entries:

                # Have we already processed this item?
                if entry.link in self._articles:
                    articles[entry.link] = self._articles[entry.link]
                    continue

                # Fetch the link
                request = urllib2.Request(
                    entry.link, headers={'User-Agent': USER_AGENT}
                )
                try:
                    response = urllib2.urlopen(request, timeout=30)
                except urllib2.HTTPError:
                    continue

                # Extract content
                more_soup = BeautifulSoup.BeautifulSoup(response.read())
                #node = more_soup.select(feed.css_content_selector)
                node = [more_soup]
                if not node:
                    continue
                content = node[0].renderContents()

                # Add
                print entry
                date = getattr(entry, 'published_parsed', None) \
                    or getattr(entry, 'updated_parsed', None) \
                    or now_struct
                date = mktime(date)
                articles[entry.link] = {
                    'date': date,
                    'title': entry.title, 
                    'description': entry.description, 
                    'content': content
                }

        # Write to file
        fp = open(self.json_path, 'w')
        try:
            fp.write(simplejson.dumps(articles))
        finally:
            fp.close()

    @property
    def articles(self):
        global _articles
        if _articles:
            return _articles

        if os.path.exists(self.json_path):
            fp = open(self.json_path, 'r')
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
            imagemainViewBackground = u'/home/hedley/emulators/zsnes/artwork/boxfront/Super Adventure Island (US).jpg'
            item.setProperty(util.IMAGE_CONTROL_BACKGROUND, imagemainViewBackground)
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
    

#fetch_thread = FetchThread()
#fetch_thread.start()

ui = UIGameDB('main.xml', util.getAddonInstallPath())
ui.doModal()
del ui

#fetch_thread.kill()
#del fetch_thread
