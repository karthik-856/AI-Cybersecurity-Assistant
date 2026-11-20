"""Keep schema migrations off Neon's transaction pooler."""

from sqlalchemy.engine import make_url


def migration_database_url(database_url: str) -> str:
    url = make_url(database_url)
    host = url.host or ""
    if host.endswith(".neon.tech") and "-pooler." in host:
        url = url.set(host=host.replace("-pooler.", ".", 1))
    return url.render_as_string(hide_password=False)
