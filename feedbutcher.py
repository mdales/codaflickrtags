# Copyright (c) 2008-2009 Cambridge Visual Networks

# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.


# This is a simple feed dissecter for RSS and ATOM feeds. Usage:
# 
# import feedbutcher
# import urllib
#
# url = 'http://slashdot.org/index.rss'
# feed_file = urllib.urlopen(url)
#
# feed = feedbutcher.FeedButcher(feed_file, url)
#
# for entry in feed.entries:
#
#     print entry.title.strip(), '(%s images)' % len(entry.images)
#     print "--------------------------------------------------------------------------------"
#     print entry.description
#


from xml.etree import ElementTree
from xml.parsers.expat import ExpatError
import re
import tidy
from urlparse import urljoin
import uuid

# Namespaces in use
NS_RDF  = '{http://www.w3.org/1999/02/22-rdf-syntax-ns#}'
NS_RSS  = '{http://purl.org/rss/1.0/}'
NS_ATOM = '{http://www.w3.org/2005/Atom}'
NS_DC   = '{http://purl.org/dc/elements/1.1/}'
NS_CONTENT = '{http://purl.org/rss/1.0/modules/content/}'
class Error(Exception): pass

style_width_re = re.compile(r'width\s*:\s*(\d+)(?:px|%)')
style_height_re = re.compile(r'height\s*:\s*(\d+)(?:px|%)')

class Image(object):
    
    def __init__(self, src, width, height):
        self.src = src
        self.width = width
        self.height = height

    def to_cml(self):
        image = ElementTree.Element('img', src=self.src)
        if self.width:
            image.set('width', str(self.width))
        if self.height:
            image.set('height', str(self.height))
        
        return ElementTree.tostring(image)
    
    def __repr__(self):
        return u'<FeedButcher Image url="%s">' % self.src

class Entry(object):

    def _tidy(self, text):
        return str(tidy.parseString(text,
                                show_body_only=True,
                                output_xhtml=True,
                                numeric_entities=True,
                                char_encoding='utf8'))

    def __init__(self, title, pubdate, text, guid, url):
        self.title = self._tidy(title.encode('utf-8'))
        self.pubdate = pubdate
        self.images = []
        self.url = url
        # we rely on there being a GUID, so if there isn't one we
        # hash all the parts to make one
        if (guid != None) and (guid != ''):
            self.guid = guid
        else:
            self.guid = str(uuid.uuid5(uuid.NAMESPACE_URL, 
                url + self.title + pubdate))


        # text can be None in rare cases. Reason unknown.
        if text is None:
            text = ''
            
        text = text.encode('utf-8')
        text = self._tidy(text)
        self.description = text

        # ElementTree expects a utf-8 encoded str-type:
        try:
            entry_xml = ElementTree.XML('<mock>%s</mock>' % text)

        except ExpatError, e:
            # xhtml broken, best effort is to set the text empy.
            entry_xml = ElementTree.Element('mock')

        # Heuristic to discover images and their dimensions
        for image in entry_xml.findall('.//img'):

            height = image.get('height', None)
            width = image.get('width', None)

            # style-width and -height attributes override normal width="" and height=""
            style_width = style_width_re.search(image.get('style', ''))
            style_height = style_height_re.search(image.get('style', ''))

            if style_width: width = style_width.groups(1)
            if style_height: height = style_width.groups(1)

            src = image.get('src', '')
            self.images.append(Image(urljoin(self.url, src), width, height))

class FeedButcher(object):

    def __init__(self, fp, url=''):
        self.entries = []
        self.title = ''
        self.description = ''
        self.date = None
        self.url = url
        
        try:
            self.et = ElementTree.parse(fp)

        except ExpatError, e:
            raise Error(str(e))

        self.feed = self.et.getroot()

        if self.feed.tag == NS_RDF+'RDF':
            self._dissect_rdf()

        elif self.feed.tag == 'rss':
            self._dissect_rss()

        elif self.feed.tag == NS_ATOM+'feed':
            self._dissect_atom()

        else:
            raise Error('unknown feed: "%s"' % self.feed.tag)
    
    def _dissect_rdf(self):
        channel = self.feed.find(NS_RSS+'channel')
        self.title = channel.findtext(NS_RSS+'title', '')
        self.description = channel.findtext(NS_RSS+'description', '')
        self.date = channel.findtext(NS_DC+'date', '')

        for item in self.feed.findall(NS_RSS+'item'):
            title = item.findtext(NS_RSS+'title', '')
            description = item.findtext(NS_RSS+'description', '')
            date = item.findtext(NS_DC+'date', '')

            self.entries.append(Entry(title, date, description, '', self.url))

    def _dissect_rss(self):
        channel = self.feed.find('channel')
        self.title = channel.findtext('title', '')
        self.description = channel.findtext('description', '')
        self.date = channel.findtext('pubDate', '')

        for item in channel.findall('item'):
            title = item.findtext('title', '')
            description = item.findtext(NS_CONTENT+'encoded', item.findtext('description', ''))
            date = item.findtext('pubDate', '')
            guid = item.findtext('guid', '')

            self.entries.append(Entry(title, date, description, guid, self.url))

    def _dissect_atom(self):
        self.title = self.feed.findtext(NS_ATOM+'title', '')
        self.date = self.feed.findtext('updated', '')
        
        for item in self.feed.findall(NS_ATOM+'entry'):
            title = item.findtext(NS_ATOM+'title', '')
            description = item.findtext(NS_ATOM+'content', item.findtext(NS_ATOM+'summary', ''))
            date = item.findtext(NS_ATOM+'updated', '')
            guid = item.findtext(NS_ATOM+'id', '')
            
            self.entries.append(Entry(title, date, description, guid, self.url))
