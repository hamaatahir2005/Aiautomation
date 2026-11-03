import os
from pathlib import Path
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, Boolean
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATA = Path(os.environ.get("AIOS_DATA", str(Path.home() / ".ai-company-os"))).resolve()
DATA.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    f"sqlite:///{DATA / 'company.db'}", connect_args={"check_same_thread": False}
)
Session = sessionmaker(engine, expire_on_commit=False)


def now():
    return datetime.now(timezone.utc).isoformat()


class Base(DeclarativeBase):
    pass


class Record(Base):
    __tablename__ = "records"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    payload: Mapped[str] = mapped_column(Text)
    created: Mapped[str] = mapped_column(default=now)


class Contact(Base):
    __tablename__ = "contacts"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(320), unique=True)
    country: Mapped[str] = mapped_column(default="")
    industry: Mapped[str] = mapped_column(default="")
    consent: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_evidence: Mapped[str] = mapped_column(Text, default="")
    unsubscribed: Mapped[bool] = mapped_column(Boolean, default=False)


class Campaign(Base):
    __tablename__ = "campaigns"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    subject: Mapped[str]
    body: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="draft")
    scheduled: Mapped[str]
    daily_limit: Mapped[int] = mapped_column(default=100)


class Delivery(Base):
    __tablename__ = "deliveries"
    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int]
    contact_id: Mapped[int]
    status: Mapped[str] = mapped_column(default="queued")
    timestamp: Mapped[str] = mapped_column(default=now)
    error: Mapped[str] = mapped_column(default="")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[int] = mapped_column(primary_key=True)
    department: Mapped[str]
    objective: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(default="queued")
    progress: Mapped[int] = mapped_column(default=0)
    result: Mapped[str] = mapped_column(Text, default="")
    options: Mapped[str] = mapped_column(Text, default="{}")
    created: Mapped[str] = mapped_column(default=now)


class Migration(Base):
    __tablename__ = "schema_migrations"
    version: Mapped[int] = mapped_column(primary_key=True)


def migrate():
    Base.metadata.create_all(engine)
    with Session.begin() as s:
        if not s.get(Migration, 1):
            s.add(Migration(version=1))
