import uuid
from typing import List, Optional
from sqlalchemy import ForeignKey, String, DateTime, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", cascade="all", uselist=False)
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="user", cascade="all")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"User(name={self.profile.name})"

class Profile(Base):
    __tablename__ = "user_profile"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    email: Mapped[str] = mapped_column(String(50), unique=True)
    job_role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    last_login: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    # Establish one-to-one relationship with User
    user: Mapped["User"] = relationship("User", back_populates="profile")

    def __repr__(self):
        return f"Profile(name={self.name}, email={self.email})"
    
class Interview(Base):
    __tablename__ = "interviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    date: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    questions: Mapped[List["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="interview", cascade="all")
    duration: Mapped[Optional[int]] = mapped_column(nullable=True)
    interview_type: Mapped[str] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())
    # Establish many-to-one relationship with User
    user: Mapped["User"] = relationship("User", back_populates="interviews")

    def __repr__(self):
        return f"Interview(id={self.id}, date={self.date}, type={self.interview_type})"
    
class Question(Base):
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question: Mapped[str] = mapped_column(String(500))
    question_type: Mapped[str] = mapped_column(String(50))
    job_role: Mapped[str] = mapped_column(String(100))
    job_level: Mapped[str] = mapped_column(String(50))
    # Establish one-to-many relationship with InterviewQuestion
    interview: Mapped[List["InterviewQuestion"]] = relationship("InterviewQuestion", back_populates="question", cascade="all")

    def __repr__(self):
        return f"Question(id={self.id}, text={self.question}, category={self.question_type})"

class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    interview_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("interviews.id"))
    question_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("questions.id"))
    question_text: Mapped[str] = mapped_column(String(500))
    answer: Mapped[str] = mapped_column(String(2000))
    score: Mapped[int] = mapped_column()
    tips: Mapped[List[str]] = mapped_column(JSON)
    feedback: Mapped[str] = mapped_column(String(2000))
    answered_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Establish many-to-one relationship with Interview
    interview: Mapped["Interview"] = relationship("Interview", back_populates="questions")
    # Establish many-to-one relationship with Question
    question: Mapped["Question"] = relationship("Question", back_populates="interview")

    def __repr__(self):
        return f"InterviewQuestion(id={self.id}, question_text={self.question_text})"
