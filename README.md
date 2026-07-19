# ToeicWriting

## Database

The app uses SQLAlchemy and defaults to the bundled SQLite database:

```bash
DATABASE_URL=sqlite:///data/database.db
```

To run against Postgres, set `DATABASE_URL` before starting the server:

```bash
DATABASE_URL='postgres://user:password@host:5432/dbname?sslmode=require'
```

Both `postgres://` and `postgresql+psycopg://` URLs are accepted. The server
creates the tables on startup, but it does not copy the existing SQLite data
into Postgres automatically.
