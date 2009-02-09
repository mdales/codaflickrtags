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

from django.shortcuts import render_to_response
from django.http import HttpResponse, HttpResponseRedirect, Http404

import feedbutcher
import datetime
import socket
import logging
import urllib2

##############################################################################
#
def coda_rss_flickr_tag(request):
    "Just a temporary demo"
    current_date = datetime.datetime.now()
    
    # Accept tags as GET parameter: ?tags=decay
    tags = request.GET.get('tags', 'all')
    url = 'http://api.flickr.com/services/feeds/photos_public.gne?tags=%s&lang=en-us&format=rss_200' % tags

    try:
        request = urllib2.Request(url)
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml')
        feed_file = urllib2.urlopen(request)
        feed = feedbutcher.FeedButcher(feed_file, url)


        # Sort image by size for nicer looks and display them on a 4x3 grid:
        all_images = sorted(sum((e.images for e in feed.entries), []),
                            key=lambda image: (-int(image.height or 0), int(image.width or 0)))
        images = []
        for x in xrange(4):
            for y in xrange(3):
                # Keep space in to top right corner for our logo
                if x == 3 and y == 0: continue
                cml_image = all_images[y*3+x]
                cml_image.width = cml_image.width or 280

                # Scale to make the longest side 280px
                if cml_image.width > cml_image.height:
                    ratio = 280.0/int(cml_image.width)
                else:
                    ratio = 280.0/int(cml_image.height)

                cml_image.width = str(int(ratio*int(cml_image.width)))
                if cml_image.height is not None:
                    cml_image.height = str(int(ratio*int(cml_image.height)))

                images.append({'x': 20+x*300,
                               'y': 20+y*320,
                               'image': cml_image,
                               })

        return render_to_response('coda_rss_overview.cml',
                                  {'images': images},
                                  mimetype="text/x-coda-markup; charset=utf-8")

    except (socket.error, IOError):
        logging.exception('')
        fail_url = url
        return render_to_response('coda_rss_fail_404.cml',
                                  locals(),
                                  mimetype="text/x-coda-markup; charset=utf-8")

    except (StandardError, feedbutcher.Error):
        logging.exception('')
        fail_url = url
        return render_to_response('coda_rss_fail.cml',
                                  locals(),
                                  mimetype="text/x-coda-markup; charset=utf-8")
#
##############################################################################
