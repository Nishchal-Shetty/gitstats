import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship
from sqlalchemy import (
    Column, String, Integer, Text, DateTime, Float,
    ForeignKey, JSON, func, UniqueConstraint, NullPool
)
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("SUPABASE_URL")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0}
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    readme = Column(Text, nullable=True)
    stars = Column(Integer, default=0)
    forks = Column(Integer, default=0)
    watchers = Column(Integer, default=0)
    open_issues = Column(Integer, default=0)
    language = Column(String, nullable=True)
    topics = Column(JSON, default=list)
    size = Column(Integer, default=0)  # in KB
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    scraped_at = Column(DateTime, server_default=func.now())
    contributor_count = Column(Integer, default=0)
    commit_count = Column(Integer, default=0)

    classification = relationship(
        "RepoClassification", back_populates="repository", uselist=False
    )


class RepoClassification(Base):
    __tablename__ = "repo_classifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    genre = Column(String, nullable=False)
    tags = Column(JSON, default=list)
    confidence = Column(Float, nullable=True)
    classified_at = Column(DateTime, server_default=func.now())

    repository = relationship("Repository", back_populates="classification")


class Developer(Base):
    __tablename__ = "developers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_username = Column(String, unique=True, nullable=False)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    public_repos = Column(Integer, default=0)
    total_stars = Column(Integer, default=0)
    top_languages = Column(JSON, default=list)
    fetched_at = Column(DateTime, server_default=func.now())


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, nullable=False)
    display_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    email = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    last_login = Column(DateTime, server_default=func.now(), onupdate=func.now())


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
