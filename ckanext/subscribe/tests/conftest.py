import pytest
from ckan.plugins import toolkit


@pytest.fixture
def clean_db(reset_db, migrate_db_for):
    reset_db()
    migrate_db_for("subscribe")
    if toolkit.check_ckan_version(min_version="2.11.0"):
        migrate_db_for("activity")
