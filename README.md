Team Task Manager 

A full-stack web application for managing projects, assigning tasks, and tracking progress with role-based access control.

🌐 Live Demo: https://team-task-manager-production-25385.up.railway.app

## Features

1. Authentication — Secure signup and login with JWT tokens and bcrypt password hashing
2. Project Management — Create projects, invite team members by email
3. Role-Based Access Control — Admins can manage members and all tasks; Members can update tasks assigned to them
4. Task Tracking — Create tasks with title, description, due date, and assignee; update status (Todo / In Progress / Done)
5. Dashboard — View all assigned tasks, overdue tasks, and status breakdown at a glance

---

## Tech Stack

1. Backend
- Python + FastAPI
- PostgreSQL (raw SQL with psycopg2, no ORM)
- JWT authentication (python-jose)
- bcrypt password hashing (passlib)

2. Frontend
- Plain HTML, CSS, JavaScript (no framework)
- Fetch API for all backend communication

3. Deployment
- Railway (backend + PostgreSQL)

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | /auth/signup | Register a new user | No |
| POST | /auth/login | Login and get JWT token | No |
| POST | /projects | Create a new project | Yes |
| GET | /projects | Get all projects for current user | Yes |
| GET | /projects/{id} | Get project details and members | Yes |
| POST | /projects/{id}/members | Add member to project (admin only) | Yes |
| POST | /projects/{id}/tasks | Create a task in a project | Yes |
| GET | /projects/{id}/tasks | Get all tasks in a project | Yes |
| PATCH | /tasks/{id} | Update task status/details | Yes |
| GET | /dashboard | Get tasks, overdue, and stats | Yes |

---

## Database Schema

users
id (UUID), name, email, password_hash, created_at
projects
id (UUID), name, description, owner_id → users, created_at
project_members
project_id → projects, user_id → users, role (admin/member)
tasks
id (UUID), title, description, status, due_date
project_id → projects, assigned_to → users, created_by → users

---

## Role-Based Access Control

1. Admin — Can add/remove members, create tasks, update any task in the project
2. Member — Can create tasks, update tasks assigned to them or created by them

A user can be an admin in one project and a member in another — roles are per project, not global.

---

## Running Locally

```bash
# Clone the repo
git clone https://github.com/irishkm/team-task-manager
cd team-task-manager

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL and run migrations
# (requires Docker or a local PostgreSQL instance)
psql -U postgres -d taskmanager < migrations/001_init.sql

# Set environment variables
DB_HOST=localhost
DB_PORT=5432
DB_NAME=taskmanager
DB_USER=postgres
DB_PASSWORD=your_password
SECRET_KEY=your_secret_key

# Start the server
uvicorn api.main:app --reload
```

---

```
## Project Structure

team-task-manager/
├── api/
│   ├── main.py          # FastAPI app, middleware, routing
│   ├── db.py            # PostgreSQL connection
│   ├── security.py      # JWT and password hashing
│   └── routes/
│       ├── auth.py      # Signup, login
│       ├── projects.py  # Project and member management
│       ├── tasks.py     # Task creation and updates
│       └── dashboard.py # Dashboard aggregation
├── frontend/
│   ├── index.html       # Login/Signup page
│   ├── dashboard.html   # User dashboard
│   ├── project.html     # Project detail page
│   └── style.css        # Shared styles
├── migrations/
│   └── 001_init.sql     # Database schema
├── railway.toml         # Railway deployment config
└── requirements.txt
```
