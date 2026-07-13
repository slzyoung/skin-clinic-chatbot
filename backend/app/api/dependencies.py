from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError
import uuid

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User

# Used for Swagger UI only, actual auth happens via cookies
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db)
) -> User:
    token = request.cookies.get("access_token")
    if not token:
        # Fallback for swagger UI testing
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
        
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        user_id = uuid.UUID(user_id_str)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
    stmt = select(User).where(User.id == user_id, User.deleted_at.is_(None))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
    return user

async def require_admin_role(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    from app.models.user import UserType, Role, UserRole
    if current_user.type != UserType.STAFF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    result = await db.execute(stmt)
    if "ADMIN" not in result.scalars().all():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return current_user

async def require_functional_or_admin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> User:
    from app.models.user import UserType, Role, UserRole
    if current_user.type != UserType.STAFF:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")
    stmt = select(Role.name).join(UserRole, UserRole.role_id == Role.id).where(UserRole.user_id == current_user.id)
    result = await db.execute(stmt)
    roles = result.scalars().all()
    if "ADMIN" not in roles and "FUNCTIONAL" not in roles:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin or Functional access required")
    return current_user
