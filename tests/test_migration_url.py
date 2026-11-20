from sqlalchemy.engine import make_url

from backend.app.database.migration_url import migration_database_url


def test_neon_migration_uses_direct_host_and_preserves_connection_options():
    original = "postgresql+psycopg2://example:p%40ss%25word@ep-example-pooler.eu-central-1.aws.neon.tech/neondb?sslmode=require"
    direct = make_url(migration_database_url(original))
    assert direct.host == "ep-example.eu-central-1.aws.neon.tech"
    assert direct.password == "p@ss%word"
    assert direct.query == make_url(original).query
    assert direct.username == "example" and direct.database == "neondb"


def test_non_neon_hosts_are_not_rewritten():
    original = "postgresql+psycopg2://postgres@localhost:55432/zuka_test_review"
    assert make_url(migration_database_url(original)) == make_url(original)
