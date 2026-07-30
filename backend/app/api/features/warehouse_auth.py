from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
import bcrypt

from app.core.database import get_db
from app.core.framework.models.auth import User, Role
from app.api.system.auth import create_access_token, create_refresh_token
from app.infrastructure.database.repositories.entity_repository import EntityRepository

router = APIRouter(prefix="/auth", tags=["auth"])

class RegisterRequest(BaseModel):
    company_name: str
    contact_person: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
        
    # Get or create company role
    role_result = await db.execute(select(Role).where(Role.name == "company"))
    role = role_result.scalar_one_or_none()
    if not role:
        role = Role(name="company")
        db.add(role)
        await db.commit()
        
    # Create User
    hashed = bcrypt.hashpw(req.password.encode(), bcrypt.gensalt()).decode()
    new_user = User(
        username=req.email,
        email=req.email,
        full_name=req.contact_person,
        hashed_password=hashed,
        is_active=True
    )
    new_user.roles.append(role)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create Company entity
    repo = EntityRepository("company", db)
    await repo.create({
        "name": req.company_name,
        "contact_person": req.contact_person,
        "email": req.email,
        "status": "pending",
        "user": new_user.id
    })
    
    return {"status": "success", "message": "Company registered successfully"}

@router.post("/login_company")
async def login_company(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    
    if not user or not bcrypt.checkpw(req.password.encode(), user.hashed_password.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
        
    access_token = create_access_token(data={"sub": user.username, "user_id": user.id})
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }
