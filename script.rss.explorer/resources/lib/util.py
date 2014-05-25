import os
import sys
import re
import time
import urllib2
import simplejson

import xbmc, xbmcaddon

import bs4


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


class Convertor:

    def __init__(self):
        domain_json = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/domain.json').decode('utf-8')

        # Load domain info
        self.domain_info = {}
        if os.path.exists(domain_json):
            fp = open(domain_json, 'r')
            try:
                self.domain_info = simplejson.loads(fp.read())
            finally:
                fp.close()

    def _html2text(self, url, html, apply_selectors=False):
        """Convert and strip markup. Bleach pulls in too many dependencies so fall
        back to regex."""

        if apply_selectors:

            # Do we have info for this domain?
            target_domain = urllib2.urlparse.urlparse(url).netloc
            domain_pattern = None
            for pattern in self.domain_info.keys():
                if re.match(r'%s' % pattern, target_domain):
                    domain_pattern = pattern
                    break

            # Extract content
            soup = bs4.BeautifulSoup(html)
            nodes = []
            if domain_pattern:
                selectors = self.domain_info[domain_pattern]['selectors']
                for selector in selectors:
                    nodes.extend(soup.select(selector))
            else:
                # todo: fall back to readability
                print "Convertor.html2text: %s has no defined selectors." % url
                selectors = []
                nodes = [soup]
            if not nodes:
                print "Convertor.html2text: no content extracted for %s with \
                    selectors %s." % (url, str(selectors))
            else:
                # Join
                html = '<br /><br />'.join([unicode(n).strip() for n in nodes])

                # Check for html tag
                if html.find('<html') != -1:
                    print "Convertor.html2text: %s has bad selectors %s." \
                        % (url, str(selectors))

        # todo: regexes to save code and be case insensitive
        # Strip linebreaks
        s = html.replace('\n', ' ')
        # Collapse whitespace
        s = re.sub(' +', ' ', s)
        # Make br's linebreaks
        s = s.replace('<br>', '\n')
        s = s.replace('<br />', '\n')
        s = s.replace('<br/>', '\n')
        # Breaking elements to become linebreaks
        s = s.replace('<p', '\n\n<p')
        s = s.replace('<li', '\n\n<li')
        s = s.replace('<h', '\n\n<h')
        # Collapse introduced linebreaks
        s = re.sub('\n+', '\n\n', s)
        # Strip all tags
        # todo: beautifulsoup is easy to pull in, so perhaps use that
        s = re.sub(r'<[^>]*>', '', s)
        s = s.strip()
        # todo: htmlentities -> ascii, remove comment tags
        return s

    def html2text(self, url, html):
        return self._html2text(url, html)

    def file2text(self, url, path):
        fp = open(path, 'r')
        try:
            html = fp.read()
        finally:
            fp.close()
        return self._html2text(url, html, apply_selectors=True)
