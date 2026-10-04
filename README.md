# LinkForge API

## Local development with Docker Compose

1. Install Docker Desktop and start its Linux container engine.
2. Keep the existing `.env` file and add the PostgreSQL values shown in
   `.env.example`. Choose a private local `POSTGRES_PASSWORD`; do not commit
   `.env`.
3. Start the database, Redis, and Django API:

   ```powershell
   docker compose up --build -d
   ```

4. Apply Django migrations:

   ```powershell
   docker compose exec web python manage.py migrate
   ```

5. Open the API at `http://localhost:8000`.

PostgreSQL persists in the `postgres_data` volume and Redis in `redis_data`.
The existing `db.sqlite3` file is left untouched; changing Django's database
setting does not copy its data.

## Optional SQLite data transfer

Only perform this if the existing SQLite records need to be preserved. The
export fixture can contain user data, so keep it local and do not commit it.
The project supports a one-command SQLite override for exporting:

```powershell
$env:DATABASE_ENGINE = 'django.db.backends.sqlite3'
python manage.py dumpdata --natural-foreign --natural-primary `
  --exclude contenttypes --exclude auth.permission `
  --exclude admin.logentry --exclude authtoken.token `
  --output sqlite-data.json
Remove-Item Env:DATABASE_ENGINE
```

After starting Compose and applying migrations, copy and load the fixture:

```powershell
docker compose cp sqlite-data.json web:/app/sqlite-data.json
docker compose exec web python manage.py loaddata sqlite-data.json
```

API tokens are deliberately excluded; users can obtain new tokens after
transfer. Keep the SQLite file and a copy of the fixture as backups until the
PostgreSQL data has been checked.
