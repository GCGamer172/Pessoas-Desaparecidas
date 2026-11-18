from datetime import date

from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.orm import Session

from database.models import Base, MissingPerson
from services.records import (
    create_ocr_analysis,
    create_person,
    delete_person,
    search_people,
    update_person,
)


def test_missing_person_persists_with_unique_identifier(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        record = MissingPerson(
            id="test-person-001",
            full_name="Pessoa Fictícia",
            age=25,
            city="Belém",
            state="PA",
            last_seen_location="Local de teste",
            description="Camisa azul fictícia",
            disappearance_date=date(2025, 1, 1),
            status="Desaparecida",
            image_path="uploads/test.jpg",
            public_number=1,
        )
        session.add(record)
        session.commit()
        loaded = session.scalar(select(MissingPerson).where(MissingPerson.id == "test-person-001"))
        assert loaded is not None
        assert loaded.full_name == "Pessoa Fictícia"
        assert loaded.status == "Desaparecida"
        assert loaded.description == "Camisa azul fictícia"
        assert loaded.public_map_consent is False
        assert loaded.last_seen_latitude is None
        assert loaded.last_seen_longitude is None
        assert loaded.public_number == 1


def test_record_service_supports_create_search_update_and_delete(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'service-test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        fields = {
            "full_name": "Pessoa de Teste",
            "age": 34,
            "city": "Belém",
            "state": "PA",
            "last_seen_location": "Endereço fictício",
            "description": "Descrição de teste",
            "disappearance_date": date(2025, 2, 1),
            "status": "Desaparecida",
            "public_map_consent": True,
        }
        person = create_person(session, fields, "uploads/foto.jpg")
        assert search_people(session, "Pessoa de Teste") == [person]
        assert person.public_map_consent is True
        assert person.public_number == 1

        updated_fields = {**fields, "status": "Localizada"}
        update_person(session, person, updated_fields)
        assert search_people(session, status="Localizada")[0].id == person.id

        delete_person(session, person)
        assert search_people(session) == []

        next_person = create_person(session, fields, "uploads/foto-2.jpg")
        assert next_person.public_number == 2
        delete_person(session, next_person)
        third_person = create_person(session, fields, "uploads/foto-3.jpg")
        assert third_person.public_number == 3


def test_ocr_analysis_is_persisted(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'ocr-test.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        analysis = create_ocr_analysis(session, "uploads/poster.png", 4, '{"full_name": "Fictícia"}')
        assert analysis.id
        assert analysis.extracted_count == 4
        assert analysis.image_path == "uploads/poster.png"


def test_initialize_database_migrates_existing_records(tmp_path, monkeypatch):
    import database.connection as connection

    path = tmp_path / "legacy.db"
    legacy_engine = create_engine(f"sqlite:///{path}")
    with legacy_engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE missing_people (
                    id VARCHAR(36) PRIMARY KEY,
                    full_name VARCHAR(160) NOT NULL,
                    age INTEGER NOT NULL,
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(2) NOT NULL,
                    last_seen_location VARCHAR(300) NOT NULL,
                    disappearance_date DATE NOT NULL,
                    status VARCHAR(30) NOT NULL,
                    image_path VARCHAR(500) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO missing_people (
                    id, full_name, age, city, state, last_seen_location,
                    disappearance_date, status, image_path, created_at, updated_at
                ) VALUES (
                    'legacy-id', 'Pessoa Fictícia', 20, 'Belém', 'PA', 'Local fictício',
                    '2025-01-01', 'Em aberto', 'uploads/ficticia.jpg', '2025-01-01', '2025-01-01'
                )
                """
            )
        )

    monkeypatch.setattr(connection, "engine", legacy_engine)
    monkeypatch.setattr(connection, "DATABASE_PATH", path)
    connection.initialize_database()

    columns = {column["name"] for column in inspect(legacy_engine).get_columns("missing_people")}
    with legacy_engine.connect() as conn:
        record = conn.execute(
            text(
                "SELECT description, status, public_map_consent, public_number "
                "FROM missing_people WHERE id = 'legacy-id'"
            )
        ).one()
    assert "description" in columns
    assert "public_map_consent" in columns
    assert "last_seen_latitude" in columns
    assert "last_seen_longitude" in columns
    assert record.description == ""
    assert record.status == "Desaparecida"
    assert record.public_map_consent == 0
    assert record.public_number == 1
    with legacy_engine.connect() as conn:
        sequence_value = conn.execute(
            text("SELECT last_value FROM person_number_sequence WHERE id = 1")
        ).scalar_one()
    assert sequence_value == 1
    legacy_engine.dispose()
