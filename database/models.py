from datetime import date, datetime, timezone

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


person_number_sequence = Table(
    "person_number_sequence",
    Base.metadata,
    Column("id", Integer, primary_key=True),
    Column("last_value", Integer, nullable=False),
)


class MissingPerson(Base):
    __tablename__ = "missing_people"
    __table_args__ = (
        CheckConstraint("age >= 0 AND age <= 120", name="ck_missing_people_age"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    state: Mapped[str] = mapped_column(String(2), nullable=False)
    last_seen_location: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    disappearance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    public_map_consent: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_seen_latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    public_number: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    analyses: Mapped[list["ImageAnalysis"]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )


class ImageAnalysis(Base):
    __tablename__ = "image_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    annotated_image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    detected_people: Mapped[int] = mapped_column(Integer, nullable=False)
    results_json: Mapped[str] = mapped_column(Text, nullable=False)
    reviewed: Mapped[bool] = mapped_column(default=False, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    person_id: Mapped[str | None] = mapped_column(
        ForeignKey("missing_people.id", ondelete="SET NULL"), nullable=True
    )

    person: Mapped[MissingPerson | None] = relationship(back_populates="analyses")


class OCRAnalysis(Base):
    __tablename__ = "ocr_analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    image_path: Mapped[str] = mapped_column(String(500), nullable=False)
    extracted_count: Mapped[int] = mapped_column(Integer, nullable=False)
    fields_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
