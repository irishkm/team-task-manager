from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from api.db import get_connection
from api.Security import hash_password, verify_password, create_access_token

router = APIRouter()

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/signup")
def signup(body: SignupRequest):
    conn = get_connection()
    cur = conn.cursor()
    
    # check if email already exists
    cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    password_hash = hash_password(body.password)
    
    cur.execute(
        "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s) RETURNING id, name, email",
        (body.name, body.email, password_hash)
    )
    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    token = create_access_token({"sub": str(user[0]), "email": user[2]})
    
    return {"token": token, "user": {"id": user[0], "name": user[1], "email": user[2]}}

@router.post("/login")
def login(body: LoginRequest):
    conn = get_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT id, name, email, password_hash FROM users WHERE email = %s", (body.email,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    
    if not user or not verify_password(body.password, user[3]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    token = create_access_token({"sub": str(user[0]), "email": user[2]})
    
    return {"token": token, "user": {"id": user[0], "name": user[1], "email": user[2]}}