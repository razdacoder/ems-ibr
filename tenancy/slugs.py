"""School slugs: the subdomain a school lives on, fixed for good at creation.

The slug names the schema too, so neither ever changes (spec 0003, child 0004).
"""
import re

# 3 to 30 characters, lowercase letters, digits and inner hyphens.
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,28}[a-z0-9])$")

# Never allowed for a school (spec 0003, child 0002). `test` and `demo` are
# for schools made in code: the test suite and `manage.py create_school`.
RESERVED = frozenset({
    "admin", "api", "www", "app", "static", "media", "mail", "smtp", "support",
    "status", "docs", "help", "blog", "ordo", "staging", "test", "dev", "demo",
    "localhost",
})


def schema_name_for(slug):
    return "school_" + slug.replace("-", "_")
