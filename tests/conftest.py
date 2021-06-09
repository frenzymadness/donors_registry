from .fixtures import (  # noqa: F401
    BACKUP_DB_PATH,
    TEST_DB_PATH,
    app,
    db,
    test_data_df,
    testapp,
    user,
)


def pytest_sessionfinish(session, exitstatus):
    try:
        BACKUP_DB_PATH.unlink()
    except FileNotFoundError:
        pass

    try:
        TEST_DB_PATH.unlink()
    except FileNotFoundError:
        pass
