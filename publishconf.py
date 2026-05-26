# This file is only used if you use `make publish` or
# explicitly specify it as your config file.

import os
import sys
sys.path.append(os.curdir)
from pelicanconf import *

# If your site is available via HTTPS, make sure SITEURL begins with https://
SITEURL = 'https://tprrt.tupi.fr'
RELATIVE_URLS = False

DELETE_OUTPUT_DIRECTORY = True

FEED_DOMAIN = SITEURL
FEED_ALL_RSS = 'feeds/all.rss.xml'
CATEGORY_FEED_RSS = 'feeds/{slug}.rss.xml'
TRANSLATION_FEED_RSS = 'feeds/all-{lang}.rss.xml'
AUTHOR_FEED_RSS = 'feeds/{slug}.rss.xml'
FEED_ALL_ATOM = 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'
TRANSLATION_FEED_ATOM = 'feeds/all-{lang}.atom.xml'
AUTHOR_FEED_ATOM = 'feeds/{slug}.atom.xml'

# Following items are often useful when publishing

GOOGLE_ANALYTICS = "G-Q2GHH38HV9"
GOOGLE_ADSENSE = "ca-pub-8632147971669760"
