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
import socket
from xml.dom.minidom import parse
from time import mktime

import xbmc, xbmcaddon

import feedparser


USER_AGENT = "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:26.0) Gecko/20100101 Firefox/26.0"
FETCH_EVERY_SECONDS = 600


def fetch(feeds_path, addon_data_path):

    # Paths
    data_json = os.path.join(addon_data_path, 'data.json')
    domain_json = os.path.join(addon_data_path, 'domain.json')
    images_path = os.path.join(addon_data_path, 'images')
    html_path = os.path.join(addon_data_path, 'html')

    # Prepare directories
    if not os.path.exists(addon_data_path):
        os.mkdir(addon_data_path)
    if not os.path.exists(images_path):
        os.mkdir(images_path)
    if not os.path.exists(html_path):
        os.mkdir(html_path)

    # Load current articles
    current_articles = {}
    if os.path.exists(data_json):
        fp = open(data_json, 'r')
        try:
            current_articles = simplejson.loads(fp.read())
        finally:
            fp.close()

    # Fetch latest domain.json file
    request = urllib2.Request(
        'https://raw.githubusercontent.com/hedleyroos/xbmc.rss.explorer/develop/domain.json.in'
        , headers={'User-Agent': USER_AGENT}
    )
    try:
        response = urllib2.urlopen(request, timeout=10)
        data = response.read()
    except (urllib2.HTTPError, socket.timeout):
        pass
    else:
        fp = open(domain_json, 'w')
        try:
            fp.write(data)
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
                data = response.read()
            except (urllib2.HTTPError, socket.timeout):
                continue

            # Some feeds redirect so get real url
            actual_url = response.geturl()
            if actual_url in current_articles:
                articles[actual_url] = current_articles[actual_url]
                continue

            print "fetch: processing %s" % actual_url

            # Write html to disk
            html_name = str(hash(actual_url))
            pth = os.path.join(html_path, html_name)
            fp = open(pth, 'wb')
            try:
                fp.write(data)
            finally:
                fp.close()

            # Fetch image if possible
            image_name = ''
            for enclosure in entry.enclosures:
                if enclosure.type.startswith('image/'):
                    request = urllib2.Request(
                        enclosure.href, headers={'User-Agent': USER_AGENT}
                    )
                    try:
                        response = urllib2.urlopen(request, timeout=10)
                        data = response.read()
                    except (urllib2.HTTPError, socket.timeout):
                        pass
                    else:
                        # Don't trust filename in URL because FS may struggle
                        # with eg. unicode filenames.
                        extension = urllib2.urlparse.urlparse(
                            enclosure.href
                        ).path.split('/')[-1].split('.')[-1]
                        image_name ='%s.%s' % (hash(enclosure.href), extension)
                        pth = os.path.join(images_path, image_name)
                        fp = open(pth, 'wb')
                        try:
                            fp.write(data)
                        finally:
                            fp.close()
                        break

            # Add
            date = getattr(entry, 'published_parsed', None) \
                or getattr(entry, 'updated_parsed', None) \
                or now_struct
            date = mktime(date)
            articles[actual_url] = {
                'date': date,
                'title': entry.title, 
                'description': entry.description, 
                'image_name': image_name,
                'html_name': html_name
            }

            counter += 1

    # Write data to disk
    fp = open(data_json, 'w')
    try:
        fp.write(simplejson.dumps(articles, indent=4))
    finally:
        fp.close()

    # Remove stale images
    for k, v in current_articles.items():
        if v['image_name'] and (k not in articles):
            try:
                os.remove(os.path.join(images_path, v['image_name']))
            except IOError:
                pass

    # Remove stale html
    for k, v in current_articles.items():
        if v['html_name'] and (k not in articles):
            try:
                os.remove(os.path.join(html_path, v['html_name']))
            except IOError:
                pass


if __name__ == '__main__':
    feeds_path = xbmc.translatePath('special://userdata/RssFeeds.xml').decode('utf-8')
    addon_data_path = xbmc.translatePath('special://userdata/addon_data/service.rss.explorer/').decode('utf-8')
    counter = 0
    while not xbmc.abortRequested:
        if counter % FETCH_EVERY_SECONDS == 0:
            fetch(feeds_path, addon_data_path)
        xbmc.sleep(1000)
        counter += 1
