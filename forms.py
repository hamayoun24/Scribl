from pydantic import BaseModel, EmailStr, Field, model_validator
from datetime import date
from enum import Enum
from typing import Optional


class LoginForm(BaseModel):
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")


class SignupForm(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, example="John")
    last_name: str = Field(..., min_length=2, max_length=50, example="Doe")
    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., min_length=8, example="securePassword123")
    confirm_password: str = Field(..., example="securePassword123")

    @model_validator(mode="after")
    def password_match(cls, values):
        if values.password != values.confirm_password:
            raise ValueError("Passwords do not match")
        return values


class ClassForm(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Class name")
    year_group: str = Field(..., description="Year group")


class StudentForm(BaseModel):
    student_id: Optional[str] = Field(None, max_length=50, description="Student ID")
    first_name: str = Field(..., min_length=2, max_length=50, description="First name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Last name")
    date_of_birth: date = Field(..., description="Date of birth")





# models/assignment.py
from typing import Optional, Literal
from pydantic import BaseModel, Field

class AssignmentForm(BaseModel):
    title: str = Field(..., max_length=200, description="Assignment Title")
    description: Optional[str] = Field(None, max_length=500, description="Assignment Description")
    
    curriculum: Literal[
        'english',
        'american',
        'ib',
        'australian'
    ] = Field(..., description="Curriculum Type")
    
    genre: Literal[
        'narrative',
        'descriptive',
        'persuasive',
        'expository',
        'poetry',
        'report',
        'letter',
        'journal',
        'custom'
    ] = Field(..., description="Genre of writing")
    
    custom_genre: Optional[str] = Field(None, max_length=100, description="Custom genre if genre=custom")


class SettingsForm(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=50, description="First name")
    last_name: str = Field(..., min_length=2, max_length=50, description="Last name")
    school_name: Optional[str] = Field(None, max_length=200, description="School name")
