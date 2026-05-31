AUTHOR = 'Thomas Perrot'
SITENAME = "Tprrt's Blog"
SITESUBTITLE = "Embedded Linux, Zephyr RTOS, open-source hardware, Linux gaming, retro gaming, and competitive fitness"
SITEDESCRIPTION = SITESUBTITLE
SITEURL = ''

PATH = 'content'

TIMEZONE = 'Europe/Paris'

DEFAULT_LANG = 'en'

DEFAULT_DATE = 'fs'
DEFAULT_DATE_FORMAT = '%d %b %Y'

GOOGLE_ANALYTICS = ""
GOOGLE_ADSENSE = ""
GOATCOUNTER_CODE = ""

GITHUB_URL = "https://github.com/tprrt"

# Feed generation is usually not desired when developing
FEED_DOMAIN = SITEURL
FEED_ALL_ATOM = None
FEED_ALL_RSS = None
CATEGORY_FEED_ATOM = None
CATEGORY_FEED_RSS = None
TRANSLATION_FEED_ATOM = None
TRANSLATION_FEED_RSS = None
AUTHOR_FEED_ATOM = None
AUTHOR_FEED_RSS = None

STATIC_PATHS = ['static']

# Copying HTML files to output without processing them
READERS = {'html': None}

EXTRA_PATH_METADATA = {
    'static/CNAME': {'path': 'CNAME'},
    'static/favicon.ico': {'path': 'favicon.ico'},
    'static/google388b7531c8b11164.html': {'path': 'google388b7531c8b11164.html'},
    'static/robots.txt': {'path': 'robots.txt'}
}

# all defaults to True.
DISPLAY_HEADER = True
DISPLAY_FOOTER = True
DISPLAY_HOME   = True
DISPLAY_MENU   = True

# urls
ARTICLES_URL       = 'articles'
ARTICLES_SAVE_AS   = 'articles/index.html'
AUTHORS_URL        = 'authors'
AUTHORS_SAVE_AS    = 'authors/index.html'
CATEGORIES_URL     = 'categories'
CATEGORIES_SAVE_AS = 'categories/index.html'
CONTACT_URL     = 'contact'
CONTACT_SAVE_AS = 'contact/index.html'
CONTRIBUTIONS_URL     = 'contributions'
CONTRIBUTIONS_SAVE_AS = 'contributions/index.html'
DIGESTS_URL        = 'digests'
DIGESTS_SAVE_AS    = 'digests/index.html'
TAGS_URL           = 'tags'
TAGS_SAVE_AS       = 'tags/index.html'

DIRECT_TEMPLATES = ['index', 'authors', 'categories', 'tags', 'articles', 'digests']

# Menu
MENU_INTERNAL_PAGES = (
    ('Articles', ARTICLES_URL, ARTICLES_SAVE_AS),
    ('Digests', DIGESTS_URL, DIGESTS_SAVE_AS),
    ('Categories', CATEGORIES_URL, CATEGORIES_SAVE_AS),
    ('Contributions', CONTRIBUTIONS_URL, CONTRIBUTIONS_SAVE_AS),
    ('Contact', CONTACT_URL, CONTACT_SAVE_AS),
)

DISPLAY_CATEGORIES_ON_MENU = False
DISPLAY_PAGES_ON_MENU = False

MENUITEMS = ()

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
