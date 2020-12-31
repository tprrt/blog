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

GITHUB_URL = "https://github.com/tprrt"

# Feed generation is usually not desired when developing
FEED_DOMAIN = SITEURL

FEED_ALL_RSS = None
CATEGORY_FEED_RSS = None
TRANSLATION_FEED_RSS = None
AUTHOR_FEED_RSS = None

FEED_ALL_ATOM= None
CATEGORY_FEED_ATOM = None
TRANSLATION_FEED_ATOM = None
AUTHOR_FEED_ATOM = None

STATIC_PATHS = ['static']

EXTRA_PATH_METADATA = {
    'static/robots.txt': {'path': 'robots.txt'},
    'static/header_cover.png': {'path': 'static/header_cover.png'},
    'static/CNAME': {'path': 'CNAME'}
}

# all defaults to True.
DISPLAY_HEADER = True
DISPLAY_FOOTER = True
DISPLAY_HOME   = True
DISPLAY_MENU   = True

# urls
TAGS_URL           = 'tags'
TAGS_SAVE_AS       = 'tags/index.html'
AUTHORS_URL        = 'authors'
AUTHORS_SAVE_AS    = 'authors/index.html'
CATEGORIES_URL     = 'categories'
CATEGORIES_SAVE_AS = 'categories/index.html'
ARCHIVES_URL       = 'archives'
ARCHIVES_SAVE_AS   = 'archives/index.html'

# Menu
MENU_INTERNAL_PAGES = (
    ('Archives', ARCHIVES_URL, ARCHIVES_SAVE_AS),
    ('Categories', CATEGORIES_URL, CATEGORIES_SAVE_AS),
    ('Tags', TAGS_URL, TAGS_SAVE_AS),
    ('Authors', AUTHORS_URL, AUTHORS_SAVE_AS),
)

# Plugins
PLUGIN_PATHS = [
    'pelican-plugins'
]

# PLUGINS = [
#     'assets',
#     'neighbors',
#     'sitemap',
# ]

# Publish draft to review before publising
DEFAULT_METADATA = {
    'status': 'draft',
}

# Specify a customized theme, via path relative to the settings file
THEME = "pelican-themes/blue-penguin"

THEME_TEMPLATES_OVERRIDES = ["templates"]
