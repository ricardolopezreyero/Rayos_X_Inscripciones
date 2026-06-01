import uuid
import json
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./rayosx.db"
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,       # detects dead connections before using them
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _enable_wal(dbapi_conn, _):
    """WAL mode: multiple readers don't block each other, writes don't block reads."""
    dbapi_conn.execute("PRAGMA journal_mode=WAL")
    dbapi_conn.execute("PRAGMA synchronous=NORMAL")   # faster writes, still safe
    dbapi_conn.execute("PRAGMA cache_size=-32000")    # 32 MB cache
    dbapi_conn.execute("PRAGMA temp_store=MEMORY")
    dbapi_conn.execute("PRAGMA mmap_size=134217728")  # 128 MB memory-mapped I/O


from sqlalchemy import event
event.listen(engine, "connect", _enable_wal)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DiagnosticSession(Base):
    __tablename__ = "sessions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    short_code = Column(String, unique=True)
    status = Column(String, default="in_progress")  # draft / in_progress / analyzed / closed
    institution_type = Column(String)
    operator_name = Column(String)
    started_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    analyzed_at = Column(DateTime)
    completeness_score = Column(Float, default=0.0)
    certainty_score = Column(Float, default=0.0)
    answers_json = Column(Text, default="{}")
    findings_json = Column(Text, default="[]")
    recommendations_json = Column(Text, default="[]")
    pdf_client_path = Column(String)
    pdf_internal_path = Column(String)

    def get_answers(self):
        return json.loads(self.answers_json or "{}")

    def set_answers(self, data: dict):
        self.answers_json = json.dumps(data, ensure_ascii=False)

    def get_findings(self):
        return json.loads(self.findings_json or "[]")

    def set_findings(self, data: list):
        self.findings_json = json.dumps(data, ensure_ascii=False)

    def get_recommendations(self):
        return json.loads(self.recommendations_json or "[]")

    def set_recommendations(self, data: list):
        self.recommendations_json = json.dumps(data, ensure_ascii=False)


def init_db():
    Base.metadata.create_all(bind=engine)


def make_short_code():
    return uuid.uuid4().hex[:8].upper()
