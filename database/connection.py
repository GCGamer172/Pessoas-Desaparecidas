import os
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from database.models import Base


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = Path(os.getenv("MISSING_PERSONS_DB", PROJECT_ROOT / "database" / "app.db")).resolve()
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def initialize_database() -> None:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    columns = {column["name"] for column in inspect(engine).get_columns("missing_people")}
    if "description" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE missing_people ADD COLUMN description TEXT NOT NULL DEFAULT ''")
            )
    if "public_map_consent" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE missing_people ADD COLUMN "
                    "public_map_consent BOOLEAN NOT NULL DEFAULT 0"
                )
            )
    if "last_seen_latitude" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE missing_people ADD COLUMN last_seen_latitude FLOAT")
            )
    if "last_seen_longitude" not in columns:
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE missing_people ADD COLUMN last_seen_longitude FLOAT")
            )
    with engine.begin() as connection:
        if "public_number" not in columns:
            connection.execute(
                text("ALTER TABLE missing_people ADD COLUMN public_number INTEGER")
            )
        current_max = connection.scalar(
            text("SELECT COALESCE(MAX(public_number), 0) FROM missing_people")
        ) or 0
        missing_ids = connection.execute(
            text(
                "SELECT id FROM missing_people WHERE public_number IS NULL "
                "ORDER BY created_at, id"
            )
        ).scalars().all()
        for person_id in missing_ids:
            current_max += 1
            connection.execute(
                text("UPDATE missing_people SET public_number = :number WHERE id = :id"),
                {"number": current_max, "id": person_id},
            )
        connection.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS "
                "ix_missing_people_public_number ON missing_people(public_number)"
            )
        )
        connection.execute(
            text(
                "INSERT OR IGNORE INTO person_number_sequence (id, last_value) "
                "VALUES (1, :last_value)"
            ),
            {"last_value": current_max},
        )
        connection.execute(
            text(
                "UPDATE person_number_sequence SET last_value = "
                "MAX(last_value, :last_value) WHERE id = 1"
            ),
            {"last_value": current_max},
        )
        connection.execute(
            text("UPDATE missing_people SET status = 'Desaparecida' WHERE status = 'Em aberto'")
        )


def get_session() -> Session:
    return SessionLocal()
