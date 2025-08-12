from datetime import datetime
from sqlalchemy import func
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    DateTime,
    ForeignKey,
    Date,
    Float,
)
from sqlalchemy.orm import relationship
from database import Base
from passlib.context import CryptContext
from werkzeug.security import generate_password_hash, check_password_hash

pwd_context = CryptContext(schemes=["scrypt"], deprecated="auto")


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    school_name = Column(String(200), nullable=True)
    school_logo = Column(Text, nullable=True)
    password_hash = Column(String, unique=True, nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    last_login = Column(DateTime, nullable=True)

    classes = relationship(
        "Class", backref="teacher", lazy=True, cascade="all, delete-orphan"
    )
    wagoll_examples = relationship(
        "WagollExample", backref="teacher", lazy=True, cascade="all, delete-orphan"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def to_dict(self, db_session) -> dict:
        """Converts user to dictionary with metrics using injected DB session"""

        class_count = len(self.classes)

        student_count = (
            db_session.query(Student)
            .join(Class)
            .filter(Class.teacher_id == self.id)
            .count()
        )

        upload_count = (
            db_session.query(Writing)
            .join(Student)
            .join(Class)
            .filter(Class.teacher_id == self.id)
            .count()
        )

        return {
            "id": self.id,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "email": self.email,
            "school_name": self.school_name,
            "is_admin": self.is_admin,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "class_count": class_count,
            "student_count": student_count,
            "upload_count": upload_count,
        }


class Class(Base):

    __tablename__ = "class"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    year_group = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    teacher_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    students = relationship(
        "Student", backref="class_group", lazy=True, cascade="all, delete-orphan"
    )
    assignments = relationship(
        "Assignment", backref="class_group", lazy=True, cascade="all, delete-orphan"
    )


class Student(Base):

    __tablename__ = "student"

    id = Column(Integer, primary_key=True)
    student_id = Column(String(50), nullable=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    date_of_birth = Column(Date, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    class_id = Column(
        Integer, ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    writing_samples = relationship(
        "Writing", backref="student", lazy=True, cascade="all, delete-orphan"
    )

    @property
    def name(self):
        """Maintain backwards compatibility with existing code"""
        return f"{self.first_name} {self.last_name}"


class Writing(Base):

    __tablename__ = "writing"

    id = Column(Integer, primary_key=True)
    filename = Column(String(255), nullable=False)
    text_content = Column(Text, nullable=False)
    writing_age = Column(String(50))
    feedback = Column(Text)
    created_at = Column(DateTime, default=datetime.now)
    student_id = Column(
        Integer, ForeignKey("student.id", ondelete="CASCADE"), nullable=False
    )
    assignment_id = Column(
        Integer, ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True
    )
    total_marks_percentage = Column(Float, nullable=True)
    criteria_marks = relationship(
        "CriteriaMark", backref="writing", lazy=True, cascade="all, delete-orphan"
    )
    analysis_feedback = relationship(
        "AnalysisFeedback", backref="writing", lazy=True, cascade="all, delete-orphan"
    )


class Assignment(Base):

    __tablename__ = "assignment"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    curriculum = Column(String(50), nullable=True)
    genre = Column(String(50), nullable=True)
    year_group = Column(String(50), nullable=True)
    due_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    class_id = Column(
        Integer, ForeignKey("class.id", ondelete="CASCADE"), nullable=False
    )
    criteria = relationship(
        "Criteria", backref="assignment", lazy=True, cascade="all, delete-orphan"
    )
    submissions = relationship("Writing", backref="assignment", lazy=True)


class Criteria(Base):

    __tablename__ = "criteria"

    id = Column(Integer, primary_key=True)
    description = Column(String(500), nullable=False)
    assignment_id = Column(
        Integer, ForeignKey("assignment.id", ondelete="CASCADE"), nullable=False
    )
    # Add relationship to marks with cascade delete
    marks = relationship(
        "CriteriaMark", backref="criteria", lazy=True, cascade="all, delete-orphan"
    )


class CriteriaMark(Base):

    __tablename__ = "criteria_mark"

    id = Column(Integer, primary_key=True)
    score = Column(
        Integer, nullable=False
    ) 
    writing_id = Column(
        Integer, ForeignKey("writing.id", ondelete="CASCADE"), nullable=False
    )
    criteria_id = Column(
        Integer, ForeignKey("criteria.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.now)


class AnalysisFeedback(Base):

    __tablename__ = "analysis_feedback"

    id = Column(Integer, primary_key=True)
    writing_id = Column(
        Integer, ForeignKey("writing.id", ondelete="CASCADE"), nullable=False
    )
    is_helpful = Column(Boolean, nullable=False)
    writing_age_accurate = Column(Boolean, nullable=True)
    strengths_accurate = Column(Boolean, nullable=True)
    development_accurate = Column(Boolean, nullable=True)
    criteria_accurate = Column(Boolean, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now)


class WagollExample(Base):

    __tablename__ = "wagoll_example"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    explanations = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)
    assignment_id = Column(
        Integer, ForeignKey("assignment.id", ondelete="SET NULL"), nullable=True
    )
    teacher_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
   
    assignment = relationship("Assignment", backref="wagollexamples", lazy=True)


