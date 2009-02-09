from django.conf.urls.defaults import *

urlpatterns = patterns('rss.views',
                       (r'^rss/cml/', 'coda_rss_flickr_tag'),
)
