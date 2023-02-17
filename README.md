# donors_registry

Registry of blood donors for Czech Red Cross in Frýdek-Místek.

## Instalation

1. Create and activate a new virtual environment
1. Install all development dependencies via `pip install -r requirements/dev.txt`
1. Prepare a new database and apply all existing migrations via `flask db upgrade`
1. Add a user account via `flask create-user <email> <password>`
1. You can install anonymized test data via `flask install-test-data` (needs empty database and with all migrations applied)
1. run the app with `FLASK_DEBUG=1 flask run` or on Windows with `set FLASK_DEBUG=1` and then `flask run`

## Database

SQLite database we are currently using has very limited support for `ALTER TABLE…` SQL queries so we need to modify
the historical migrations from time to time. If you have any issue with the database, try removing the `.sqlite` file
first and then repeat the last four steps from above.

Our plan is to switch to a more robust database system when switching to production use.

## Testing

Tests use pytest and are configured via tox. To run all of them, simply install and execute `tox`.

If you want to prevent tests failing because of linter issues,
you can use pre-commit which automatically runs linters before every commit
(this doesn't work on Windows)
1. To activate it install `pre-commit` using `pip install pre-commit` or you
can install all extra requirements via `pip install -r requirements/extra.txt`.
1. Then run `pre-commit install`
1. After that linters should run before every commit.

Code coverage is measured by `coverage` Python package. It's automatically measured for the last tox environment
with a report at the very end of the output. If you want to run it manually, use `coverage run -m pytest`
and then `coverage report` to see the results in the command line or `coverage html` which produces folder `htmlcov`
with more interactive results.
