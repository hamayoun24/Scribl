# dependencies/auth.py
from fastapi import Request, Depends, HTTPException, status
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
from sqlalchemy.orm import Session
from database import get_db
from models import User
from fastapi_login import LoginManager
from config import settings as env_settings

async def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to pull `user_id` from request.session (set at login)
    and load the User from the database, or 401 if not logged in.
    """
    user_id = request.session.get("user_id")
    print(f"User ID from session: {user_id}{request.session}")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    user = db.get(User, user_id)
    if not user:
        request.session.pop("user_id", None)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user


# manager = LoginManager(secret=env_settings.SESSION_SECRET, token_url="/auth/token")
# @manager.user_loader
# def load_user(user_id: str) -> User:
#     """
#     Load user from the database using the user_id.
#     """
#     db = next(get_db())
#     user = db.query(User).get(user_id)
#     if not user:
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="User not found"
#         )
#     return user




def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def login_user(request: Request, user: User):
    request.session["user_id"] = user.id
