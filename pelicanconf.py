# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Thomas Perrot'
SITENAME = "Tprrt's Blog"
SITESUBTITLE = "Yet another blog about embedded Linux, the open source and hardware"
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'

DEFAULT_DATE = 'fs'
DEFAULT_DATE_FORMAT = '%d %b %Y'

GOOGLE_ANALYTICS = ""
GOOGLE_ADSENSE = ""

GITHUB_URL = "https://github.com/tprrt"

# Feed generation is usually not desired when developing
FEED_DOMAIN = SITEURL

FEED_ALL_RSS = 'feeds/all.rss.xml'
CATEGORY_FEED_RSS = 'feeds/{slug}.rss.xml'
TRANSLATION_FEED_RSS = 'feeds/all-{lang}.rss.xml'
AUTHOR_FEED_RSS = 'feeds/{slug}.rss.xml'

FEED_ALL_ATOM= 'feeds/all.atom.xml'
CATEGORY_FEED_ATOM = 'feeds/{slug}.atom.xml'
TRANSLATION_FEED_ATOM = 'feeds/all-{lang}.atom.xml'
AUTHOR_FEED_ATOM = 'feeds/{slug}.atom.xml'

STATIC_PATHS = ['static']

# Copying HTML files to output without processing them
READERS = {'html': None}

EXTRA_PATH_METADATA = {
    'static/CNAME': {'path': 'CNAME'},
    'static/favicon.ico': {'path': 'favicon.ico'},
    'static/google388b7531c8b11164.html': {'path': 'google388b7531c8b11164.html'},
    'static/header_cover.png': {'path': 'static/header_cover.png'},
    'static/robots.txt': {'path': 'robots.txt'}
}

# all defaults to True.
DISPLAY_HEADER = True
DISPLAY_FOOTER = True
DISPLAY_HOME   = True
DISPLAY_MENU   = True

# urls
ARCHIVES_URL       = 'archives'
ARCHIVES_SAVE_AS   = 'archives/index.html'
AUTHORS_URL        = 'authors'
AUTHORS_SAVE_AS    = 'authors/index.html'
CATEGORIES_URL     = 'categories'
CATEGORIES_SAVE_AS = 'categories/index.html'
CONTACT_URL     = 'contact'
CONTACT_SAVE_AS = 'contact/index.html'
CONTRIBUTIONS_URL     = 'contributions'
CONTRIBUTIONS_SAVE_AS = 'contributions/index.html'
TAGS_URL           = 'tags'
TAGS_SAVE_AS       = 'tags/index.html'

# Menu
MENU_INTERNAL_PAGES = ()

DISPLAY_CATEGORIES_ON_MENU = False
DISPLAY_PAGES_ON_MENU = False

MENUITEMS = (
    ('Contributions', CONTRIBUTIONS_URL),
    ('Archives', ARCHIVES_URL),
    ('Categories', CATEGORIES_URL),
    ('Contact', CONTACT_URL),
)

# Plugins
PLUGIN_PATHS = [
    'pelican-plugins'
]

PLUGINS = [
    'assets',
    'sitemap',
]

# Publish draft to review before publising
DEFAULT_METADATA = {
    'status': 'draft',
}

# Specify a customized theme, via path relative to the settings file
THEME = "pelican-themes/blue-penguin"

THEME_TEMPLATES_OVERRIDES = ["templates"]
