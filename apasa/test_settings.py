"""Explicit portable database tests; never used by normal local startup."""
from .settings import *
DATABASES = {'default': {'ENGINE':'django.db.backends.sqlite3','NAME':':memory:'}}
PUBLIC_EVIDENCE_TEST_DATABASE = True
PUBLIC_EVIDENCE_MODE = 'csv'
