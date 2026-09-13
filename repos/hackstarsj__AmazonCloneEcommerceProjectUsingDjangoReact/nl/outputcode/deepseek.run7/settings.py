# =============================================
# settings.py additions (only relevant parts)
# =============================================
INSTALLED_APPS = [
    ...
    'store',
    ...
]

AUTH_USER_MODEL = 'store.User'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Media files (for product images)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# You'll need to set up static and media serving in urls.py (project level) and run migrations.
