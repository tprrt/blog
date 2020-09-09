# -*- coding: utf-8 -*- #
from __future__ import unicode_literals

AUTHOR = 'Thomas Perrot'
SITENAME = "Tprrt's Blog"
SITESUBTITLE = "Yet another  blog about Linux embedded"
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

# Blogroll
# LINKS = (('Pelican', 'http://getpelican.com/'),
#          ('Python.org', 'http://python.org/'),
#          ('Jinja2', 'http://jinja.pocoo.org/'),
#          ('You can modify those links in your config file', '#'),)

# Social widget
SOCIAL = (('github', 'https://github.com/tprrt'),
          ('linkedin', 'https://www.linkedin.com/in/tprrt/'),
          ('instagram','https://www.instagram.com/thomas.prrt'),
          ('facebook','https://facebook.com/tperrot31'),
          ('twitter', 'https://twitter.com/tprrt31'),
          ('envelope','mailto:tprrt@tupi.fr'))

DEFAULT_PAGINATION = 3
PAGINATION_PATTERNS = (
    (1, '{base_name}/', '{base_name}/index.html'),
    (2, '{base_name}/page/{number}/', '{base_name}/page/{number}/index.html'),
)

# Uncomment following line if you want document-relative URLs when developing
#RELATIVE_URLS = True

STATIC_PATHS = ['static']

EXTRA_PATH_METADATA = {
    'static/robots.txt': {'path': 'robots.txt'},
    'static/header_cover.png': {'path': 'static/header_cover.png'},
    'static/CNAME': {'path': 'CNAME'}
}

# Post and Pages path
ARTICLE_URL = '{date:%Y}/{date:%m}/{slug}.html'
ARTICLE_SAVE_AS = '{date:%Y}/{date:%m}/{slug}.html'
PAGE_URL = 'pages/{slug}/'
PAGE_SAVE_AS = 'pages/{slug}/index.html'
YEAR_ARCHIVE_SAVE_AS = '{date:%Y}/index.html'
MONTH_ARCHIVE_SAVE_AS = '{date:%Y}/{date:%m}/index.html'

# Tags and Category path
CATEGORY_URL = 'category/{slug}'
CATEGORY_SAVE_AS = 'category/{slug}/index.html'
CATEGORIES_SAVE_AS = 'catgegories.html'
TAG_URL = 'tag/{slug}'
TAG_SAVE_AS = 'tag/{slug}/index.html'
TAGS_SAVE_AS = 'tags.html'

# Author
AUTHOR_URL = 'author/{slug}'
AUTHOR_SAVE_AS = 'author/{slug}/index.html'
AUTHORS_SAVE_AS = 'authors.html'

### Plugins

PLUGIN_PATHS = [
  'pelican-plugins'
]

PLUGINS = [
  'assets',
  'html_rst_directive',
  'neighbors',
  'pdf',
  'sitemap',
]

# Sitemap
SITEMAP = {
    'format': 'xml',
    'priorities': {
        'articles': 0.5,
        'indexes': 0.5,
        'pages': 0.5
    },
    'changefreqs': {
        'articles': 'monthly',
        'indexes': 'daily',
        'pages': 'monthly'
    }
}

# Publish draft to review before publising
DEFAULT_METADATA = {
    'status': 'draft',
}

# code blocks with line numbers
PYGMENTS_RST_OPTIONS = {'linenos': 'table'}

# Specify a customized theme, via path relative to the settings file
THEME = "pelican-themes/attila"
HEADER_COVER = 'static/header_cover.png'
HEADER_COLOR = 'black'
#COLOR_SCHEME_CSS = 'monokai.css'
#CSS_OVERRIDE = ['css/myblog.css']
#JS_OVERRIDE = ['']

# Jinja config - Pelican 4
JINJA_ENVIRONMENT = {
  'extensions' :[
    'jinja2.ext.loopcontrols',
    'jinja2.ext.i18n',
    'jinja2.ext.with_',
    'jinja2.ext.do'
  ]
}
JINJA_FILTERS = {'max': max}

AUTHORS_BIO = {
  "tperrot": {
    "name": "Thomas Perrot",
    "cover": "static/header_cover.png",
    "image": "static/avatar.png",
    "website": "https://tprrt.tupi.fr",
    "linkedin": "www.linkedin.com/in/tprrt",
    "github": "tprrt",
    "location": "Toulouse",
    "bio": "This is the place for a small biography with max 200 characters. Well, now 100 are left. Cool, hugh?"
  }
}

THEME_TEMPLATES_OVERRIDES = ["templates"]
