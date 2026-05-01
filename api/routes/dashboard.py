from fastapi import APIRouter, Header
from api.db import get_connection
from api.routes.projects import get_current_user
from datetime import date

router = APIRouter()

@router.get("/dashboard")
def get_dashboard(authorization: str = Header(None)):
    user = get_current_user(authorization)
    user_id = user["sub"]

    conn = get_connection()
    cur = conn.cursor()

    # all tasks assigned to me
    cur.execute("""
        SELECT t.id, t.title, t.status, t.due_date, p.name as project_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.assigned_to = %s
        ORDER BY t.due_date ASC NULLS LAST
    """, (user_id,))
    my_tasks = cur.fetchall()

    # overdue tasks (due_date < today and not done)
    today = date.today()
    cur.execute("""
        SELECT t.id, t.title, t.due_date, p.name as project_name
        FROM tasks t
        JOIN projects p ON t.project_id = p.id
        WHERE t.assigned_to = %s
          AND t.due_date < %s
          AND t.status != 'done'
        ORDER BY t.due_date ASC
    """, (user_id, today))
    overdue = cur.fetchall()

    # status breakdown across all my tasks
    cur.execute("""
        SELECT status, COUNT(*) 
        FROM tasks 
        WHERE assigned_to = %s 
        GROUP BY status
    """, (user_id,))
    status_rows = cur.fetchall()

    # my projects
    cur.execute("""
        SELECT p.id, p.name, pm.role
        FROM projects p
        JOIN project_members pm ON p.id = pm.project_id
        WHERE pm.user_id = %s
    """, (user_id,))
    projects = cur.fetchall()

    cur.close()
    conn.close()

    status_breakdown = {"todo": 0, "in_progress": 0, "done": 0}
    for row in status_rows:
        status_breakdown[row[0]] = row[1]

    return {
        "my_tasks": [{
            "id": str(t[0]),
            "title": t[1],
            "status": t[2],
            "due_date": str(t[3]) if t[3] else None,
            "project_name": t[4]
        } for t in my_tasks],

        "overdue_tasks": [{
            "id": str(t[0]),
            "title": t[1],
            "due_date": str(t[2]),
            "project_name": t[3]
        } for t in overdue],

        "status_breakdown": status_breakdown,

        "projects": [{
            "id": str(p[0]),
            "name": p[1],
            "role": p[2]
        } for p in projects]
    }