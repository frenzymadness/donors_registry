# donors_registry

Registry of blood donors for Czech Red Cross in Frýdek-Místek.

## Instalation

1. Create and activate a new virtual environment
1. Install all development dependencies via `pip install -r requirements/dev.txt`
1. Create a config file `registry/.env` with the following content:

```
FLASK_ENV=development
DATABASE_URL=sqlite:///database.sqlite
SECRET_KEY=<some_random_string_here>
```

1. Prepare a new database and apply all existing migrations via `flask db upgrade`

1. Add a user account via `flask create-user <email> <password>`

1. You can install anonymized test data via `flask install-test-data` (needs empty database and with all migrations applied)

1. run the app with `flask run`

## Testing

There are currently no tests but you can run linters at least via `tox -e lint`.
