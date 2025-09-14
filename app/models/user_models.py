"""User Models Module

This module defines SQLAlchemy models for user management including core user entities,
profile information, interview sessions, and question management. It provides the
complete data model structure for the interview application.

The module contains model classes that define the database schema for user management,
interview tracking, and question repositories. It serves as the primary data layer
for user-related operations in the application's model layer.

Dependencies:
- sqlalchemy: For ORM functionality and database modeling.
- uuid: For UUID generation for primary keys.
- datetime: For timestamp handling.
- typing: For type annotations and optional fields.

Author: @kcaparas1630
"""

import uuid
from typing import List, Optional
from sqlalchemy import ForeignKey, String, DateTime, func, JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime

class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models.
    
    Provides the foundation for all database models in the application.
    """
    pass

class User(Base):
    """Core user entity that links Firebase authentication with application data.
    
    Stores the Firebase UID and serves as the central reference point for
    all user-related data including profiles and interviews.
    
    Attributes:
        id (int): Primary key, auto-incrementing
        firebase_uid (str): Unique Firebase user identifier
        profile (Profile): One-to-one relationship with user profile
        interviews (List[Interview]): One-to-many relationship with interviews
        created_at (datetime): Timestamp when user was created
        updated_at (datetime): Timestamp when user was last updated
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    firebase_uid: Mapped[str] = mapped_column(String(128), unique=True)
    profile: Mapped["Profile"] = relationship("Profile", back_populates="user", cascade="all", uselist=False)
    interviews: Mapped[List["Interview"]] = relationship("Interview", back_populates="user", cascade="all")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    def __repr__(self):
        profile_name = self.profile.name if self.profile else "No Profile"
        return f"User(name={profile_name})"

class Profile(Base):
    """User profile information and preferences.
    
    Stores detailed user information that can be updated independently
    of the core User entity. Maintains a one-to-one relationship with User.
    
    Attributes:
        id (int): Primary key, auto-incrementing
        name (str, optional): User's display name
        email (str): User's email address (unique)
        job_role (str, optional): User's professional role
        last_login (datetime): Timestamp of last login, auto-updated
        user_id (int): Foreign key to User table
        user (User): One-to-one relationship with User
    """
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
    """Interview session record.
    
    Represents a single interview session conducted by a user, including
    metadata about the session and relationships to asked questions.
    
    Attributes:
        id (UUID): Primary key, auto-generated UUID
        user_id (int): Foreign key to User table
        date (DateTime): When the interview was conducted
        questions (List[InterviewQuestion]): Questions asked in this interview
        duration (int, optional): Interview duration in seconds
        interview_type (str): Type/category of interview
        created_at (datetime): Timestamp when record was created
        updated_at (datetime): Timestamp when record was last updated
        user (User): Many-to-one relationship with User
    """
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
    """Master question repository.
    
    Contains all available interview questions that can be used across
    different interview sessions. Questions are categorized by type,
    job role, and job level.
    
    Attributes:
        id (UUID): Primary key, auto-generated UUID
        question (str): The question text (max 500 chars)
        question_type (str): Category/type of question
        job_role (str): Target job role for this question
        job_level (str): Target job level (junior, mid, senior, etc.)
        interview (List[InterviewQuestion]): Usage history in interviews
    """
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
    """Question instance within a specific interview.
    
    Represents a question that was asked during a specific interview session,
    including the user's answer, scoring, and feedback. Links Questions to
    Interviews with additional contextual data.
    
    Attributes:
        id (UUID): Primary key, auto-generated UUID
        interview_id (UUID): Foreign key to Interview table
        question_id (UUID): Foreign key to Question table
        question_text (str): The actual question text asked (may differ from master)
        answer (str): User's response to the question (max 2000 chars)
        score (int): Numerical score assigned to the answer
        tips (List[str]): Improvement tips stored as JSON array
        feedback (str): Detailed feedback on the answer (max 2000 chars)
        answered_at (datetime): Timestamp when question was answered
        interview (Interview): Many-to-one relationship with Interview
        question (Question): Many-to-one relationship with Question
    """
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
