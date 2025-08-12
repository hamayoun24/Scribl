from fastapi import (
    Request,
    Depends,
    Form,
    HTTPException,
    UploadFile,
    File,
    Query,
    status,
)
from sqlalchemy import text
from PIL import Image, ImageEnhance, ImageFilter
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response, HTMLResponse, StreamingResponse
from starlette.status import (
    HTTP_302_FOUND,
    HTTP_201_CREATED,
    HTTP_200_OK,
    HTTP_500_INTERNAL_SERVER_ERROR,
    HTTP_303_SEE_OTHER,
)
from mailchimp_utils import add_user_to_mailchimp, tag_user_first_analysis
from pydantic import ValidationError
from sqlalchemy.orm import Session
from fastapi import FastAPI
from database import get_db
from models import (
    Student,
    Class,
    User,
    Writing,
    Assignment,
    AnalysisFeedback,
    Criteria,
    WagollExample,
    CriteriaMark,
)
from forms import (
    StudentForm,
    LoginForm,
    ClassForm,
    SignupForm,
    AssignmentForm,
    SettingsForm,
)
from sqlalchemy import func, case, distinct, desc
from dependencies.auth import get_current_user, login_user
from image_processing import (
    analyze_writing,
    allowed_file,
    encode_image_to_base64,
    evaluate_criteria,
)
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
from starlette.config import Config

from typing import Optional, List, Union
from config import settings as env_settings
import io
import base64
from PIL import Image
import logging
from datetime import datetime, date, timedelta
from markupsafe import Markup, escape
from io import StringIO, BytesIO
import csv
import os
import json
import secrets
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware


def nl2br(value: str):
    return Markup("<br>".join(escape(value).splitlines()))


logger = logging.getLogger(__name__)


templates = Jinja2Templates(directory="templates")
templates.env.filters["nl2br"] = nl2br


allowed_hosts = [
    "0.0.0.0",
    "localhost",
    "127.0.0.1",
    "js-projects-scribl.wjhk3s.easypanel.host",
    "scribl-v1.onrender.com",
    "*.onrender.com",
]


# Use one HTTPS redirect middleware
class PermanentHTTPSRedirectMiddleware(HTTPSRedirectMiddleware):
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            host = headers.get(b"host", b"").decode("latin-1")
            if not is_local_development():  # only redirect if NOT local
                scheme = scope.get("scheme", "http")
                if scheme != "https":
                    url = f"https://{host}{scope['path']}"
                    if scope["query_string"]:
                        url += f"?{scope['query_string'].decode()}"
                    response = RedirectResponse(url, status_code=301)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


def is_local_development(request: Request = None):
    local_hosts = ["localhost", "127.0.0.1", "0.0.0.0"]
    if request:
        host = request.headers.get("host", "").split(":")[0]
        return host in local_hosts
    return os.environ.get("ENVIRONMENT", "development") != "production"


def is_production(request: Request = None):
    production_hosts = [
        "js-projects-scribl.wjhk3s.easypanel.host",
        "scribl-v1.onrender.com",
    ]
    if request:
        host = request.headers.get("host", "").split(":")[0]
        return host in production_hosts
    return False


templates.env.globals.update(is_production=is_production)


middleware = [
    Middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts),
    Middleware(
        SessionMiddleware,
        secret_key=env_settings.SESSION_SECRET,
        session_cookie="sessionid",
        same_site="lax",
        https_only=True,
        max_age=3600 * 24,
    ),
    Middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]


app = FastAPI(middleware=middleware)

if not is_local_development():
    app.add_middleware(PermanentHTTPSRedirectMiddleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    if is_production(request):
        response.headers.update(
            {
                "Content-Security-Policy": "upgrade-insecure-requests",
                "X-Content-Type-Options": "nosniff",
                "X-Frame-Options": "DENY",
            }
        )

        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=63072000; includeSubDomains; preload"
            )

    return response


class NoCacheStaticMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if request.url.path.startswith("/static/"):
            response.headers.update(
                {
                    "Cache-Control": "no-store, no-cache, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0",
                }
            )
        return response


app.mount("/static", StaticFiles(directory="static"), name="static")
app.add_middleware(NoCacheStaticMiddleware)


async def get_csrf_token(request: Request) -> str:
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = secrets.token_urlsafe(32)
    return request.session["csrf_token"]


async def validate_csrf_token(request: Request, token: str):
    session_token = request.session.get("csrf_token")
    if not session_token:
        raise HTTPException(status_code=403, detail="Missing CSRF token in session")

    if len(token) != len(session_token):
        raise HTTPException(status_code=403, detail="Invalid CSRF token length")

    if not secrets.compare_digest(token, session_token):
        raise HTTPException(status_code=403, detail="CSRF tokens do not match")

    request.session["csrf_token"] = secrets.token_urlsafe(32)


# Static files with no-cache headers
@app.get("/static/{filename:path}", name="static")
async def static_files(filename: str):
    static_file_path = os.path.join("static", filename)
    if not os.path.exists(static_file_path):
        raise HTTPException(status_code=404, detail="File not found")

    headers = {
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
    }
    return FileResponse(static_file_path, headers=headers)


# Add Student
@app.post("/add_student")
async def add_student(
    request: Request,
    student_id: str = Form(...),
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: date = Form(None),
    class_id: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not class_id:
        request.session["flash"] = {"message": "Class ID is required", "type": "error"}
        return RedirectResponse(url="/classes", status_code=HTTP_302_FOUND)

    class_obj = db.get(Class, class_id)
    if not class_obj or class_obj.teacher_id != request.session["user_id"]:
        request.session["flash"] = {
            "message": "Invalid Class Selected",
            "category": "error",
        }
        return RedirectResponse(url="/classes", status_code=HTTP_302_FOUND)

    try:
        student = Student(
            student_id=student_id,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            class_id=class_id,
        )
        db.add(student)
        db.commit()
        request.session["flash"] = {
            "message": "Student added successfully",
            "category": "success",
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error adding student: {e}")
        request.session["flash"] = {
            "message": "Error adding student",
            "category": "error",
        }

    return RedirectResponse(
        url=f"/classes?class_id={class_id}", status_code=HTTP_302_FOUND
    )


@app.get("/get_students/{class_id}", response_class=JSONResponse)
async def get_students(
    request: Request,
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Retrieve class or return 404
    class_obj = db.query(Class).filter_by(id=class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    # Check teacher ownership
    if class_obj.teacher_id != request.session["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")

    # Query students for the class
    students = db.query(Student).filter_by(class_id=class_id).all()

    # Calculate age (approximate)
    today = date.today()
    student_data = [
        {
            "id": student.id,
            "name": f"{student.first_name} {student.last_name}",
            "age": (today - student.date_of_birth).days // 365,
        }
        for student in students
    ]

    return student_data


@app.post("/student/{student_id}/delete")
def delete_student(
    request: Request,
    student_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from models import Student

    student = db.query(Student).get(student_id)

    # Check if current user is the teacher of this student's class
    if student.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        db.delete(student)
        db.commit()
        request.session["flash"] = ("Student deleted successfully!", "success")
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        logger.error(f"Error deleting student: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, content={"error": "Failed to delete student"}
        )


@app.post(
    "/process_image",
)
async def process_image(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process uploaded writing sample image and return analysis."""
    try:
        # Get the base64 image data from the request
        data = await request.json()
        if not data or "image" not in data:
            return JSONResponse(
                status_code=400, content={"error": "No image data provided"}
            )

        base64_image = data["image"].split(",")[
            1
        ]  # Remove the data:image/jpeg;base64, prefix
        assignment_id = data.get("assignment_id")
        student_id = data.get("student_id")

        # Get assignment if ID provided
        assignment = None
        if assignment_id:
            assignment = db.query(Assignment).get(assignment_id)

        # Analyze the writing
        analysis_result = analyze_writing(base64_image, assignment)

        if analysis_result:
            # Create new writing record
            writing_sample = Writing(
                filename=data.get("filename", "uploaded_image.jpg"),
                image_data=base64_image,
                analysis_result=json.dumps(analysis_result),
                text_content=analysis_result.get("extracted_text", ""),
                writing_age=analysis_result.get("age", ""),
                feedback=analysis_result.get("feedback", ""),
                user_id=current_user.id,
                assignment_id=assignment_id if assignment_id else None,
                student_id=student_id if student_id else None,
                created_at=datetime.now(),
            )

            # Save to database
            db.add(writing_sample)
            db.commit()

            # Check if this is the user's first writing analysis
            try:
                # Get all writings connected to students in classes taught by this teacher
                writing_count = (
                    db.query(Writing)
                    .join(Student)
                    .join(Class)
                    .filter(Class.teacher_id == current_user.id)
                    .count()
                )

                if writing_count == 1:  # This means it's their first writing
                    success = tag_user_first_analysis(current_user.email)
                    if success:
                        logger.info(
                            f"Successfully tagged user {current_user.email} with 'Scribl Used'"
                        )
                    else:
                        logger.warning(
                            f"Failed to tag user {current_user.email} with 'Scribl Used'"
                        )
            except Exception as e:
                logger.error(f"Error checking first writing analysis: {str(e)}")
                # Continue with the response even if tagging fails

            return JSONResponse(
                {
                    "request": request,
                    "status": "success",
                    "analysis": analysis_result,
                    "writing_id": writing_sample.id,
                }
            )
        else:
            return JSONResponse(
                status_code=500, content={"error": "Failed to analyze writing"}
            )

    except Exception as e:
        logger.error(f"Error processing image: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/login")
async def show_login_form(request: Request):
    csrf_token = await get_csrf_token(request)
    response = templates.TemplateResponse(
        "login.html", {"request": request, "csrf_token": csrf_token}
    )
    # Explicitly set cookie headers
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    # Validate CSRF token first
    await validate_csrf_token(request, csrf_token)

    email = email.lower()
    user = db.query(User).filter_by(email=email).first()

    try:
        if not user:
            logger.warning(f"Failed login attempt for user: {email}")
            return RedirectResponse(
                url="/login?error=Invalid+email+or+password", status_code=HTTP_302_FOUND
            )

        if not user.check_password(password):
            logger.warning(f"Failed login attempt for user: {email}")
            return RedirectResponse(
                url="/login?error=Invalid+email+or+password", status_code=HTTP_302_FOUND
            )

        # Successful login
        db.commit()

        request.session["user_id"] = user.id
        request.session["_fresh"] = True  # Mark session as fresh
        logger.info(f"Successful login for user: {email}")

        return RedirectResponse(url="/home", status_code=HTTP_302_FOUND)

    except Exception as e:
        logger.error(f"Error during login: {e}")
        return RedirectResponse(
            url="/login?error=An+error+occurred+during+login",
            status_code=HTTP_302_FOUND,
        )


@app.post("/signup", response_class=HTMLResponse)
async def signup(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    try:
        form = SignupForm(
            first_name=first_name,
            last_name=last_name,
            email=email,
            password=password,
            confirm_password=confirm_password,
        )
    except Exception as e:
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "form": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
                "error": str(e),
            },
        )

    if db.query(User).filter_by(email=form.email).first():
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "form": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
                "error": "Email already registered",
            },
        )

    user = User(
        first_name=form.first_name,
        last_name=form.last_name,
        email=form.email,
        created_at=datetime.now(),
    )
    user.set_password(form.password)
   
    try:
        db.add(user)
        db.commit()
        logger.info(f"Successfully created user account for {user.email}")

        try:
            success = add_user_to_mailchimp(
                email=user.email, first_name=user.first_name, last_name=user.last_name
            )
            if success:
                request.session["flash"] = "User Created Successfully.."
                logger.info(f"Successfully added {user.email} to Mailchimp audience")
            else:
                logger.warning(f"Failed to add {user.email} to Mailchimp audience")
        except Exception as e:
            logger.error(f"Mailchimp error for {user.email}: {str(e)}")

        login_user(request, user)
        return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)

    except Exception as e:
        db.rollback()
        logger.error(f"Database error during signup: {str(e)}")
        return templates.TemplateResponse(
            "signup.html",
            {
                "request": request,
                "form": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                },
                "error": "An error occurred during signup. Please try again.",
            },
        )


@app.get("/logout", name="logout")
async def logout(request: Request, response: Response):
    request.session.pop("user_id", None)
    response.delete_cookie("session")
    return RedirectResponse(url="/login", status_code=HTTP_302_FOUND)


@app.post("/admin/delete-user/{user_id}")
def delete_user(
    user_id,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a single user and their associated data."""
    logger.info(f"Delete user request received for user_id: {user_id}")
    logger.info(
        f"Current user: {current_user.email}, is_admin: {getattr(current_user, 'is_admin', False)}"
    )

    if current_user not in request.session:
        logger.warning("Unauthorized: User not authenticated")
        return (
            JSONResponse(
                status_code=403, content={"error": "Unauthorized - not authenticated"}
            ),
        )

    if not current_user.is_admin:
        logger.warning(f"Unauthorized: User {current_user.email} is not an admin")
        return (
            JSONResponse(
                status_code=403, content={"error": "Unauthorized - not admin"}
            ),
        )

    try:
        user_to_delete = db.query(User).get(user_id)

        # Don't allow admin to delete themselves
        if user_to_delete.id == current_user.id:
            logger.warning("Attempted to delete own admin account")
            return (
                JSONResponse(
                    status_code=400,
                    content={"error": "Cannot delete your own admin account"},
                ),
            )

        # Delete associated data using SQLAlchemy cascade
        db.delete(user_to_delete)
        db.commit()

        logger.info(f"Successfully deleted user {user_id}")
        return (
            JSONResponse(
                status_code=200, content={"message": "User deleted successfully"}
            ),
        )

    except Exception as e:
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        db.rollback()
        return (
            JSONResponse(status_code=500, content={"error": "Failed to delete user"}),
        )


@app.get("/admin")
def admin_dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Admin dashboard with enhanced user metrics and management."""
    if not current_user.is_admin:
        request.session["flash"] = "Unauthorized access"
        return RedirectResponse(url="index")

    try:
        # Get all teachers (non-admin users)
        teachers = db.query(User).filter_by(is_admin=False).all()

        # Calculate overall metrics
        metrics = {
            "total_users": db.query(User).count(),
            "total_writings": db.query(Writing).count(),
            "total_classes": db.query(Class).count(),
            "total_students": db.query(Student).count(),
        }

        logger.info(f"Admin dashboard loaded with {len(teachers)} teachers")
        return templates.TemplateResponse(
            "admin_dashboard.html",
            {"request": request, "teachers": teachers, "metrics": metrics},
        )

    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}")
        request.session["flash"] = "An error occurred while loading the dashboard"
        return RedirectResponse(url="index")


@app.get("/wagoll_library", response_class=HTMLResponse)
async def wagoll_library(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View all WAGOLL examples in the teacher's library."""

    my_examples = (
        db.query(WagollExample)
        .filter_by(teacher_id=current_user.id)
        .order_by(WagollExample.updated_at.desc())
        .all()
    )

    public_examples = (
        db.query(WagollExample)
        .filter(
            WagollExample.teacher_id != current_user.id,
            WagollExample.is_public.is_(True),
        )
        .order_by(WagollExample.updated_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "wagoll_library.html",
        {
            "request": request,
            "my_examples": my_examples,
            "public_examples": public_examples,
        },
    )


@app.get("/classes", response_class=HTMLResponse)
async def classes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    class_form = ClassForm(name="New", year_group="2025")
    student_form = StudentForm(
        student_id=None, first_name="John", last_name="Doe", date_of_birth=date.today()
    )

    user_classes = db.query(Class).filter_by(teacher_id=current_user.id).all()

    for class_ in user_classes:
        class_.students = sorted(
            class_.students, key=lambda s: f"{s.first_name} {s.last_name}"
        )
        for student in class_.students:
            student.writing_samples = (
                db.query(Writing).filter_by(student_id=student.id).all()
            )

    return templates.TemplateResponse(
        "classes.html",
        {
            "request": request,
            "class_form": class_form,
            "student_form": student_form,
            "classes": user_classes,
        },
    )


@app.get("/view_classes/export/{class_id}", response_class=StreamingResponse)
def export_class_overview(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    class_obj = db.query(Class).get(class_id)

    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "Student Name",
            "Latest Writing Age",
            "Total Submissions",
            "Assignment Submissions",
            "Free Writing Submissions",
            "Average Score",
            "Latest Submission Date",
        ]
    )

    for student in class_obj.students:
        samples = (
            db.query(Writing)
            .filter_by(student_id=student.id)
            .order_by(Writing.created_at.desc())
            .all()
        )

        if samples:
            latest_writing_age = samples[0].writing_age
            latest_submission = samples[0].created_at.strftime("%Y-%m-%d")
            total_submissions = len(samples)
            assignment_submissions = len([s for s in samples if s.assignment_id])
            free_writing = total_submissions - assignment_submissions

            scores = []
            for sample in samples:
                if sample.assignment_id and sample.criteria_marks:
                    total_possible = len(sample.criteria_marks) * 2
                    achieved = sum(mark.score for mark in sample.criteria_marks)
                    if total_possible > 0:
                        scores.append((achieved / total_possible) * 100)

            avg_score = f"{round(sum(scores) / len(scores), 1)}%" if scores else "N/A"
        else:
            latest_writing_age = "No submissions"
            latest_submission = "N/A"
            total_submissions = 0
            assignment_submissions = 0
            free_writing = 0
            avg_score = "N/A"

        writer.writerow(
            [
                f"{student.first_name} {student.last_name}",
                latest_writing_age,
                total_submissions,
                assignment_submissions,
                free_writing,
                avg_score,
                latest_submission,
            ]
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename=class_{class_id}_overview_{datetime.now().strftime('%Y%m%d')}.csv"
        },
    )


@app.post("/class/{class_id}/delete", status_code=200)
async def delete_class(
    class_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)
):
    class_obj = db.query(Class).filter_by(id=class_id).first()

    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    sql_queries = [
        # First delete criteria marks
        """DELETE FROM criteria_mark WHERE writing_id IN (
            SELECT w.id FROM writing w
            JOIN student s ON w.student_id = s.id
            WHERE s.class_id = :class_id
        );""",
        # Delete criteria
        """DELETE FROM criteria WHERE assignment_id IN (
            SELECT id FROM assignment WHERE class_id = :class_id
        );""",
        # Delete writings
        """DELETE FROM writing WHERE student_id IN (
            SELECT id FROM student WHERE class_id = :class_id
        );""",
        # Delete assignments
        "DELETE FROM assignment WHERE class_id = :class_id;",
        # Delete students
        "DELETE FROM student WHERE class_id = :class_id;",
        # Finally delete the class
        "DELETE FROM class WHERE id = :class_id;",
    ]

    try:
        for sql in sql_queries:
            db.execute(text(sql), {"class_id": class_id})

        db.commit()
        return JSONResponse(content={"success": True}, status_code=HTTP_200_OK)
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting class {class_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete class")


@app.post("/upload_students")
async def upload_students(
    request: Request,
    file: UploadFile,
    class_id: int = Form(...),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        request.session["flash"] = ("Please upload a CSV file", "error")
        return RedirectResponse(url="/classes", status_code=HTTP_303_SEE_OTHER)

    try:
        stream = StringIO((await file.read()).decode("UTF8"))
        csv_input = csv.DictReader(stream)

        students_added = 0
        row_errors = []

        logger.debug(f"CSV Headers: {csv_input.fieldnames}")

        for row_num, row in enumerate(csv_input, start=1):
            try:
                logger.debug(f"Processing CSV row {row_num}: {dict(row)}")

                first_name = row.get("First Name", "").strip()
                last_name = row.get("Last Name", "").strip()
                student_id = row.get("Student ID", "").strip() or None

                if not first_name or not last_name:
                    row_errors.append(f"Row {row_num}: First and last name required")
                    continue

                try:
                    dob = datetime.strptime(
                        row.get("Date of Birth", "").strip(), "%Y-%m-%d"
                    ).date()
                except ValueError:
                    row_errors.append(f"Row {row_num}: Invalid date format")
                    continue

                student = Student(
                    student_id=student_id,
                    first_name=first_name,
                    last_name=last_name,
                    date_of_birth=dob,
                    class_id=class_id,
                )
                db.add(student)
                students_added += 1

            except Exception as e:
                logger.error(f"Error in row {row_num}: {str(e)}")
                row_errors.append(f"Row {row_num}: {str(e)}")

        if students_added:
            try:
                db.commit()
                flash_msg = f"Added {students_added} students."
                if row_errors:
                    flash_msg += " Some rows had errors."
                request.session["flash"] = (flash_msg, "info")
            except Exception as e:
                db.rollback()
                logger.error(f"DB commit error: {str(e)}")
                request.session["flash"] = ("Error saving students.", "error")
        else:
            request.session["flash"] = (
                "No students added. Check CSV format.",
                "warning",
            )

    except Exception as e:
        logger.error(f"CSV processing error: {str(e)}")
        request.session["flash"] = (
            "Error processing CSV. Format: Student ID, First Name, Last Name, Date of Birth (YYYY-MM-DD)",
            "error",
        )

    return RedirectResponse(url="/classes", status_code=HTTP_303_SEE_OTHER)


@app.get("/class/{class_id}/export_data")
async def export_class_data(
    class_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    class_obj = db.query(Class).get(class_id)

    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        output = StringIO()
        writer = csv.writer(output)

        writer.writerow(
            [
                "Student Name",
                "Assignment Title",
                "Submission Date",
                "Writing Age",
                "Total Score",
                "Max Possible Score",
                "Achievement Percentage",
                "Strengths",
                "Areas for Development",
            ]
        )

        assignments = db.query(Assignment).filter_by(class_id=class_id).all()

        for student in class_obj.students:
            for assignment in assignments:
                submission = (
                    db.query(Writing)
                    .filter_by(student_id=student.id, assignment_id=assignment.id)
                    .first()
                )

                if submission:
                    total_possible_marks = len(submission.criteria_marks) * 2
                    achieved_marks = sum(
                        mark.score for mark in submission.criteria_marks
                    )
                    percentage = (
                        round((achieved_marks / total_possible_marks * 100), 1)
                        if total_possible_marks > 0
                        else 0
                    )

                    feedback_parts = (
                        submission.feedback.split("\n\n")
                        if submission.feedback
                        else ["", ""]
                    )
                    strengths = (
                        feedback_parts[0].replace("Strengths:", "").strip()
                        if len(feedback_parts) > 0
                        else ""
                    )
                    development = (
                        feedback_parts[1].replace("Areas for Development:", "").strip()
                        if len(feedback_parts) > 1
                        else ""
                    )

                    writer.writerow(
                        [
                            f"{student.first_name} {student.last_name}",
                            assignment.title,
                            submission.created_at.strftime("%Y-%m-%d"),
                            submission.writing_age,
                            achieved_marks,
                            total_possible_marks,
                            f"{percentage}%",
                            strengths,
                            development,
                        ]
                    )

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename=class_{class_id}_performance_{datetime.now().strftime("%Y%m%d")}.csv'
            },
        )

    except Exception as e:
        logger.error(f"Error exporting class data: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export class data")


@app.get("/get_assignments/{class_id}", response_class=JSONResponse)
async def get_assignments(
    class_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    class_obj = db.query(Class).filter_by(id=class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    assignments = (
        db.query(Assignment)
        .filter_by(class_id=class_id)
        .order_by(Assignment.created_at.desc())
        .all()
    )

    return [
        {
            "id": a.id,
            "title": a.title,
            "curriculum": a.curriculum,
            "genre": a.genre,
            "created_at": a.created_at,
        }
        for a in assignments
    ]


@app.get("/class/{class_id}/assignments/new", response_class=HTMLResponse)
async def get_assignment_form(
    class_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: any = Depends(get_current_user),
):
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    return templates.TemplateResponse(
        "create_assignment.html",
        {
            "request": request,
            "class_obj": class_obj,
            "form_data": {},
            "form_errors": [],
        },
    )


@app.api_route("/settings", methods=["GET", "POST"], response_class=HTMLResponse)
async def settings(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    school_logo: Optional[UploadFile] = File(None),
):
    """
    Handles:
    - GET: Settings page display
    - POST (Form or multipart): Settings update
    - POST (JSON): Logo removal
    """
    # Handle JSON payload for logo removal
    if request.headers.get("content-type", "").startswith("application/json"):
        try:
            body = await request.json()
            if body.get("remove_logo") is True:
                current_user.school_logo = None
                db.commit()
                return JSONResponse(content={"success": True})
        except Exception as e:
            logger.error(f"Error removing logo: {str(e)}")
            db.rollback()
            return JSONResponse(
                status_code=500, content={"error": "Failed to remove logo"}
            )

    if request.method == "POST":
        form_data = await request.form()
        try:
            form = SettingsForm(
                first_name=form_data.get("first_name"),
                last_name=form_data.get("last_name"),
                school_name=form_data.get("school_name"),
            )
        except Exception as e:
            logger.warning(f"Validation error: {str(e)}")
            return templates.TemplateResponse(
                "settings.html",
                {
                    "request": request,
                    "form_data": form_data,
                    "errors": str(e),
                },
                status_code=422,
            )

        try:
            current_user.first_name = form.first_name
            current_user.last_name = form.last_name
            current_user.school_name = form.school_name

            if school_logo and allowed_file(school_logo.filename):
                img = Image.open(school_logo.file)
                img.thumbnail((200, 200))
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                encoded_logo = base64.b64encode(buffer.getvalue()).decode("utf-8")
                current_user.school_logo = encoded_logo

            db.commit()
            request.session["flash"] = {
                "message": "Settings updated successfully!",
                "category": "success",
            }
            return RedirectResponse(url="/settings", status_code=302)

        except Exception as e:
            logger.error(f"Failed to update settings: {str(e)}")
            db.rollback()
            request.session["flash"] = {
                "message": "Error updating settings",
                "category": "danger",
            }
            return RedirectResponse(url="/settings", status_code=302)

    # GET Request - render template
    return templates.TemplateResponse(
        "settings.html",
        {
            "request": request,
            "current_user": current_user,
            "form": {
                "first_name": current_user.first_name,
                "last_name": current_user.last_name,
                "school_name": current_user.school_name,
            },
        },
    )


@app.post("/update_settings", response_class=HTMLResponse)
async def update_settings(
    first_name: str = Form(...),
    last_name: str = Form(...),
    school_name: Optional[str] = Form(None),
    school_logo: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        # Update the user data
        current_user.first_name = first_name
        current_user.last_name = last_name
        current_user.school_name = school_name

        # Handle logo upload if available
        if school_logo:
            img = Image.open(school_logo.file)
            img.thumbnail((200, 200))  # Resize while maintaining aspect ratio
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format="PNG")
            img_byte_arr = img_byte_arr.getvalue()
            current_user.school_logo = base64.b64encode(img_byte_arr).decode("utf-8")

        db.commit()
        return HTMLResponse(
            content="Settings updated successfully!", status_code=HTTP_200_OK
        )

    except Exception as e:
        db.rollback()
        return HTMLResponse(
            content=f"Error updating settings: {str(e)}",
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.post("/remove_logo", response_class=JSONResponse)
async def remove_logo(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    try:
        # Remove the logo
        current_user.school_logo = None
        db.commit()
        return JSONResponse(content={"success": True}, status_code=HTTP_200_OK)
    except Exception as e:
        db.rollback()
        return JSONResponse(
            content={"error": "Failed to remove logo"},
            status_code=HTTP_500_INTERNAL_SERVER_ERROR,
        )


@app.post("/save_to_wagoll")
async def save_to_wagoll(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a writing sample as a WAGOLL example from index page."""
    try:
        data = await request.json()
        title = data.get("title")
        content = data.get("content")
        explanations = data.get("explanations", "")
        is_public = data.get("is_public", False)
        writing_id = data.get("writing_id")
        assignment_id = data.get("assignment_id")

        logger.debug(
            f"WAGOLL save request received: title={title}, content length={len(content) if content else 'None'}"
        )

        if not title or not content:
            logger.error(
                f"Missing required fields: title={bool(title)}, content={bool(content)}"
            )
            return (
                JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "Title and content are required",
                    },
                ),
            )

        # Import the model
        from models import WagollExample, Writing

        # If we have a writing ID but no content, try to get content from the writing sample
        if writing_id and not content and db.query(Writing).get(writing_id):
            writing = db.query(Writing).get(writing_id)
            if writing and writing.text_content:
                content = writing.text_content
                logger.debug(f"Retrieved content from writing ID {writing_id}")

        # Double-check content after potential retrieval
        if not content:
            logger.error(
                "Content still missing after attempting to retrieve from writing_id"
            )
            return (
                JSONResponse(
                    status_code=400,
                    content={"success": False, "error": "Content isrequired"},
                ),
            )

        # Create the WAGOLL example
        example = WagollExample(
            title=title,
            content=content,
            explanations=explanations,
            is_public=is_public,
            assignment_id=assignment_id,
            teacher_id=current_user.id,
            writing_id=writing_id,
        )

        db.add(example)
        db.commit()
        logger.debug(f"WAGOLL example saved successfully with ID: {example.id}")

        return JSONResponse(content={"success": True, "id": example.id})

    except Exception as e:
        logger.error(f"Error saving WAGOLL from index: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


# FastAPI equivalent for the /add_class endpoint and admin dashboard view


@app.post("/add_class", response_class=HTMLResponse)
def add_class(
    name: str = Form(...),
    year_group: str = Form(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_class = Class(name=name, year_group=year_group, teacher_id=current_user.id)
    db.add(new_class)
    db.commit()

    # Dashboard metrics
    teacher_data = (
        db.query(
            User.id,
            (User.first_name + " " + User.last_name).label("name"),
            User.email,
            User.school_name,
            func.count(Writing.id).label("writings_count"),
            func.count(distinct(Class.id)).label("classes_count"),
            func.count(distinct(Student.id)).label("students_count"),
            func.max(Writing.created_at).label("last_activity"),
        )
        .outerjoin(Class, User.id == Class.teacher_id)
        .outerjoin(Student, Class.id == Student.class_id)
        .outerjoin(Writing, Student.id == Writing.student_id)
        .group_by(User.id)
        .order_by(desc("writings_count"))
        .limit(10)
        .all()
    )

    top_teachers = []
    teacher_names = []
    teacher_writing_counts = []

    for teacher in teacher_data:
        top_teachers.append(
            {
                "id": teacher.id,
                "name": teacher.name,
                "email": teacher.email,
                "school_name": teacher.school_name or "Not specified",
                "writings_count": teacher.writings_count,
                "classes_count": teacher.classes_count,
                "students_count": teacher.students_count,
                "last_activity": (
                    teacher.last_activity.strftime("%Y-%m-%d %H:%M")
                    if teacher.last_activity
                    else "N/A"
                ),
            }
        )
        teacher_names.append(teacher.name)
        teacher_writing_counts.append(teacher.writings_count)

    feedback_data = db.query(
        func.count(AnalysisFeedback.id).label("total_feedback"),
        func.sum(case((AnalysisFeedback.is_helpful == True, 1), else_=0)).label(
            "helpful_count"
        ),
        func.sum(
            case((AnalysisFeedback.writing_age_accurate == True, 1), else_=0)
        ).label("writing_age_accurate"),
        func.sum(case((AnalysisFeedback.strengths_accurate == True, 1), else_=0)).label(
            "strengths_accurate"
        ),
        func.sum(
            case((AnalysisFeedback.development_accurate == True, 1), else_=0)
        ).label("development_accurate"),
        func.sum(case((AnalysisFeedback.criteria_accurate == True, 1), else_=0)).label(
            "criteria_accurate"
        ),
    ).first()

    total_feedback = feedback_data.total_feedback if feedback_data else 0
    helpful_count = feedback_data.helpful_count if feedback_data else 0
    not_helpful_count = total_feedback - helpful_count if total_feedback else 0
    no_feedback_count = db.query(Writing).count() - total_feedback

    writing_age_accurate_count = (
        feedback_data.writing_age_accurate if feedback_data else 0
    )
    strengths_accurate_count = feedback_data.strengths_accurate if feedback_data else 0
    development_accurate_count = (
        feedback_data.development_accurate if feedback_data else 0
    )
    criteria_accurate_count = feedback_data.criteria_accurate if feedback_data else 0

    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    time_data = (
        db.query(
            func.date(Writing.created_at).label("date"),
            func.count(Writing.id).label("count"),
        )
        .filter(Writing.created_at >= start_date)
        .group_by(func.date(Writing.created_at))
        .order_by("date")
        .all()
    )

    date_labels = []
    date_dict = {}
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        date_dict[date_str] = 0
        date_labels.append(date_str)
        current_date += timedelta(days=1)

    for item in time_data:
        date_str = item.date.strftime("%Y-%m-%d")
        date_dict[date_str] = item.count

    submission_counts = [date_dict[date] for date in date_labels]

    metrics = {
        "total_users": db.query(User).count(),
        "total_classes": db.query(Class).count(),
        "total_students": db.query(Student).count(),
        "total_submissions": db.query(Writing).count(),
    }

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "metrics": metrics,
            "top_teachers": top_teachers,
            "teacher_names": teacher_names,
            "teacher_writing_counts": teacher_writing_counts,
            "total_feedback": total_feedback,
            "helpful_count": helpful_count,
            "not_helpful_count": not_helpful_count,
            "no_feedback_count": no_feedback_count,
            "writing_age_accurate_count": writing_age_accurate_count,
            "strengths_accurate_count": strengths_accurate_count,
            "development_accurate_count": development_accurate_count,
            "criteria_accurate_count": criteria_accurate_count,
            "date_labels": date_labels,
            "submission_counts": submission_counts,
        },
    )


# FastAPI version of /admin/export for exporting teacher data to Excel


@app.get("/admin/export")
def export_users(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Unauthorized access")

    try:
        teachers = db.query(User).filter_by(is_admin=False).all()
        users_data = [teacher.to_dict(db) for teacher in teachers]

        df = pd.DataFrame(users_data)

        columns = [
            "first_name",
            "last_name",
            "email",
            "school_name",
            "created_at",
            "last_login",
            "class_count",
            "student_count",
            "upload_count",
        ]
        df = df[columns]

        column_names = {
            "first_name": "First Name",
            "last_name": "Last Name",
            "email": "Email",
            "school_name": "School",
            "created_at": "Signup Date",
            "last_login": "Last Login",
            "class_count": "Number of Classes",
            "student_count": "Total Students",
            "upload_count": "Total Uploads",
        }
        df.rename(columns=column_names, inplace=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Teachers")
            worksheet = writer.sheets["Teachers"]
            for idx, col in enumerate(df.columns):
                max_len = max(df[col].astype(str).apply(len).max(), len(col)) + 2
                worksheet.column_dimensions[chr(65 + idx)].width = max_len

        output.seek(0)
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": "attachment;filename=teachers_report.xlsx"},
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


@app.post("/admin/delete-users")
def delete_users(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete multiple users and their associated data."""
    logger.info("Bulk delete users request received")
    logger.info(
        f"Current user: {current_user.email}, is_admin: {getattr(current_user, 'is_admin', False)}"
    )

    if current_user not in request.session:
        logger.warning("Unauthorized: User not authenticated")
        return JSONResponse(
            status_code=403, content={"error": "Unauthorized - not authenticated"}
        )

    if not current_user.is_admin:
        logger.warning(f"Unauthorized: User {current_user.email} is not an admin")
        return JSONResponse(
            status_code=403, content={"error": "Unauthorized - not admin"}
        )

    try:
        data = request.json()
        if not data or "user_ids" not in data:
            logger.warning("No user IDs provided in request")
            return JSONResponse(
                status_code=400, content={"error": "No user IDs provided"}
            )

        user_ids = data["user_ids"]
        if not isinstance(user_ids, list):
            logger.warning("Invalid user IDs format provided")
            return JSONResponse(
                status_code=400, content={"error": "Invalid user IDs format"}
            )

        # Don't allow admin to delete themselves
        if current_user.id in user_ids:
            logger.warning("Attempted to delete own admin account in bulk delete")
            return JSONResponse(
                status_code=400,
                content={"error": "Cannot delete your own admin account"},
            )

        # Delete users and their associated data
        deleted_count = 0
        for user_id in user_ids:
            user = db.query(User).get(user_id)
            if user:
                db.delete(user)
                deleted_count += 1

        db.commit()
        logger.info(f"Successfully deleted {deleted_count} users")
        return JSONResponse(
            status_code=200,
            content={"message": f"Successfully deleted {deleted_count} users"},
        )

    except Exception as e:
        logger.error(f"Error deleting users: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, content={"error": "Failed to delete users"}
        )


@app.get("/teacher_activity", response_class=HTMLResponse)
async def teacher_activity(db: Session = Depends(get_db)):
    teacher_data = (
        db.query(
            User.id,
            User.name,
            User.email,
            User.school_name,
            func.count(Writing.id).label("writings_count"),
            func.count(distinct(Class.id)).label("classes_count"),
            func.count(distinct(Student.id)).label("students_count"),
            func.max(Writing.created_at).label("last_activity"),
        )
        .join(Class, User.id == Class.teacher_id, isouter=True)
        .join(Student, Class.id == Student.class_id, isouter=True)
        .join(Writing, Student.id == Writing.student_id, isouter=True)
        .group_by(User.id)
        .order_by(desc("writings_count"))
        .limit(10)
        .all()
    )

    top_teachers = []
    for teacher in teacher_data:
        top_teachers.append(
            {
                "id": teacher.id,
                "name": teacher.name,
                "email": teacher.email,
                "school_name": teacher.school_name or "Not specified",
                "writings_count": teacher.writings_count,
                "classes_count": teacher.classes_count,
                "students_count": teacher.students_count,
                "last_activity": (
                    teacher.last_activity.strftime("%Y-%m-%d %H:%M")
                    if teacher.last_activity
                    else "N/A"
                ),
            }
        )

    return HTMLResponse(
        content=f"Top teachers: {top_teachers}", status_code=HTTP_200_OK
    )


@app.get("/feedback_metrics", response_class=HTMLResponse)
async def feedback_metrics(db: Session = Depends(get_db)):
    feedback_data = db.query(
        func.count(AnalysisFeedback.id).label("total_feedback"),
        func.sum(case((AnalysisFeedback.is_helpful == True, 1), else_=0)).label(
            "helpful_count"
        ),
        func.sum(
            case((AnalysisFeedback.writing_age_accurate == True, 1), else_=0)
        ).label("writing_age_accurate"),
        func.sum(case((AnalysisFeedback.strengths_accurate == True, 1), else_=0)).label(
            "strengths_accurate"
        ),
        func.sum(
            case((AnalysisFeedback.development_accurate == True, 1), else_=0)
        ).label("development_accurate"),
        func.sum(case((AnalysisFeedback.criteria_accurate == True, 1), else_=0)).label(
            "criteria_accurate"
        ),
    ).first()

    total_feedback = feedback_data.total_feedback if feedback_data else 0
    helpful_count = feedback_data.helpful_count if feedback_data else 0
    not_helpful_count = total_feedback - helpful_count if total_feedback else 0
    no_feedback_count = db.query(Writing).count() - total_feedback

    return HTMLResponse(
        content=f"Feedback metrics: {feedback_data}", status_code=HTTP_200_OK
    )


@app.get("/submissions_over_time", response_class=HTMLResponse)
async def submissions_over_time(db: Session = Depends(get_db)):
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    time_data = (
        db.query(
            func.date(Writing.created_at).label("date"),
            func.count(Writing.id).label("count"),
        )
        .filter(Writing.created_at >= start_date)
        .group_by(func.date(Writing.created_at))
        .order_by("date")
        .all()
    )

    date_labels = []
    submission_counts = []
    current_date = start_date
    date_dict = {}

    while current_date <= end_date:
        date_str = current_date.strftime("%Y-%m-%d")
        date_dict[date_str] = 0
        date_labels.append(date_str)
        current_date += timedelta(days=1)

    for item in time_data:
        date_str = item.date.strftime("%Y-%m-%d")
        date_dict[date_str] = item.count

    submission_counts = [date_dict[date] for date in date_labels]

    return HTMLResponse(
        content=f"Submission counts: {submission_counts}", status_code=HTTP_200_OK
    )


@app.get("/add-writing", response_class=HTMLResponse)
async def add_writing(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    mobile_camera: bool = Query(default=False),
):
    """
    Standard add writing page with optional camera view for mobile.
    """
    # Detect mobile from User-Agent
    user_agent = request.headers.get("user-agent", "").lower()
    is_mobile = any(
        keyword in user_agent for keyword in ["android", "iphone", "ipad", "mobile"]
    )

    # Fetch teacher's classes
    classes = db.query(Class).filter_by(teacher_id=current_user.id).all()

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "classes": classes,
            "is_mobile": is_mobile,
            "mobile_camera": mobile_camera,
        },
    )


@app.api_route(
    "/writing/{writing_id}/delete", methods=["GET", "POST"], response_class=HTMLResponse
)
async def delete_writing(
    writing_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Delete a writing sample. Supports both GET and POST methods.
    """
    try:
        # Fetch writing and related student
        writing = db.query(Writing).filter_by(id=writing_id).first()
        if not writing:
            raise HTTPException(status_code=404, detail="Writing not found")

        student = db.query(Student).filter_by(id=writing.student_id).first()
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Check teacher ownership
        if student.class_group.teacher_id != current_user.id:
            logger.warning(f"Unauthorized delete attempt by user {current_user.id}")
            if request.method == "POST":
                return JSONResponse(status_code=403, content={"error": "Unauthorized"})
            return RedirectResponse(url="/", status_code=302)

        student_id = student.id

        db.delete(writing)
        db.commit()
        logger.info(f"Writing sample {writing_id} deleted")

        # Handle AJAX/JSON POST
        if request.method == "POST":
            return JSONResponse(status_code=200, content={"success": True})

        # Handle browser redirect after GET
        response = RedirectResponse(
            url=f"/student/{student_id}/portfolio", status_code=302
        )
        request.session["flash"] = {
            "message": "Writing sample deleted successfully!",
            "category": "success",
        }
        return response

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting writing sample {writing_id}: {str(e)}")

        if request.method == "POST":
            return JSONResponse(
                status_code=500, content={"error": "Failed to delete writing sample"}
            )

        request.session["flash"] = {
            "message": "Failed to delete writing sample.",
            "category": "error",
        }
        return RedirectResponse(url=f"/student/{student_id}/portfolio", status_code=302)


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


@app.post("/process")
async def process_images_ocr(
    images: List[UploadFile] = File(...),
    student_id: str = Form(...),
    assignment_id: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if not images:
        raise HTTPException(status_code=400, detail="No files uploaded")

    student = db.query(Student).get(student_id)
    if not student or student.class_group.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Invalid student selected")

    assignment = None
    is_young_writer = False
    if assignment_id:
        assignment = db.query(Assignment).get(assignment_id)
        if assignment and assignment.class_group:
            year_group = assignment.class_group.year_group.lower()
            if any(y in year_group for y in ["1", "2", "3", "4", "reception", "ks1"]):
                is_young_writer = True

    def preprocess_image(image_bytes: bytes) -> bytes:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            if img.mode != "RGB":
                img = img.convert("RGB")
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = img.filter(ImageFilter.SHARPEN)
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=95)
            return output.getvalue()
        except Exception as e:
            logger.error(f"Preprocess error: {e}")
            raise HTTPException(status_code=500, detail="Failed to preprocess image")

    def process_single_image(file: UploadFile):
        if file.filename == "" or not allowed_file(file.filename):
            return None
        img_bytes = file.file.read()
        processed_img_bytes = preprocess_image(img_bytes)
        base64_image = encode_image_to_base64(processed_img_bytes)

        system_prompt = (
            "You are an expert at transcribing children's handwritten text..."
            if is_young_writer
            else "You are an expert at transcribing handwritten text..."
        )

        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Transcribe this handwritten text exactly as it appears.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            },
                        },
                    ],
                },
            ],
            max_tokens=1500,
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()

    # Process images concurrently
    with ThreadPoolExecutor(max_workers=min(len(images), 3)) as executor:
        futures = [executor.submit(process_single_image, file) for file in images]
        combined_text = [future.result() for future in futures if future.result()]

    if not combined_text:
        raise HTTPException(
            status_code=403, detail="No text could be extracted from the images"
        )

    final_text = "\n\nPage Break\n\n".join(combined_text)

    if assignment_id:
        assignment = db.query(Assignment).get(assignment_id)
        if assignment and assignment.class_id != student.class_id:
            raise HTTPException(status_code=403, detail="Invalid assignment selected")

    # Read the first image again for analysis
    first_image = images[0]
    first_image.file.seek(0)
    first_image_bytes = await first_image.read()
    first_image_base64 = encode_image_to_base64(first_image_bytes)

    analysis_response = analyze_writing(first_image_base64, assignment)
    age_estimate, feedback = "0 years 0 months", "Feedback unavailable"

    if analysis_response:
        age_estimate = analysis_response.get("age", age_estimate)
        feedback = analysis_response.get("feedback", feedback)
        feedback = feedback.replace("WRITING AGE:", "").strip()
        sections = feedback.split("\n\n")
        strengths = next((s for s in sections if "Strengths" in s), "")
        development = next((s for s in sections if "Areas for Development" in s), "")
        feedback = f"{strengths}\n\n{development}".strip()
        feedback = (
            feedback.replace("**Key", "")
            .replace("**", "")
            .replace("ize", "ise")
            .replace("yze", "yse")
        )

    writing_sample = Writing(
        filename=images[0].filename,
        text_content=final_text,
        writing_age=age_estimate,
        feedback=feedback,
        student_id=student_id,
        assignment_id=assignment_id if assignment_id else None,
    )
    db.add(writing_sample)
    db.commit()
    db.refresh(writing_sample)

    try:
        writing_count = db.query(Writing).filter_by(student_id=student_id).count()
        if writing_count == 0:
            tag_user_first_analysis(current_user.email)
    except Exception as e:
        logger.error(f"Mailchimp tagging failed: {str(e)}")

    criteria_marks = []

    if assignment:
        criteria_prompt = """You are an expert teacher evaluating a writing sample against specific success criteria.

        For each criterion, you must evaluate CONSISTENTLY using these specific scoring guidelines
        Score 0 = Not met:
        - The required skill/element is completely absent
        - No evidence of attempting the criterion
        - Significant errors that impede understandin
        Score 1 = Partially met:
        - The skill/element is present but inconsistent
        - Basic or limited demonstration of the criterion
        - Some errors but meaning is generally clea
        Score 2 = Confidently used:
        - Consistent and effective use throughout
        - Clear evidence of mastery of the criterion
        - Minimal errors that don't impact understandin
        IMPORTANT SCORING RULES:
        1. Be consistent - similar writing should receive similar scores
        2. Focus on evidence - cite specific examples from the text
        3. Consider age-appropriate expectations
        4. Score each criterion independently
        5. Avoid being influenced by overall impression

        Criteria to evaluate:
        """
        for criterion in assignment.criteria:
            criteria_prompt += f"- {criterion.description}\n"

        criteria_prompt += """
        Analyze the text thoroughly and respond with a JSON object in this exact format:
        {
            "evaluations": [
                {
                    "criterion": "exact criterion text",
                    "score": number (0, 1, or 2),
                    "justification": "MUST include specific examples from the text that justify this score"
                }
            ]
        }

        For each criterion, your justification MUST:
        1. Quote specific examples from the text
        2. Explain why these examples merit the given score
        3. Reference the scoring guidelines above"""

        try:
            criteria_response = client.chat.completions.create(
                model=os.getenv("MODEL_NAME"),
                max_tokens=1500,
                temperature=0.2,
                messages=[
                    {"role": "system", "content": criteria_prompt},
                    {
                        "role": "user",
                        "content": f"Evaluate this writing:\n\n{final_text}",
                    },
                ],
            )

            response_data = json.loads(criteria_response.choices[0].message.content)
            evaluations = response_data.get("evaluations", [])
            db.query(CriteriaMark).filter_by(writing_id=writing_sample.id).delete()
            for criterion, evaluation in zip(assignment.criteria, evaluations):
                score = min(2, max(0, int(evaluation.get("score", 0))))
                mark = CriteriaMark(
                    writing_id=writing_sample.id, criteria_id=criterion.id, score=score
                )
                db.add(mark)
                criteria_marks.append(
                    {
                        "criteria": criterion.description,
                        "score": score,
                        "justification": evaluation.get("justification", ""),
                    }
                )

            total_marks = len(criteria_marks)
            if total_marks:
                total_score = sum(mark["score"] for mark in criteria_marks)
                writing_sample.total_marks_percentage = (
                    total_score / (total_marks * 2)
                ) * 100

            db.commit()

        except Exception as e:
            logger.error(f"Error scoring criteria: {str(e)}")
            db.rollback()

    return JSONResponse(
        content={
            "text": final_text,
            "writing_age": age_estimate,
            "feedback": feedback,
            "writing_id": writing_sample.id,
            "criteria_marks": criteria_marks,
        }
    )


# schemas.py
from pydantic import BaseModel
from typing import Optional


class FeedbackSubmission(BaseModel):
    writing_id: int
    is_helpful: bool
    writing_age_accurate: Optional[bool]
    strengths_accurate: Optional[bool]
    development_accurate: Optional[bool]
    criteria_accurate: Optional[bool]
    comment: Optional[str]


@app.post("/submit_feedback", response_class=JSONResponse)
async def submit_feedback(
    feedback_data: FeedbackSubmission,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Submit teacher feedback on writing analysis.
    """
    try:
        logger.debug("Received feedback submission")

        writing = db.query(Writing).get(feedback_data.writing_id)
        if not writing:
            logger.error("Writing ID not found")
            raise HTTPException(status_code=404, detail="Writing not found")

        student = db.query(Student).get(writing.student_id)
        if not student or student.class_group.teacher_id != current_user.id:
            logger.warning(
                f"Unauthorized feedback attempt for writing {feedback_data.writing_id}"
            )
            raise HTTPException(status_code=403, detail="Unauthorized")

        feedback = AnalysisFeedback(
            writing_id=feedback_data.writing_id,
            is_helpful=feedback_data.is_helpful,
            writing_age_accurate=feedback_data.writing_age_accurate,
            strengths_accurate=feedback_data.strengths_accurate,
            development_accurate=feedback_data.development_accurate,
            criteria_accurate=feedback_data.criteria_accurate,
            comment=feedback_data.comment,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        logger.info(
            f"Successfully saved feedback for writing {feedback_data.writing_id}"
        )
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Feedback submitted successfully",
                "feedback_id": feedback.id,
            },
        )

    except Exception as e:
        logger.error(f"Error submitting feedback: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to submit feedback")


# FastAPI version of /assignment/{assignment_id}/class-feedback


@app.post("/update_criteria_marks")
async def update_criteria_marks(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        logger.debug("Received criteria marks update")
        data = await request.json()
        writing_id = data.get("writing_id")
        updated_marks = data.get("updated_marks")

        if not writing_id or not updated_marks:
            logger.error("Writing ID or updated marks missing from request")
            return (
                JSONResponse(
                    status_code=400,
                    content={"error": "Writing ID and updated marks are required"},
                ),
            )

        from models import Writing, CriteriaMark, Student

        writing = db.query(Writing).get(writing_id)
        student = db.query(Student).get(writing.student_id)

        # Verify permission (teacher of the student's class)
        if student.class_group.teacher_id != current_user.id:
            logger.warning(
                f"Unauthorized marks update attempt for writing {writing_id}"
            )
            return JSONResponse(status_code=403, content={"error": "Unauthorized"})

        # Get existing criteria marks
        criteria_marks = db.query(CriteriaMark).filter_by(writing_id=writing_id).all()

        if len(criteria_marks) != len(updated_marks):
            logger.error(
                f"Mismatch in criteria marks count: DB={len(criteria_marks)}, Request={len(updated_marks)}"
            )
            return JSONResponse(
                status_code=400, content={"error": "Criteria marks count mismatch"}
            )

        # Update marks in database
        for update in updated_marks:
            index = update.get("criteria_index")
            new_score = update.get("score")

            if index < len(criteria_marks) and 0 <= new_score <= 2:
                criteria_marks[index].score = new_score
            else:
                logger.warning(
                    f"Invalid index orscore: index={index}, score={new_score}"
                )

        # Calculate and store total marks percentage
        total_marks = len(criteria_marks)
        if total_marks > 0:
            total_score = sum(mark.score for mark in criteria_marks)
            # Max score per criterion is 2, so maximum possible score is total_marks * 2
            percentage = (total_score / (total_marks * 2)) * 100
            writing.total_marks_percentage = percentage
            logger.info(f"Calculated total marks percentage: {percentage}%")

        db.commit()
        logger.info(f"Successfully updated criteria marks for writing {writing_id}")

        return JSONResponse(
            status_code=200,
            content={"success": True, "message": "Criteria marks updated successfully"},
        )

    except Exception as e:
        logger.error(f"Error updating criteria marks:{str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to update criteria marks: {str(e)}"},
        )


@app.get("/assignment/{assignment_id}/wagoll")
async def get_wagoll(
    assignment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a 'What A Good One Looks Like' (WAGOLL) example for the assignment."""
    from models import Assignment, Writing, CriteriaMark, Criteria

    # Get the assignment and verify ownership
    assignment = db.query(Assignment).get(assignment_id)
    if assignment.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        # Collect all criteria for this assignment
        criteria_list = db.query(Criteria).filter_by(assignment_id=assignment_id).all()

        if not criteria_list:
            return JSONResponse(
                content={
                    "title": assignment.title,
                    "exemplar": "No success criteria found for this assignment.",
                    "explanations": [
                        "Please add success criteria to generate a WAGOLL example."
                    ],
                }
            )

        # Get top-scoring submissions
        submissions = db.query(Writing).filter_by(assignment_id=assignment_id).all()

        # Find the best examples for each criterion
        best_examples = {}
        for criterion in criteria_list:
            best_score = -1
            best_example = None

            for submission in submissions:
                for mark in submission.criteria_marks:
                    if mark.criteria_id == criterion.id and mark.score > best_score:
                        best_score = mark.score
                        best_example = submission.text_content

            if best_example:
                best_examples[criterion.description] = {
                    "score": best_score,
                    "example": best_example,
                }

        # Create the prompt for generating the WAGOLL
        wagoll_prompt = f"""You are an expert educational writer who specializes in creating exemplary writing samples that demonstrate mastery of learning objectives.

        Task: Create a "What A Good One Looks Like" (WAGOLL) example for a {assignment.curriculum} curriculum {assignment.genre} writing assignment titled "{assignment.title}".

        This WAGOLL should:
        1. Exemplify mastery of all the success criteria
        2. Be age-appropriate (targeting {assignment.class_group.year_group} students)
        3. Showcase excellent writing techniques appropriate for this genre
        4. Be original but inspired by the best elements from student submissions

        Success Criteria:
        {chr(10).join([f"- {c.description}" for c in criteria_list])}

        Format your response as a JSON object with these keys:
        {{
            "exemplar": "The complete example text",
            "explanations": [
                "3-5 specific points explaining why this is a good example",
                "Including how it meets each success criterion"
            ]
        }}

        Keep the exemplar text appropriate in length for {assignment.class_group.year_group} students (typically 250-500 words). Focus on quality over quantity."""

        # Get AI to generate the WAGOLL
        response = client.chat.completions.create(
            model=os.getenv("MODEL_NAME"),
            messages=[
                {"role": "system", "content": wagoll_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "assignment": {
                                "title": assignment.title,
                                "genre": assignment.genre,
                                "curriculum": assignment.curriculum,
                                "year_group": assignment.class_group.year_group,
                            },
                            "criteria": [c.description for c in criteria_list],
                            "best_examples": best_examples,
                        }
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        # Parse the response
        wagoll = json.loads(response.choices[0].message.content)

        # Return the WAGOLL with explanations
        return JSONResponse(
            content={
                "title": assignment.title,
                "exemplar": wagoll.get("exemplar", "Error generating example."),
                "explanations": wagoll.get(
                    "explanations", ["No explanations provided."]
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error generating WAGOLL: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "title": assignment.title if assignment else "Unknown Assignment",
                "exemplar": "Error generating the WAGOLL example.",
                "explanations": [f"Error: {str(e)}"],
            },
        )


@app.get("/assignment/{assignment_id}/wagoll_examples")
def get_wagoll_examples(
    assignment_id,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get saved WAGOLL examples for an assignment."""
    from models import Assignment, WagollExample

    # Get the assignment and verify ownership
    assignment = db.query(Assignment).get(assignment_id)
    if assignment.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        # Get examples created by this teacher for this assignment
        examples = (
            db.query(WagollExample)
            .filter_by(assignment_id=assignment_id, teacher_id=current_user.id)
            .order_by(WagollExample.updated_at.desc())
            .all()
        )

        # Format response
        response = {
            "examples": [
                {
                    "id": example.id,
                    "title": example.title,
                    "updated_at": example.updated_at.isoformat(),
                    "is_public": example.is_public,
                }
                for example in examples
            ]
        }

        return JSONResponse(response)

    except Exception as e:
        logger.error(f"Error getting WAGOLL examples: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/wagoll_example/{example_id}")
def get_wagoll_example(
    example_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific WAGOLL example."""
    from models import WagollExample

    example = db.query(WagollExample).get(example_id)
    if example is None:
        return JSONResponse(status_code=404, content={"error": "Example not found"})

    if example.teacher_id != current_user.id and not example.is_public:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        response = {
            "id": example.id,
            "title": example.title,
            "content": example.content,
            "explanations": example.explanations,
            "is_public": example.is_public,
            "assignment_id": example.assignment_id,
            "assignment_title": (
                example.assignment.title if example.assignment else None
            ),
            "created_at": (
                example.created_at.isoformat() if example.created_at else None
            ),
            "updated_at": (
                example.updated_at.isoformat() if example.updated_at else None
            ),
        }

        return JSONResponse(content=response)

    except Exception as e:
        logger.error(f"Error getting WAGOLL example: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/assignment/{assignment_id}/class-feedback")
def get_class_feedback(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = db.query(Assignment).get(assignment_id)
    if not assignment or assignment.class_group.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        submissions = db.query(Writing).filter_by(assignment_id=assignment_id).all()

        if not submissions:
            return JSONResponse(
                content={
                    "strengths": ["No submissions to analyze"],
                    "areas_for_development": ["No submissions to analyze"],
                    "practice_activities": ["No submissions to analyze"],
                }
            )

        max_submissions = min(len(submissions), 10)
        submissions = submissions[:max_submissions]

        criteria_scores = {}
        common_strengths = []
        common_weaknesses = []
        avg_writing_age = 0
        writing_age_count = 0

        for submission in submissions:
            if submission.writing_age:
                try:
                    years = float(submission.writing_age.split(" years")[0])
                    avg_writing_age += years
                    writing_age_count += 1
                except (ValueError, IndexError):
                    continue

            if submission.feedback:
                parts = submission.feedback.split("\n\n")
                if len(parts) >= 1:
                    for line in parts[0].replace("Strengths:", "").split("\n"):
                        if line.strip().startswith("- "):
                            common_strengths.append(line.strip()[2:])
                if len(parts) >= 2:
                    for line in (
                        parts[1].replace("Areas for Development:", "").split("\n")
                    ):
                        if line.strip().startswith("- "):
                            common_weaknesses.append(line.strip()[2:])

            for mark in submission.criteria_marks:
                key = mark.criteria.description
                if key not in criteria_scores:
                    criteria_scores[key] = {"total": mark.score, "count": 1}
                else:
                    criteria_scores[key]["total"] += mark.score
                    criteria_scores[key]["count"] += 1

        if writing_age_count:
            avg_writing_age /= writing_age_count

        avg_criteria = [
            {"criterion": k, "avg_score": v["total"] / v["count"]}
            for k, v in criteria_scores.items()
        ]
        avg_criteria.sort(key=lambda x: x["avg_score"])

        analysis_prompt = f"""Analyze this class's writing submissions for a specific assignment and provide exactly:

        1. Three clear class strengths
        2. Three specific areas for development
        3. Four practical practice activities

        Format your response as a JSON object with exactly these keys:
        {{
            "strengths": [3 strength items],
            "areas_for_development": [3 development items],
            "practice_activities": [4 activity items]
        }}

        Assignment Details:
        Title: {assignment.title}
        Genre: {assignment.genre}
        Curriculum: {assignment.curriculum}
        Number of Submissions Analyzed: {max_submissions} (out of {len(submissions)})
        Average Writing Age: {avg_writing_age:.1f} years"""

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL_NAME = "gpt-4o"

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": analysis_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "highest_scoring_criteria": [
                                c for c in avg_criteria[-3:] if c["avg_score"] > 1
                            ],
                            "lowest_scoring_criteria": [
                                c for c in avg_criteria[:3] if c["avg_score"] < 1
                            ],
                            "common_strengths": common_strengths[:10],
                            "common_weaknesses": common_weaknesses[:10],
                            "avg_writing_age": avg_writing_age,
                        }
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        analysis = json.loads(response.choices[0].message.content)
        return JSONResponse(
            content={
                "strengths": analysis.get("strengths", ["No strengths identified"]),
                "areas_for_development": analysis.get(
                    "areas_for_development", ["No areas identified"]
                ),
                "practice_activities": analysis.get(
                    "practice_activities", ["No activities suggested"]
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error generating class feedback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "strengths": ["Error analyzing submissions"],
                "areas_fordevelopment": ["Error analyzing submissions"],
                "practice_activities": ["Error analyzing submissions"],
            },
        )


@app.get("/data_analysis", response_class=HTMLResponse)
async def data_analysis(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_classes = db.query(Class).filter_by(teacher_id=current_user.id).all()
    now = datetime.now()

    return templates.TemplateResponse(
        "data_analysis.html", {"request": request, "classes": user_classes, "now": now}
    )


@app.get("/api/students")
async def get_api_students(
    class_id: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if class_id == "all":
        students = (
            db.query(Student)
            .join(Class)
            .filter(Class.teacher_id == current_user.id)
            .order_by(Student.first_name, Student.last_name)
            .all()
        )
    else:
        students = (
            db.query(Student)
            .join(Class)
            .filter(Class.id == class_id, Class.teacher_id == current_user.id)
            .order_by(Student.first_name, Student.last_name)
            .all()
        )

    return JSONResponse(
        {
            "students": [
                {
                    "id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "class_id": student.class_id,
                }
                for student in students
            ]
        }
    )


@app.get("/api/student_data")
async def get_api_student_data(
    ids: Optional[str] = Query(default=""),
    class_id: Optional[str] = Query(default="all"),
    time_period: Optional[str] = Query(default="all"),
    chart_type: Optional[str] = Query(default="writing_scores"),
    include_average: Optional[bool] = Query(default=False),
    average_type: Optional[str] = Query(default="all"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student_id_list = [int(sid) for sid in ids.split(",") if sid.isdigit()]
    time_filter = None

    if time_period != "all":
        now = datetime.now()
        days_map = {"month": 30, "quarter": 90, "year": 365}
        if time_period in days_map:
            time_filter = now - timedelta(days=days_map[time_period])

    datasets = []
    all_dates = set()

    for student_id in student_id_list:
        student = (
            db.query(Student)
            .join(Class)
            .filter(Student.id == student_id, Class.teacher_id == current_user.id)
            .first()
        )
        if not student:
            continue

        query = db.query(Writing).filter(Writing.student_id == student_id)
        if time_filter:
            query = query.filter(Writing.created_at >= time_filter)
        samples = query.order_by(Writing.created_at).all()

        data_points = []
        for sample in samples:
            value = None
            if chart_type == "writing_scores" and sample.criteria_marks:
                total = len(sample.criteria_marks)
                met = sum(1 for m in sample.criteria_marks if m.score == 2)
                partial = sum(1 for m in sample.criteria_marks if m.score == 1)
                value = (met / total) * 100 + (partial / total) * 50
            elif chart_type == "writing_age" and sample.writing_age:
                try:
                    value = float(sample.writing_age.split()[0])
                except:
                    continue
            elif chart_type == "age_difference" and sample.writing_age:
                try:
                    writing_age = float(sample.writing_age.split()[0])
                    actual_age = (
                        sample.created_at.date() - student.date_of_birth
                    ).days / 365.25
                    value = writing_age - actual_age
                except:
                    continue
            else:
                continue

            date_str = f"{sample.created_at.strftime('%Y-%m-%d')} ({sample.id})"
            date_display = sample.created_at.strftime("%d %b %Y")
            all_dates.add(date_str)
            data_points.append(
                {
                    "date": date_str,
                    "date_display": date_display,
                    "value": value,
                    "writing_id": sample.id,
                }
            )

        if data_points:
            sorted_points = sorted(data_points, key=lambda x: x["date"])
            datasets.append(
                {
                    "student_id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "data": [p["value"] for p in sorted_points],
                    "dates": [p["date"] for p in sorted_points],
                    "is_average": False,
                }
            )

    # Average dataset for class
    if include_average and class_id != "all" and class_id.isdigit():
        class_obj = (
            db.query(Class)
            .filter_by(id=int(class_id), teacher_id=current_user.id)
            .first()
        )
        if class_obj:
            student_ids = [
                s.id for s in db.query(Student).filter_by(class_id=class_obj.id).all()
            ]
            all_dates_list = sorted(all_dates)
            avg_data = []

            for date_str in all_dates_list:
                if " (" in date_str:
                    date_part = date_str.split(" (")[0]
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d").date()
                    next_day = date_obj + timedelta(days=1)
                    writings = (
                        db.query(Writing)
                        .filter(
                            Writing.student_id.in_(student_ids),
                            Writing.created_at >= date_obj,
                            Writing.created_at < next_day,
                        )
                        .all()
                    )

                    values = []
                    for w in writings:
                        if chart_type == "writing_scores" and w.criteria_marks:
                            total = len(w.criteria_marks)
                            achieved = sum(m.score for m in w.criteria_marks)
                            if total:
                                values.append((achieved / (total * 2)) * 100)
                        elif chart_type == "writing_age" and w.writing_age:
                            try:
                                values.append(float(w.writing_age.split()[0]))
                            except:
                                pass
                        elif chart_type == "age_difference" and w.writing_age:
                            try:
                                writing_age = float(w.writing_age.split()[0])
                                actual_age = (
                                    w.created_at.date() - student.date_of_birth
                                ).days / 365.25
                                values.append(writing_age - actual_age)
                            except:
                                pass
                    avg_data.append(sum(values) / len(values) if values else None)

            if any(avg_data):
                datasets.append(
                    {
                        "student_id": "average",
                        "name": f"{class_obj.name} Class Average",
                        "data": avg_data,
                        "dates": all_dates_list,
                        "is_average": True,
                    }
                )

    # Format date display map
    date_display_map = {}
    for ds in datasets:
        for date_key in ds.get("dates", []):
            if " (" in date_key:
                date_part = date_key.split(" (")[0]
                try:
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                    display = date_obj.strftime("%d %b %Y")
                    date_display_map[date_key] = display
                except:
                    date_display_map[date_key] = date_key

    insights = {}
    if datasets:
        insights = {
            "key_observations": [
                "Select multiple students to compare their progress over time.",
                "Use the chart filters to explore different metrics and time periods.",
            ],
            "recommendations": "Focus on students showing significant differences from the class average.",
        }

    return JSONResponse(
        {
            "labels": sorted(all_dates),
            "date_displays": date_display_map,
            "datasets": datasets,
            "insights": insights,
        }
    )


@app.get("/student/{student_id}/portfolio", name="student_portfolio")
async def student_portfolio(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        student = db.query(Student).filter(Student.id == student_id).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Permission check
        if student.class_group.teacher_id != current_user.id:
            request.session["flash"] = {
                "message": "You do not have permission to view this portfolio.",
                "category": "danger",
            }
            return RedirectResponse(url="/", status_code=303)

        from sqlalchemy.orm import joinedload

        writing_samples = (
            db.query(Writing)
            .options(joinedload(Writing.criteria_marks), joinedload(Writing.assignment))
            .filter(Writing.student_id == student_id)
            .order_by(Writing.created_at.desc())
            .all()
        )

        assignments = (
            db.query(Assignment).filter(Assignment.class_id == student.class_id).all()
        )

        # Average criteria met
        total_criteria_scores = 0
        total_criteria_count = 0
        for sample in writing_samples:
            if sample.criteria_marks:
                total_criteria_count += len(sample.criteria_marks)
                total_criteria_scores += sum(
                    mark.score for mark in sample.criteria_marks
                )

        average_criteria_met = (
            (total_criteria_scores / (total_criteria_count * 2)) * 100
            if total_criteria_count > 0
            else None
        )

        # Progress rating calculation
        age_differences = []
        for sample in writing_samples:
            if sample.writing_age:
                try:
                    writing_age_value = float(sample.writing_age.split()[0])
                    today = datetime.now().date()
                    birth_date = student.date_of_birth
                    student_age = (today - birth_date).days / 365.25
                    age_diff = round(writing_age_value - student_age, 1)

                    age_differences.append(
                        {
                            "sample_id": sample.id,
                            "date": sample.created_at,
                            "filename": sample.filename,
                            "writing_age": writing_age_value,
                            "student_age": student_age,
                            "difference": age_diff,
                            "assignment": (
                                sample.assignment.title
                                if sample.assignment
                                else "No Assignment"
                            ),
                        }
                    )
                except (ValueError, AttributeError, IndexError):
                    continue

        progress_rating = None
        if age_differences:
            age_differences.sort(key=lambda x: x["date"], reverse=True)
            latest = age_differences[: min(3, len(age_differences))]
            avg_diff = sum(item["difference"] for item in latest) / len(latest)
            if avg_diff >= 3:
                progress_rating = "Excellent"
            elif avg_diff >= 2:
                progress_rating = "Very Good"
            elif avg_diff >= 1:
                progress_rating = "Good"
            elif avg_diff >= 0:
                progress_rating = "Satisfactory"
            else:
                progress_rating = "Needs Support"

        # Chart data prep
        chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "Assignment Score",
                    "data": [],
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "pointBackgroundColor": "rgba(75, 192, 192, 1)",
                    "fill": True,
                }
            ],
        }

        age_chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "Writing Age",
                    "data": [],
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "fill": False,
                },
                {
                    "label": "Actual Age",
                    "data": [],
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "fill": False,
                },
            ],
        }

        for sample in reversed(writing_samples):
            chart_data["labels"].append(sample.created_at.strftime("%d %b %Y"))
            if sample.criteria_marks:
                total_marks = len(sample.criteria_marks)
                score = sum(mark.score for mark in sample.criteria_marks)
                chart_data["datasets"][0]["data"].append(
                    (score / (total_marks * 2)) * 100
                )
            else:
                chart_data["datasets"][0]["data"].append(0)

            if sample.writing_age:
                try:
                    writing_age_val = float(sample.writing_age.split()[0])
                    today = datetime.now().date()
                    birth_date = student.date_of_birth
                    student_age = (today - birth_date).days / 365.25
                    age_chart_data["labels"].append(
                        sample.created_at.strftime("%d %b %Y")
                    )
                    age_chart_data["datasets"][0]["data"].append(writing_age_val)
                    age_chart_data["datasets"][1]["data"].append(student_age)
                except Exception:
                    continue

        # Prev/next student navigation
        class_students = (
            db.query(Student)
            .filter(Student.class_id == student.class_id)
            .order_by(Student.first_name)
            .all()
        )
        current_index = next(
            (i for i, s in enumerate(class_students) if s.id == student.id), None
        )

        prev_student = (
            class_students[current_index - 1]
            if current_index and current_index > 0
            else class_students[-1]
        )
        next_student = (
            class_students[(current_index + 1) % len(class_students)]
            if current_index is not None
            else None
        )

        return templates.TemplateResponse(
            "student_portfolio_new_temp.html",
            context={
                "request": request,
                "student": student,
                "writing_samples": writing_samples,
                "assignments": assignments,
                "average_criteria_met": average_criteria_met,
                "progress_rating": progress_rating,
                "prev_student": prev_student,
                "next_student": next_student,
                "chart_data": json.dumps(chart_data),
                "age_chart_data": json.dumps(age_chart_data),
                "age_differences": age_differences,
            },
        )
    except Exception as e:
        print(f"error fetching student{e}")


@app.get("/student/{student_id}/export_portfolio", name="export_student_portfolio")
async def export_student_portfolio(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export a student's portfolio as a CSV file.
    Only the student's class teacher is authorized to perform this export.
    """
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.class_group.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(
            [
                "Date",
                "Assignment",
                "Writing Age",
                "Score",
                "Max Score",
                "Achievement %",
                "Strengths",
                "Areas for Development",
            ]
        )

        samples = (
            db.query(Writing)
            .filter_by(student_id=student_id)
            .order_by(Writing.created_at.desc())
            .all()
        )

        for sample in samples:
            max_score = len(sample.criteria_marks) * 2 if sample.assignment_id else 0
            achieved_score = (
                sum(mark.score for mark in sample.criteria_marks)
                if sample.assignment_id
                else 0
            )
            percent = (
                round((achieved_score / max_score * 100), 1) if max_score > 0 else "N/A"
            )

            feedback_parts = (
                sample.feedback.split("\n\n") if sample.feedback else ["", ""]
            )
            strengths = (
                feedback_parts[0].replace("Strengths:", "").strip()
                if len(feedback_parts) > 0
                else ""
            )
            development = (
                feedback_parts[1].replace("Areas for Development:", "").strip()
                if len(feedback_parts) > 1
                else ""
            )

            writer.writerow(
                [
                    sample.created_at.strftime("%Y-%m-%d"),
                    sample.assignment.title if sample.assignment else "Free Writing",
                    sample.writing_age,
                    achieved_score if max_score > 0 else "N/A",
                    max_score if max_score > 0 else "N/A",
                    f"{percent}%" if isinstance(percent, (int, float)) else percent,
                    strengths,
                    development,
                ]
            )

        output.seek(0)

        filename = f"{student.first_name}_{student.last_name}_portfolio_{datetime.now().strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Error exporting portfolio for student {student_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export portfolio")


@app.post("/writing/{writing_id}/update_filename")
async def update_writing_filename(
    writing_id: int,
    request: Request,
    filename: Optional[str] = Form(None),  # fallback for form submission
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update the filename of a writing sample.
    Accepts both JSON and form data.
    """
    try:
        # Prioritize JSON input
        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
            new_filename = data.get("filename")
        else:
            new_filename = filename

        if not new_filename:
            if request.headers.get("accept", "").startswith("application/json"):
                raise HTTPException(status_code=400, detail="Filename is required")
            return RedirectResponse(
                url=str(request.headers.get("referer", "/")), status_code=303
            )

        writing = db.query(Writing).get(writing_id)
        if not writing:
            raise HTTPException(status_code=404, detail="Writing not found")

        student = db.query(Student).get(writing.student_id)
        if not student or student.class_group.teacher_id != current_user["id"]:
            if request.headers.get("accept", "").startswith("application/json"):
                raise HTTPException(status_code=403, detail="Unauthorized")
            return RedirectResponse(url="/", status_code=303)

        writing.filename = new_filename
        db.commit()

        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(
                content={"success": True, "filename": new_filename}, status_code=200
            )
        return RedirectResponse(
            url=str(request.headers.get("referer", "/")), status_code=303
        )

    except Exception as e:
        logger.error(f"Error updating writing filename: {str(e)}")
        db.rollback()

        if request.headers.get("accept", "").startswith("application/json"):
            raise HTTPException(status_code=500, detail="Failed to update filename")
        return RedirectResponse(url="/", status_code=303)


logger = logging.getLogger(__name__)


class BulkDeleteRequest(BaseModel):
    writing_ids: List[int]


@app.post("/writing/bulk_delete")
async def bulk_delete_writing(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    writing_ids: Optional[Union[List[int], None]] = Form(None),
):
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
            writing_ids = body.get("writing_ids", [])
        else:
            form = await request.form()
            writing_ids = form.getlist("writing_ids")

        if not writing_ids:
            return JSONResponse(
                {"error": "No writing samples selected"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch writings
        writings = db.query(Writing).filter(Writing.id.in_(writing_ids)).all()

        if not writings:
            return JSONResponse(
                {"error": "No matching writing samples found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        student_id = writings[0].student_id if writings else None

        for writing in writings:
            student = db.query(Student).filter_by(id=writing.student_id).first()
            if not student or student.class_group.teacher_id != current_user.id:
                return JSONResponse(
                    {"error": "Unauthorized access to one or more writing samples"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            db.delete(writing)

        db.commit()

        # Respond appropriately based on content type
        if request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"success": True}, status_code=status.HTTP_200_OK)
        else:
            redirect_url = f"/student/{student_id}/portfolio" if student_id else "/"
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

    except Exception as e:
        logger.error(f"Error bulk deleting writing samples: {str(e)}")
        db.rollback()
        if request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse(
                {"error": "Failed to delete writing samples"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/writing/{writing_id}/print_report", response_class=HTMLResponse)
async def print_writing_report(
    writing_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Render a printable report of a student's writing sample.
    """
    # Fetch writing
    writing = db.query(Writing).filter_by(id=writing_id).first()
    if not writing:
        raise HTTPException(status_code=404, detail="Writing not found")

    # Fetch student
    student = db.query(Student).filter_by(id=writing.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Authorization check
    if student.class_group.teacher_id != current_user.id:
        return RedirectResponse(url="/", status_code=302)

    # Score calculations
    total_possible_marks = len(writing.criteria_marks) * 2 if writing.assignment else 0
    achieved_marks = (
        sum(mark.score for mark in writing.criteria_marks) if writing.assignment else 0
    )
    percentage = (
        round((achieved_marks / total_possible_marks * 100), 1)
        if total_possible_marks > 0
        else 0
    )

    # Feedback parsing
    feedback_parts = writing.feedback.split("\n\n") if writing.feedback else ["", ""]
    strengths = (
        feedback_parts[0].replace("Strengths:", "").strip() if feedback_parts else ""
    )
    development = (
        feedback_parts[1].replace("Areas for Development:", "").strip()
        if len(feedback_parts) > 1
        else ""
    )

    # Age calculations
    student_age = (writing.created_at.date() - student.date_of_birth).days / 365.25
    student_age_str = f"{int(student_age)} years {int((student_age % 1) * 12)} months"
    writing_age_str = (
        writing.writing_age.replace("Estimated writing age:", "").strip()
        if writing.writing_age
        else "N/A"
    )

    return templates.TemplateResponse(
        "print_report.html",
        {
            "request": request,
            "writing": writing,
            "student": student,
            "total_marks": total_possible_marks,
            "achieved_marks": achieved_marks,
            "percentage": percentage,
            "strengths": strengths,
            "development": development,
            "student_age": student_age_str,
            "writing_age": writing_age_str,
        },
    )


@app.post("/student/{student_id}/delete")
def delete_student(
    request: Request,
    student_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from models import Student

    student = db.query(Student).get(student_id)

    # Check if current user is the teacher of this student's class
    if student.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, detail={"error": "Unauthorized"})

    try:
        db.delete(student)
        db.commit()
        request.session["flash"] = {"message": "Class ID is required", "type": "error"}
        return JSONResponse(status_code=200, detail={"sucess": True})
    except Exception as e:
        logger.error(f"Error deleting student: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, detail={"error": "Failed to delete student"}
        )


@app.get("/assignment/{assignment_id}/class-feedback")
def get_class_feedback(
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = db.query(Assignment).get(assignment_id)
    if not assignment or assignment.class_group.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Unauthorized")

    try:
        submissions = db.query(Writing).filter_by(assignment_id=assignment_id).all()

        if not submissions:
            return JSONResponse(
                content={
                    "strengths": ["No submissions to analyze"],
                    "areas_for_development": ["No submissions to analyze"],
                    "practice_activities": ["No submissions to analyze"],
                }
            )

        max_submissions = min(len(submissions), 10)
        submissions = submissions[:max_submissions]

        criteria_scores = {}
        common_strengths = []
        common_weaknesses = []
        avg_writing_age = 0
        writing_age_count = 0

        for submission in submissions:
            if submission.writing_age:
                try:
                    years = float(submission.writing_age.split(" years")[0])
                    avg_writing_age += years
                    writing_age_count += 1
                except (ValueError, IndexError):
                    continue

            if submission.feedback:
                parts = submission.feedback.split("\n\n")
                if len(parts) >= 1:
                    for line in parts[0].replace("Strengths:", "").split("\n"):
                        if line.strip().startswith("- "):
                            common_strengths.append(line.strip()[2:])
                if len(parts) >= 2:
                    for line in (
                        parts[1].replace("Areas for Development:", "").split("\n")
                    ):
                        if line.strip().startswith("- "):
                            common_weaknesses.append(line.strip()[2:])

            for mark in submission.criteria_marks:
                key = mark.criteria.description
                if key not in criteria_scores:
                    criteria_scores[key] = {"total": mark.score, "count": 1}
                else:
                    criteria_scores[key]["total"] += mark.score
                    criteria_scores[key]["count"] += 1

        if writing_age_count:
            avg_writing_age /= writing_age_count

        avg_criteria = [
            {"criterion": k, "avg_score": v["total"] / v["count"]}
            for k, v in criteria_scores.items()
        ]
        avg_criteria.sort(key=lambda x: x["avg_score"])

        analysis_prompt = f"""Analyze this class's writing submissions for a specific assignment and provide exactly:

        1. Three clear class strengths
        2. Three specific areas for development
        3. Four practical practice activities

        Format your response as a JSON object with exactly these keys:
        {{
            "strengths": [3 strength items],
            "areas_for_development": [3 development items],
            "practice_activities": [4 activity items]
        }}

        Assignment Details:
        Title: {assignment.title}
        Genre: {assignment.genre}
        Curriculum: {assignment.curriculum}
        Number of Submissions Analyzed: {max_submissions} (out of {len(submissions)})
        Average Writing Age: {avg_writing_age:.1f} years"""

        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        MODEL_NAME = "gpt-4o"

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": analysis_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "highest_scoring_criteria": [
                                c for c in avg_criteria[-3:] if c["avg_score"] > 1
                            ],
                            "lowest_scoring_criteria": [
                                c for c in avg_criteria[:3] if c["avg_score"] < 1
                            ],
                            "common_strengths": common_strengths[:10],
                            "common_weaknesses": common_weaknesses[:10],
                            "avg_writing_age": avg_writing_age,
                        }
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )

        analysis = json.loads(response.choices[0].message.content)
        return JSONResponse(
            content={
                "strengths": analysis.get("strengths", ["No strengths identified"]),
                "areas_for_development": analysis.get(
                    "areas_for_development", ["No areas identified"]
                ),
                "practice_activities": analysis.get(
                    "practice_activities", ["No activities suggested"]
                ),
            }
        )

    except Exception as e:
        logger.error(f"Error generating class feedback: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "strengths": ["Error analyzing submissions"],
                "areas_fordevelopment": ["Error analyzing submissions"],
                "practice_activities": ["Error analyzing submissions"],
            },
        )


@app.get("/data_analysis", response_class=HTMLResponse)
async def data_analysis(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_classes = db.query(Class).filter_by(teacher_id=current_user.id).all()
    now = datetime.now()

    return templates.TemplateResponse(
        "data_analysis.html", {"request": request, "classes": user_classes, "now": now}
    )


@app.get("/api/students")
async def get_api_students(
    class_id: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if class_id == "all":
        students = (
            db.query(Student)
            .join(Class)
            .filter(Class.teacher_id == current_user.id)
            .order_by(Student.first_name, Student.last_name)
            .all()
        )
    else:
        students = (
            db.query(Student)
            .join(Class)
            .filter(Class.id == class_id, Class.teacher_id == current_user.id)
            .order_by(Student.first_name, Student.last_name)
            .all()
        )

    return JSONResponse(
        {
            "students": [
                {
                    "id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "class_id": student.class_id,
                }
                for student in students
            ]
        }
    )


@app.get("/api/student_data")
async def get_api_student_data(
    ids: Optional[str] = Query(default=""),
    class_id: Optional[str] = Query(default="all"),
    time_period: Optional[str] = Query(default="all"),
    chart_type: Optional[str] = Query(default="writing_scores"),
    include_average: Optional[bool] = Query(default=False),
    average_type: Optional[str] = Query(default="all"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    student_id_list = [int(sid) for sid in ids.split(",") if sid.isdigit()]
    time_filter = None

    if time_period != "all":
        now = datetime.now()
        days_map = {"month": 30, "quarter": 90, "year": 365}
        if time_period in days_map:
            time_filter = now - timedelta(days=days_map[time_period])

    datasets = []
    all_dates = set()

    for student_id in student_id_list:
        student = (
            db.query(Student)
            .join(Class)
            .filter(Student.id == student_id, Class.teacher_id == current_user.id)
            .first()
        )
        if not student:
            continue

        query = db.query(Writing).filter(Writing.student_id == student_id)
        if time_filter:
            query = query.filter(Writing.created_at >= time_filter)
        samples = query.order_by(Writing.created_at).all()

        data_points = []
        for sample in samples:
            value = None
            if chart_type == "writing_scores" and sample.criteria_marks:
                total = len(sample.criteria_marks)
                met = sum(1 for m in sample.criteria_marks if m.score == 2)
                partial = sum(1 for m in sample.criteria_marks if m.score == 1)
                value = (met / total) * 100 + (partial / total) * 50
            elif chart_type == "writing_age" and sample.writing_age:
                try:
                    value = float(sample.writing_age.split()[0])
                except:
                    continue
            elif chart_type == "age_difference" and sample.writing_age:
                try:
                    writing_age = float(sample.writing_age.split()[0])
                    actual_age = (
                        sample.created_at.date() - student.date_of_birth
                    ).days / 365.25
                    value = writing_age - actual_age
                except:
                    continue
            else:
                continue

            date_str = f"{sample.created_at.strftime('%Y-%m-%d')} ({sample.id})"
            date_display = sample.created_at.strftime("%d %b %Y")
            all_dates.add(date_str)
            data_points.append(
                {
                    "date": date_str,
                    "date_display": date_display,
                    "value": value,
                    "writing_id": sample.id,
                }
            )

        if data_points:
            sorted_points = sorted(data_points, key=lambda x: x["date"])
            datasets.append(
                {
                    "student_id": student.id,
                    "name": f"{student.first_name} {student.last_name}",
                    "data": [p["value"] for p in sorted_points],
                    "dates": [p["date"] for p in sorted_points],
                    "is_average": False,
                }
            )

    # Average dataset for class
    if include_average and class_id != "all" and class_id.isdigit():
        class_obj = (
            db.query(Class)
            .filter_by(id=int(class_id), teacher_id=current_user.id)
            .first()
        )
        if class_obj:
            student_ids = [
                s.id for s in db.query(Student).filter_by(class_id=class_obj.id).all()
            ]
            all_dates_list = sorted(all_dates)
            avg_data = []

            for date_str in all_dates_list:
                if " (" in date_str:
                    date_part = date_str.split(" (")[0]
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d").date()
                    next_day = date_obj + timedelta(days=1)
                    writings = (
                        db.query(Writing)
                        .filter(
                            Writing.student_id.in_(student_ids),
                            Writing.created_at >= date_obj,
                            Writing.created_at < next_day,
                        )
                        .all()
                    )

                    values = []
                    for w in writings:
                        if chart_type == "writing_scores" and w.criteria_marks:
                            total = len(w.criteria_marks)
                            achieved = sum(m.score for m in w.criteria_marks)
                            if total:
                                values.append((achieved / (total * 2)) * 100)
                        elif chart_type == "writing_age" and w.writing_age:
                            try:
                                values.append(float(w.writing_age.split()[0]))
                            except:
                                pass
                        elif chart_type == "age_difference" and w.writing_age:
                            try:
                                writing_age = float(w.writing_age.split()[0])
                                actual_age = (
                                    w.created_at.date() - student.date_of_birth
                                ).days / 365.25
                                values.append(writing_age - actual_age)
                            except:
                                pass
                    avg_data.append(sum(values) / len(values) if values else None)

            if any(avg_data):
                datasets.append(
                    {
                        "student_id": "average",
                        "name": f"{class_obj.name} Class Average",
                        "data": avg_data,
                        "dates": all_dates_list,
                        "is_average": True,
                    }
                )

    # Format date display map
    date_display_map = {}
    for ds in datasets:
        for date_key in ds.get("dates", []):
            if " (" in date_key:
                date_part = date_key.split(" (")[0]
                try:
                    date_obj = datetime.strptime(date_part, "%Y-%m-%d")
                    display = date_obj.strftime("%d %b %Y")
                    date_display_map[date_key] = display
                except:
                    date_display_map[date_key] = date_key

    insights = {}
    if datasets:
        insights = {
            "key_observations": [
                "Select multiple students to compare their progress over time.",
                "Use the chart filters to explore different metrics and time periods.",
            ],
            "recommendations": "Focus on students showing significant differences from the class average.",
        }

    return JSONResponse(
        {
            "labels": sorted(all_dates),
            "date_displays": date_display_map,
            "datasets": datasets,
            "insights": insights,
        }
    )


@app.get("/student/{student_id}/portfolio", name="student_portfolio")
async def student_portfolio(
    student_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        student = db.query(Student).filter(Student.id == student_id).first()

        if not student:
            raise HTTPException(status_code=404, detail="Student not found")

        # Permission check
        if student.class_group.teacher_id != current_user.id:
            request.session["flash"] = {
                "message": "You do not have permission to view this portfolio.",
                "category": "danger",
            }
            return RedirectResponse(url="/", status_code=303)

        from sqlalchemy.orm import joinedload

        writing_samples = (
            db.query(Writing)
            .options(joinedload(Writing.criteria_marks), joinedload(Writing.assignment))
            .filter(Writing.student_id == student_id)
            .order_by(Writing.created_at.desc())
            .all()
        )

        assignments = (
            db.query(Assignment).filter(Assignment.class_id == student.class_id).all()
        )

        # Average criteria met
        total_criteria_scores = 0
        total_criteria_count = 0
        for sample in writing_samples:
            if sample.criteria_marks:
                total_criteria_count += len(sample.criteria_marks)
                total_criteria_scores += sum(
                    mark.score for mark in sample.criteria_marks
                )

        average_criteria_met = (
            (total_criteria_scores / (total_criteria_count * 2)) * 100
            if total_criteria_count > 0
            else None
        )

        # Progress rating calculation
        age_differences = []
        for sample in writing_samples:
            if sample.writing_age:
                try:
                    writing_age_value = float(sample.writing_age.split()[0])
                    today = datetime.now().date()
                    birth_date = student.date_of_birth
                    student_age = (today - birth_date).days / 365.25
                    age_diff = round(writing_age_value - student_age, 1)

                    age_differences.append(
                        {
                            "sample_id": sample.id,
                            "date": sample.created_at,
                            "filename": sample.filename,
                            "writing_age": writing_age_value,
                            "student_age": student_age,
                            "difference": age_diff,
                            "assignment": (
                                sample.assignment.title
                                if sample.assignment
                                else "No Assignment"
                            ),
                        }
                    )
                except (ValueError, AttributeError, IndexError):
                    continue

        progress_rating = None
        if age_differences:
            age_differences.sort(key=lambda x: x["date"], reverse=True)
            latest = age_differences[: min(3, len(age_differences))]
            avg_diff = sum(item["difference"] for item in latest) / len(latest)
            if avg_diff >= 3:
                progress_rating = "Excellent"
            elif avg_diff >= 2:
                progress_rating = "Very Good"
            elif avg_diff >= 1:
                progress_rating = "Good"
            elif avg_diff >= 0:
                progress_rating = "Satisfactory"
            else:
                progress_rating = "Needs Support"

        # Chart data prep
        chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "Assignment Score",
                    "data": [],
                    "backgroundColor": "rgba(75, 192, 192, 0.2)",
                    "borderColor": "rgba(75, 192, 192, 1)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "pointBackgroundColor": "rgba(75, 192, 192, 1)",
                    "fill": True,
                }
            ],
        }

        age_chart_data = {
            "labels": [],
            "datasets": [
                {
                    "label": "Writing Age",
                    "data": [],
                    "borderColor": "rgba(54, 162, 235, 1)",
                    "backgroundColor": "rgba(54, 162, 235, 0.2)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "fill": False,
                },
                {
                    "label": "Actual Age",
                    "data": [],
                    "borderColor": "rgba(255, 99, 132, 1)",
                    "backgroundColor": "rgba(255, 99, 132, 0.2)",
                    "borderWidth": 2,
                    "pointRadius": 5,
                    "fill": False,
                },
            ],
        }

        for sample in reversed(writing_samples):
            chart_data["labels"].append(sample.created_at.strftime("%d %b %Y"))
            if sample.criteria_marks:
                total_marks = len(sample.criteria_marks)
                score = sum(mark.score for mark in sample.criteria_marks)
                chart_data["datasets"][0]["data"].append(
                    (score / (total_marks * 2)) * 100
                )
            else:
                chart_data["datasets"][0]["data"].append(0)

            if sample.writing_age:
                try:
                    writing_age_val = float(sample.writing_age.split()[0])
                    today = datetime.now().date()
                    birth_date = student.date_of_birth
                    student_age = (today - birth_date).days / 365.25
                    age_chart_data["labels"].append(
                        sample.created_at.strftime("%d %b %Y")
                    )
                    age_chart_data["datasets"][0]["data"].append(writing_age_val)
                    age_chart_data["datasets"][1]["data"].append(student_age)
                except Exception:
                    continue

        # Prev/next student navigation
        class_students = (
            db.query(Student)
            .filter(Student.class_id == student.class_id)
            .order_by(Student.first_name)
            .all()
        )
        current_index = next(
            (i for i, s in enumerate(class_students) if s.id == student.id), None
        )

        prev_student = (
            class_students[current_index - 1]
            if current_index and current_index > 0
            else class_students[-1]
        )
        next_student = (
            class_students[(current_index + 1) % len(class_students)]
            if current_index is not None
            else None
        )

        return templates.TemplateResponse(
            "student_portfolio_new_temp.html",
            context={
                "request": request,
                "student": student,
                "writing_samples": writing_samples,
                "assignments": assignments,
                "average_criteria_met": average_criteria_met,
                "progress_rating": progress_rating,
                "prev_student": prev_student,
                "next_student": next_student,
                "chart_data": json.dumps(chart_data),
                "age_chart_data": json.dumps(age_chart_data),
                "age_differences": age_differences,
            },
        )
    except Exception as e:
        print(f"error fetching student{e}")


@app.get("/student/{student_id}/export_portfolio", name="export_student_portfolio")
async def export_student_portfolio(
    student_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export a student's portfolio as a CSV file.
    Only the student's class teacher is authorized to perform this export.
    """
    student = db.query(Student).get(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if student.class_group.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied")

    try:
        output = StringIO()
        writer = csv.writer(output)

        # Header row
        writer.writerow(
            [
                "Date",
                "Assignment",
                "Writing Age",
                "Score",
                "Max Score",
                "Achievement %",
                "Strengths",
                "Areas for Development",
            ]
        )

        samples = (
            db.query(Writing)
            .filter_by(student_id=student_id)
            .order_by(Writing.created_at.desc())
            .all()
        )

        for sample in samples:
            max_score = len(sample.criteria_marks) * 2 if sample.assignment_id else 0
            achieved_score = (
                sum(mark.score for mark in sample.criteria_marks)
                if sample.assignment_id
                else 0
            )
            percent = (
                round((achieved_score / max_score * 100), 1) if max_score > 0 else "N/A"
            )

            feedback_parts = (
                sample.feedback.split("\n\n") if sample.feedback else ["", ""]
            )
            strengths = (
                feedback_parts[0].replace("Strengths:", "").strip()
                if len(feedback_parts) > 0
                else ""
            )
            development = (
                feedback_parts[1].replace("Areas for Development:", "").strip()
                if len(feedback_parts) > 1
                else ""
            )

            writer.writerow(
                [
                    sample.created_at.strftime("%Y-%m-%d"),
                    sample.assignment.title if sample.assignment else "Free Writing",
                    sample.writing_age,
                    achieved_score if max_score > 0 else "N/A",
                    max_score if max_score > 0 else "N/A",
                    f"{percent}%" if isinstance(percent, (int, float)) else percent,
                    strengths,
                    development,
                ]
            )

        output.seek(0)

        filename = f"{student.first_name}_{student.last_name}_portfolio_{datetime.now().strftime('%Y%m%d')}.csv"
        return StreamingResponse(
            output,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error(f"Error exporting portfolio for student {student_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to export portfolio")


@app.post("/writing/{writing_id}/update_filename")
async def update_writing_filename(
    writing_id: int,
    request: Request,
    filename: Optional[str] = Form(None),  
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Update the filename of a writing sample.
    Accepts both JSON and form data.
    """
    try:

        if request.headers.get("content-type", "").startswith("application/json"):
            data = await request.json()
            new_filename = data.get("filename")
        else:
            new_filename = filename

        if not new_filename:
            if request.headers.get("accept", "").startswith("application/json"):
                raise HTTPException(status_code=400, detail="Filename is required")
            return RedirectResponse(
                url=str(request.headers.get("referer", "/")), status_code=303
            )

        writing = db.query(Writing).get(writing_id)
        if not writing:
            raise HTTPException(status_code=404, detail="Writing not found")

        student = db.query(Student).get(writing.student_id)
        if not student or student.class_group.teacher_id != current_user["id"]:
            if request.headers.get("accept", "").startswith("application/json"):
                raise HTTPException(status_code=403, detail="Unauthorized")
            return RedirectResponse(url="/", status_code=303)

        writing.filename = new_filename
        db.commit()

        if request.headers.get("accept", "").startswith("application/json"):
            return JSONResponse(
                content={"success": True, "filename": new_filename}, status_code=200
            )
        return RedirectResponse(
            url=str(request.headers.get("referer", "/")), status_code=303
        )

    except Exception as e:
        logger.error(f"Error updating writing filename: {str(e)}")
        db.rollback()

        if request.headers.get("accept", "").startswith("application/json"):
            raise HTTPException(status_code=500, detail="Failed to update filename")
        return RedirectResponse(url="/", status_code=303)


logger = logging.getLogger(__name__)


class BulkDeleteRequest(BaseModel):
    writing_ids: List[int]


@app.post("/writing/bulk_delete")
async def bulk_delete_writing(
    request: Request,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
    writing_ids: Optional[Union[List[int], None]] = Form(None),
):
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
            writing_ids = body.get("writing_ids", [])
        else:
            form = await request.form()
            writing_ids = form.getlist("writing_ids")

        if not writing_ids:
            return JSONResponse(
                {"error": "No writing samples selected"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # Fetch writings
        writings = db.query(Writing).filter(Writing.id.in_(writing_ids)).all()

        if not writings:
            return JSONResponse(
                {"error": "No matching writing samples found"},
                status_code=status.HTTP_404_NOT_FOUND,
            )

        student_id = writings[0].student_id if writings else None

        for writing in writings:
            student = db.query(Student).filter_by(id=writing.student_id).first()
            if not student or student.class_group.teacher_id != current_user.id:
                return JSONResponse(
                    {"error": "Unauthorized access to one or more writing samples"},
                    status_code=status.HTTP_403_FORBIDDEN,
                )
            db.delete(writing)

        db.commit()

        if request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"success": True}, status_code=status.HTTP_200_OK)
        else:
            redirect_url = f"/student/{student_id}/portfolio" if student_id else "/"
            return RedirectResponse(
                url=redirect_url, status_code=status.HTTP_303_SEE_OTHER
            )

    except Exception as e:
        logger.error(f"Error bulk deleting writing samples: {str(e)}")
        db.rollback()
        if request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse(
                {"error": "Failed to delete writing samples"},
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        else:
            return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/writing/{writing_id}/print_report", response_class=HTMLResponse)
async def print_writing_report(
    writing_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Render a printable report of a student's writing sample.
    """
    # Fetch writing
    writing = db.query(Writing).filter_by(id=writing_id).first()
    if not writing:
        raise HTTPException(status_code=404, detail="Writing not found")

    # Fetch student
    student = db.query(Student).filter_by(id=writing.student_id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    # Authorization check
    if student.class_group.teacher_id != current_user.id:
        return RedirectResponse(url="/", status_code=302)

    # Score calculations
    total_possible_marks = len(writing.criteria_marks) * 2 if writing.assignment else 0
    achieved_marks = (
        sum(mark.score for mark in writing.criteria_marks) if writing.assignment else 0
    )
    percentage = (
        round((achieved_marks / total_possible_marks * 100), 1)
        if total_possible_marks > 0
        else 0
    )

    # Feedback parsing
    feedback_parts = writing.feedback.split("\n\n") if writing.feedback else ["", ""]
    strengths = (
        feedback_parts[0].replace("Strengths:", "").strip() if feedback_parts else ""
    )
    development = (
        feedback_parts[1].replace("Areas for Development:", "").strip()
        if len(feedback_parts) > 1
        else ""
    )

    # Age calculations
    student_age = (writing.created_at.date() - student.date_of_birth).days / 365.25
    student_age_str = f"{int(student_age)} years {int((student_age % 1) * 12)} months"
    writing_age_str = (
        writing.writing_age.replace("Estimated writing age:", "").strip()
        if writing.writing_age
        else "N/A"
    )

    return templates.TemplateResponse(
        "print_report.html",
        {
            "request": request,
            "writing": writing,
            "student": student,
            "total_marks": total_possible_marks,
            "achieved_marks": achieved_marks,
            "percentage": percentage,
            "strengths": strengths,
            "development": development,
            "student_age": student_age_str,
            "writing_age": writing_age_str,
        },
    )


@app.post("/student/{student_id}/delete")
def delete_student(
    request: Request,
    student_id,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    from models import Student

    student = db.query(Student).get(student_id)

    # Check if current user is the teacher of this student's class
    if student.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, detail={"error": "Unauthorized"})

    try:
        db.delete(student)
        db.commit()
        request.session["flash"] = {"message": "Class ID is required", "type": "error"}
        return JSONResponse(status_code=200, detail={"sucess": True})
    except Exception as e:
        logger.error(f"Error deleting student: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, detail={"error": "Failed to delete student"}
        )


@app.post("/wagoll_example/save")
async def save_wagoll_example(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Save a WAGOLL example."""
    from models import WagollExample, Assignment

    try:
        data = await request.json()
        assignment_id = data.get("assignment_id")
        title = data.get("title")
        content = data.get("content")
        explanations = data.get("explanations")
        is_public = data.get("is_public", False)

        if not title or not content:
            return JSONResponse(
                status_code=400,
                content={"success": False, "error": "Title and content are required"},
            )

        # If assignment_id is provided, verify ownership
        if assignment_id:
            assignment = db.query(Assignment).get(assignment_id)
            if (
                not assignment
                or not assignment.class_group
                or assignment.class_group.teacher_id != current_user.id
            ):
                return JSONResponse(
                    status_code=403, content={"success": False, "error": "Unauthorized"}
                )

        # Create the WAGOLL example
        example = WagollExample(
            title=title,
            content=content,
            explanations=explanations,
            is_public=is_public,
            assignment_id=assignment_id,
            teacher_id=current_user.id,
        )

        db.add(example)
        db.commit()

        return JSONResponse(content={"success": True, "id": example.id})

    except Exception as e:
        logger.error(f"Error saving WAGOLL example: {str(e)}")
        db.rollback()
        return JSONResponse(
            status_code=500, content={"success": False, "error": str(e)}
        )


@app.post("/wagoll_example/{example_id}/delete")
def delete_wagoll_example(
    example_id,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a WAGOLL example."""
    from models import WagollExample

    example = db.query(WagollExample).get(example_id)
    if example.teacher_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        db.delete(example)
        db.commit()

        return JSONResponse(status_code=200, content={"success": True})

    except Exception as e:
        logger.error(f"Error deleting WAGOLL example: {str(e)}")
        db.rollback()
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/assignments", response_class=HTMLResponse)
async def assignments(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
        "assignments.html", {"request": request, "current_user": current_user}
    )


@app.post("/class/{class_id}/assignments/new")
async def create_assignment(
    class_id: int,
    title: str = Form(...),
    curriculum: str = Form(...),
    genre: str = Form(...),
    custom_genre: str = Form(None),
    criteria_description: List[str] = Form(None),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    class_obj = db.query(Class).filter(Class.id == class_id).first()
    if not class_obj:
        raise HTTPException(status_code=404, detail="Class not found")

    if class_obj.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    logger.debug(f"Creating assignment for class {class_id}")

    form = AssignmentForm(
        title=title, curriculum=curriculum, genre=genre, custom_genre=custom_genre
    )

    if not criteria_description:
        return templates.TemplateResponse(
            "create_assignment.html",
            {
                "request": request,
                "form": form,
                "class_obj": class_obj,
                "error": "Please add at least one success criterion.",
            },
        )

    try:
        genre = form.genre
        if genre == "custom" and form.custom_genre:
            genre = form.custom_genre

        assignment = Assignment(
            title=form.title, curriculum=form.curriculum, genre=genre, class_id=class_id
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        for desc in criteria_description:
            if desc.strip():
                criteria = Criteria(
                    description=desc.strip(), assignment_id=assignment.id
                )
                db.add(criteria)
        db.commit()
        logger.debug("Assignment and criteria created")
        return RedirectResponse(url="/assignments", status_code=303)

    except Exception as e:
        db.rollback()
        logger.error(f"Error: {str(e)}")
        return templates.TemplateResponse(
            "create_assignment.html",
            {
                "request": request,
                "form": form,
                "class_obj": class_obj,
                "error": "Error creating assignment. Please try again.",
            },
        )


# app/routes/assignment_routes.py


@app.api_route(
    "/assignment/{assignment_id}/edit",
    methods=["GET", "POST"],
    response_class=HTMLResponse,
)
async def edit_assignment(
    request: Request,
    assignment_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    assignment = db.query(Assignment).filter_by(id=assignment_id).first()
    if not assignment:
        return RedirectResponse(url="/assignments", status_code=HTTP_302_FOUND)

    if assignment.class_group.teacher_id != current_user.id:
        request.session["flash"] = {
            "message": "You do not have permission to edit this assignment.",
            "category": "danger",
        }
        return RedirectResponse(url="/assignments", status_code=HTTP_302_FOUND)

    form_errors = {}
    form_data = {
        "title": assignment.title,
        "description": assignment.description,
        "curriculum": assignment.curriculum,
        "genre": assignment.genre,
        "custom_genre": "" if assignment.genre != "custom" else assignment.genre,
    }

    if request.method == "POST":
        post_data = await request.form()
        criteria_descriptions = post_data.getlist("criteria-description[]")

        # Update form_data with submitted values to keep user input on error
        form_data["title"] = post_data.get("title")
        form_data["description"] = post_data.get("description")
        form_data["curriculum"] = post_data.get("curriculum")
        form_data["genre"] = post_data.get("genre")
        form_data["custom_genre"] = post_data.get("custom_genre")

        # Validate criteria
        if not criteria_descriptions or all(
            not desc.strip() for desc in criteria_descriptions
        ):
            form_errors["criteria"] = ["Please add at least one success criterion."]

        # Validate title and description
        if not form_data["title"]:
            form_errors["title"] = ["Title is required."]
        if not form_data["description"] or len(form_data["description"].strip()) < 10:
            form_errors["description"] = ["Description must be at least 10 characters."]

        if form_errors:
            # Render template directly with errors and user input — no flashing or redirecting
            return templates.TemplateResponse(
                "edit_assignment.html",
                {
                    "request": request,
                    "form": form_data,
                    "form_errors": form_errors,
                    "assignment": assignment,
                },
            )

        # If no errors, update DB
        try:
            assignment.title = form_data["title"]
            assignment.description = form_data["description"]
            assignment.curriculum = form_data["curriculum"]
            genre = (
                form_data["custom_genre"]
                if form_data["genre"] == "custom" and form_data["custom_genre"]
                else form_data["genre"]
            )
            assignment.genre = genre

            existing_criteria = {c.description: c for c in assignment.criteria}
            new_criteria = []
            for desc in criteria_descriptions:
                desc = desc.strip()
                if desc:
                    if desc in existing_criteria:
                        new_criteria.append(existing_criteria[desc])
                    else:
                        new_criteria.append(
                            Criteria(description=desc, assignment_id=assignment.id)
                        )

            for criterion in assignment.criteria:
                if criterion not in new_criteria:
                    db.delete(criterion)

            assignment.criteria = new_criteria
            db.commit()

            # Set flash message and redirect after successful POST
            request.session["flash"] = {
                "message": "Assignment updated successfully!",
                "category": "success",
            }
            return RedirectResponse(url="/assignments", status_code=HTTP_302_FOUND)

        except Exception:
            db.rollback()
            form_errors["database"] = ["Error updating assignment. Please try again."]
            # Render template with DB error message
            return templates.TemplateResponse(
                "edit_assignment.html",
                {
                    "request": request,
                    "form": form_data,
                    "form_errors": form_errors,
                    "assignment": assignment,
                },
            )

    # GET request — just render form with initial data
    return templates.TemplateResponse(
        "edit_assignment.html",
        {
            "request": request,
            "form": form_data,
            "form_errors": form_errors,
            "assignment": assignment,
        },
    )


@app.post("/assignment/{assignment_id}/delete", response_class=JSONResponse)
async def delete_assignment(
    request: Request,
    assignment_id,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assignment = db.query(Assignment).get(assignment_id)

    # Check if current user is the teacher of this class
    if assignment.class_group.teacher_id != current_user.id:
        return JSONResponse(status_code=403, content={"error": "Unauthorized"})

    try:
        db.delete(assignment)
        db.commit()
        request.session["flash"] = ("Assignment deleted successfully!", "success")
        return JSONResponse(status_code=200, content={"success": True})
    except Exception as e:
        logger.error(f"Error deleting assignment: {str(e)}")
        db.rollback()
        return JSONResponse({"error": "Failed todelete assignment"}), 500


@app.get("/")
async def root(request: Request):
    if is_production(request):
        redirect_url = "/landing"
        response = RedirectResponse(url=redirect_url)
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response
    elif is_local_development(request):
        redirect_url = "/landing"
        response = RedirectResponse(url=redirect_url)
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response
    else:

        redirect_url = "/landing"
        response = RedirectResponse(url=redirect_url)
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "-1"
        return response


@app.get("/static/attached_assets/{filename:path}", response_class=FileResponse)
def serve_attached_assets(filename: str):
    file_path = os.path.join("static/attached_assets", filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)


@app.get("/login", response_class=HTMLResponse)
async def login_get(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


# Add this route after the other route definitions, before the last line
@app.get("/landing", response_class=HTMLResponse, name="landing")
async def landing(request: Request):
    return templates.TemplateResponse("landing_page.html", {"request": request})


@app.get("/signup", response_class=HTMLResponse)
async def show_signup(request: Request):
    return templates.TemplateResponse(
        "signup.html", {"request": request, "form": {}, "error": None}
    )


@app.route("/analyzer")
def analyzer(request: Request, current_user: User = Depends(get_current_user)):
    if current_user is None:
        return RedirectResponse(url="/login")
    elif current_user in request.session:
        return RedirectResponse(url=("add_writing"))


@app.get("/terms", response_class=HTMLResponse)
def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


@app.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@app.get("/data-protection", response_class=HTMLResponse)
def data_protection(request: Request):
    return templates.TemplateResponse("data_protection.html", {"request": request})


@app.get("/data-processing", response_class=HTMLResponse)
def data_processing(request: Request):
    return templates.TemplateResponse("data_processing.html", {"request": request})


# @app.get("/", response_class=HTMLResponse)
# async def index(request: Request):
#     class_form = ClassForm(name="Example Class", year_group="Year 10")
#     student_form = StudentForm(name="John Doe", age=15)
#     return templates.TemplateResponse("home.html", {
#         "request": request,
#         "class_form": class_form,
#         "student_form": student_form
#     })


@app.get("/home", response_class=HTMLResponse, name="home")
def home(request: Request, current_user=Depends(get_current_user)):
    return templates.TemplateResponse(
        "home.html", {"request": request, "current_user": current_user, "form_data": {}}
    )


@app.get("/mobile-camera")
def mobile_camera(request: Request):
    """Completely isolated mobile camera implementation."""
    student_id = request.args.get("student_id", "")
    assignment_id = request.args.get("assignment_id", "")
    # This template is self-contained with no shared JavaScript or templates
    return templates.TemplateResponse(
        "mobile_camera.html", student_id=student_id, assignment_id=assignment_id
    )


app.get("/single-camera")


def single_camera(request: Request):
    """Absolutely standalone camera with no dependencies or inherited templates."""
    student_id = request.args.get("student_id", "")
    assignment_id = request.args.get("assignment_id", "")
    return templates.TemplateResponse(
        "single_camera.html", student_id=student_id, assignment_id=assignment_id
    )


def find_index(list_obj, value):
    try:
        return list_obj.index(value)
    except ValueError:
        return 0


# Register it with Jinja environment
templates.env.filters["index"] = find_index
templates.env.filters["find_index"] = find_index


def calculate_mean(lst):
    """Calculate mean of a list of numbers."""
    try:
        return sum(lst) / len(lst)
    except (TypeError, ZeroDivisionError):
        return 0


def nl2br(value):
    """Convert newlines to <br> tags."""
    if not value:
        return ""
    return Markup(value.replace("\n", "<br>"))


templates.env.filters["mean"] = calculate_mean
templates.env.filters["nl2br"] = nl2br
