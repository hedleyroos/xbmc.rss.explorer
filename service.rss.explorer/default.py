#!/usr/bin/python
# -*- coding: utf-8 -*-
#
#     Copyright (C) 2013 Team-XBMC
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#

import os
import datetime
import urllib2
import simplejson
from xml.dom.minidom import parse
from time import mktime

import xbmc, xbmcaddon

import BeautifulSoup
import feedparser


USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:26.0) Gecko/20100101 Firefox/26.0"
FETCH_EVERY_SECONDS = 600

#xbmc.executebuiltin("XBMC.Notification("+name+","+number+",7000,special://home/addons/script.yaclistener/phone.png)")

def fetch(feeds_path, addon_data_path):

    # Paths
    json_path = os.path.join(addon_data_path, 'data.json')
    images_path = os.path.join(addon_data_path, 'images')

    # Prepare directories
    if not os.path.exists(addon_data_path):
        os.mkdir(addon_data_path)
    if not os.path.exists(images_path):
        os.mkdir(images_path)

    # Load current articles
    current_articles = {}
    if os.path.exists(json_path):
        fp = open(json_path, 'r')
        try:
            current_articles = simplejson.loads(fp.read())
        finally:
            fp.close()

    now_struct = datetime.datetime.now().timetuple()
    articles = {}
    counter = 1
    for feed in parse(feeds_path).getElementsByTagName('feed'):

        # Abort?
        if xbmc.abortRequested:
            return

        url = feed.firstChild.toxml()
        parsed = feedparser.parse(url, agent=USER_AGENT)

        for entry in parsed.entries:

            # Abort?
            if xbmc.abortRequested:
                return

            # Have we already processed this item?
            if entry.link in articles:
                continue
            if entry.link in current_articles:
                articles[entry.link] = current_articles[entry.link]
                continue

            # Fetch the link
            request = urllib2.Request(
                entry.link, headers={'User-Agent': USER_AGENT}
            )
            try:
                response = urllib2.urlopen(request, timeout=10)
            except urllib2.HTTPError:
                continue

            # Extract content
            more_soup = BeautifulSoup.BeautifulSoup(response.read())
            #node = more_soup.select(feed.css_content_selector)
            node = [more_soup]
            if not node:
                continue
            content = node[0].renderContents()

            # Fetch image if possible
            image_name = ''
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('image/'):
                    request = urllib2.Request(
                        enclosure.href, headers={'User-Agent': USER_AGENT}
                    )
                    try:
                        response = urllib2.urlopen(request, timeout=10)
                    except urllib2.HTTPError:
                        pass
                    else:
                        # Don't trust filename in URL because FS may struggle
                        # with eg. unicode filenames.
                        image_name = urllib2.urlparse.urlparse(
                            enclosure.href
                        ).path.split('/')[-1]
                        image_name ='%s.%s' \
                            % (hash(image_name), image_name.split('.')[-1])
                        pth = os.path.join(images_path, image_name)
                        fp = open(pth, 'wb')
                        try:
                            fp.write(response.read())
                        finally:
                            fp.close()
                        break

            # Add
            date = getattr(entry, 'published_parsed', None) \
                or getattr(entry, 'updated_parsed', None) \
                or now_struct
            date = mktime(date)
            print "counter = %s" % counter
            articles[entry.link] = {
                'date': date,
                'title': entry.title, 
                'description': entry.description, 
                'content': content,
                'image_name': image_name
            }

            counter += 1

    # Write to file
    fp = open(json_path, 'w')
    try:
        fp.write(simplejson.dumps(articles))
    finally:
        fp.close()


if __name__ == '__main__':
    feeds_path = xbmc.translatePath('special://userdata/RssFeeds.xml').decode('utf-8')
    addon_data_path = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/').decode('utf-8')
    counter = 0
    while not xbmc.abortRequested:
        if counter % FETCH_EVERY_SECONDS == 0:
            fetch(feeds_path, addon_data_path)
        xbmc.sleep(1000)
        counter += 1
