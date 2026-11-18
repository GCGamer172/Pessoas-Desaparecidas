import uuid

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from database.models import ImageAnalysis, MissingPerson, OCRAnalysis


def create_person(session: Session, fields: dict[str, object], image_path: str) -> MissingPerson:
    session.execute(
        text(
            "INSERT OR IGNORE INTO person_number_sequence (id, last_value) "
            "VALUES (1, 0)"
        )
    )
    public_number = session.execute(
        text(
            "UPDATE person_number_sequence SET last_value = last_value + 1 "
            "WHERE id = 1 RETURNING last_value"
        )
    ).scalar_one()
    person = MissingPerson(
        id=str(uuid.uuid4()),
        public_number=public_number,
        image_path=image_path,
        **fields,
    )
    session.add(person)
    session.commit()
    session.refresh(person)
    return person


def update_person(
    session: Session, person: MissingPerson, fields: dict[str, object], image_path: str | None = None
) -> MissingPerson:
    for key, value in fields.items():
        setattr(person, key, value)
    if image_path is not None:
        person.image_path = image_path
    session.commit()
    session.refresh(person)
    return person


def search_people(session: Session, query: str = "", status: str | None = None) -> list[MissingPerson]:
    statement = select(MissingPerson)
    if query.strip():
        term = f"%{query.strip()}%"
        statement = statement.where(
            or_(MissingPerson.full_name.ilike(term), MissingPerson.city.ilike(term))
        )
    if status:
        statement = statement.where(MissingPerson.status == status)
    return list(session.scalars(statement.order_by(MissingPerson.created_at.desc())).all())


def create_ocr_analysis(
    session: Session, image_path: str, extracted_count: int, fields_json: str
) -> OCRAnalysis:
    analysis = OCRAnalysis(
        id=str(uuid.uuid4()),
        image_path=image_path,
        extracted_count=extracted_count,
        fields_json=fields_json,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis


def delete_person(session: Session, person: MissingPerson) -> None:
    session.delete(person)
    session.commit()


def create_analysis(
    session: Session,
    image_path: str,
    annotated_image_path: str,
    detected_people: int,
    results_json: str,
) -> ImageAnalysis:
    analysis = ImageAnalysis(
        id=str(uuid.uuid4()),
        image_path=image_path,
        annotated_image_path=annotated_image_path,
        detected_people=detected_people,
        results_json=results_json,
    )
    session.add(analysis)
    session.commit()
    session.refresh(analysis)
    return analysis
