from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from api.db import get_connection
from api.Security import decode_token

router = APIRouter()

def get_current_user(authorization: str = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization.split(" ")[1]
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload

def require_project_admin(cur, project_id: str, user_id: str):
    cur.execute(
        "SELECT role FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, user_id)
    )
    member = cur.fetchone()
    if not member or member[0] != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

class ProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None

class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"

@router.post("/projects")
def create_project(body: ProjectRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO projects (name, description, owner_id) VALUES (%s, %s, %s) RETURNING id, name, description, created_at",
        (body.name, body.description, user_id)
    )
    project = cur.fetchone()
    project_id = str(project[0])

    # creator is automatically an admin member
    cur.execute(
        "INSERT INTO project_members (project_id, user_id, role) VALUES (%s, %s, %s)",
        (project_id, user_id, "admin")
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"id": project_id, "name": project[1], "description": project[2], "created_at": str(project[3])}

@router.get("/projects")
def get_projects(authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    # only return projects the user is a member of
    cur.execute("""
        SELECT p.id, p.name, p.description, p.created_at, pm.role
        FROM projects p
        JOIN project_members pm ON p.id = pm.project_id
        WHERE pm.user_id = %s
        ORDER BY p.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{"id": str(r[0]), "name": r[1], "description": r[2], "created_at": str(r[3]), "your_role": r[4]} for r in rows]

@router.get("/projects/{project_id}")
def get_project(project_id: str, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    # verify user is a member
    cur.execute("SELECT role FROM project_members WHERE project_id = %s AND user_id = %s", (project_id, user_id))
    membership = cur.fetchone()
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this project")

    cur.execute("SELECT id, name, description, created_at FROM projects WHERE id = %s", (project_id,))
    project = cur.fetchone()

    # get all members
    cur.execute("""
        SELECT u.id, u.name, u.email, pm.role
        FROM project_members pm
        JOIN users u ON pm.user_id = u.id
        WHERE pm.project_id = %s
    """, (project_id,))
    members = cur.fetchall()

    cur.close()
    conn.close()

    return {
        "id": str(project[0]),
        "name": project[1],
        "description": project[2],
        "created_at": str(project[3]),
        "your_role": membership[0],
        "members": [{"id": str(m[0]), "name": m[1], "email": m[2], "role": m[3]} for m in members]
    }

@router.post("/projects/{project_id}/members")
def add_member(project_id: str, body: AddMemberRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    if body.role not in ("admin", "member"):
        raise HTTPException(status_code=400, detail="Role must be admin or member")

    conn = get_connection()
    cur = conn.cursor()

    require_project_admin(cur, project_id, user_id)

    # find user by email
    cur.execute("SELECT id FROM users WHERE email = %s", (body.email,))
    target = cur.fetchone()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    # check if already a member
    cur.execute("SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s", (project_id, str(target[0])))
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="User is already a member")

    cur.execute(
        "INSERT INTO project_members (project_id, user_id, role) VALUES (%s, %s, %s)",
        (project_id, str(target[0]), body.role)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"message": "Member added successfully"}