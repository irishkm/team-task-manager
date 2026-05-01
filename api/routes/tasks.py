from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from typing import Optional
from api.db import get_connection
from api.Security import decode_token
from api.routes.projects import get_current_user

router = APIRouter()

class TaskRequest(BaseModel):
    title: str
    description: Optional[str] = None
    assigned_to: Optional[str] = None  # user id
    due_date: Optional[str] = None     # YYYY-MM-DD

class TaskUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    assigned_to: Optional[str] = None
    due_date: Optional[str] = None

@router.post("/projects/{project_id}/tasks")
def create_task(project_id: str, body: TaskRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    # verify user is a member of this project
    cur.execute(
        "SELECT role FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, user_id)
    )
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="Not a member of this project")

    # if assigned_to is given, verify that user is also a member
    if body.assigned_to:
        cur.execute(
            "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
            (project_id, body.assigned_to)
        )
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Assigned user is not a member of this project")

    cur.execute("""
        INSERT INTO tasks (title, description, project_id, assigned_to, created_by, due_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, title, description, status, due_date, created_at
    """, (body.title, body.description, project_id, body.assigned_to, user_id, body.due_date))

    task = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    return {
        "id": str(task[0]),
        "title": task[1],
        "description": task[2],
        "status": task[3],
        "due_date": str(task[4]) if task[4] else None,
        "created_at": str(task[5])
    }

@router.get("/projects/{project_id}/tasks")
def get_tasks(project_id: str, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    # verify membership
    cur.execute(
        "SELECT 1 FROM project_members WHERE project_id = %s AND user_id = %s",
        (project_id, user_id)
    )
    if not cur.fetchone():
        raise HTTPException(status_code=403, detail="Not a member of this project")

    cur.execute("""
        SELECT t.id, t.title, t.description, t.status, t.due_date, t.created_at,
               u.name as assigned_to_name, u.email as assigned_to_email
        FROM tasks t
        LEFT JOIN users u ON t.assigned_to = u.id
        WHERE t.project_id = %s
        ORDER BY t.created_at DESC
    """, (project_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [{
        "id": str(r[0]),
        "title": r[1],
        "description": r[2],
        "status": r[3],
        "due_date": str(r[4]) if r[4] else None,
        "created_at": str(r[5]),
        "assigned_to": {"name": r[6], "email": r[7]} if r[6] else None
    } for r in rows]

@router.patch("/tasks/{task_id}")
def update_task(task_id: str, body: TaskUpdateRequest, authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    if body.status and body.status not in ("todo", "in_progress", "done"):
        raise HTTPException(status_code=400, detail="Invalid status value")

    conn = get_connection()
    cur = conn.cursor()

    # get the task and verify user is a member of its project
    cur.execute("""
        SELECT t.project_id, t.assigned_to, t.created_by, pm.role
        FROM tasks t
        JOIN project_members pm ON t.project_id = pm.project_id AND pm.user_id = %s
        WHERE t.id = %s
    """, (user_id, task_id))

    task = cur.fetchone()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found or access denied")

    project_id, assigned_to, created_by, role = task

    # members can only update tasks assigned to them or created by them
    # admins can update any task
    if role == "member" and str(assigned_to) != user_id and str(created_by) != user_id:
        raise HTTPException(status_code=403, detail="You can only update tasks assigned to you")

    # build dynamic update query
    fields = []
    values = []

    if body.title is not None:
        fields.append("title = %s")
        values.append(body.title)
    if body.description is not None:
        fields.append("description = %s")
        values.append(body.description)
    if body.status is not None:
        fields.append("status = %s")
        values.append(body.status)
    if body.assigned_to is not None:
        fields.append("assigned_to = %s")
        values.append(body.assigned_to)
    if body.due_date is not None:
        fields.append("due_date = %s")
        values.append(body.due_date)

    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")

    values.append(task_id)
    cur.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = %s RETURNING id, title, status", values)
    updated = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    return {"id": str(updated[0]), "title": updated[1], "status": updated[2]}