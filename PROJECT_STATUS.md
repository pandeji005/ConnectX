# Project Status & Overview: Project Collab Tool

## Overview
The **Project Collab Tool** is a web-based project and task management application built using Python's Flask framework. It provides role-based access control, allowing "Team Leaders" and "Team Members" to collaborate on projects, assign and manage tasks, and share files. The application also includes authentication (both local credentials and Google OAuth), search functionality, and basic file management.

## Tech Stack
*   **Backend:** Python, Flask
*   **Database:** MySQL (via SQLAlchemy ORM)
*   **Authentication:** Werkzeug (password hashing), Authlib (Google OAuth 2.0)
*   **Frontend:** HTML/CSS/JS (using Jinja2 templating, Bootstrap/Custom CSS expected based on previous Notion-style UI updates)
*   **Database URI Format:** `mysql+pymysql://root:<password>@localhost/project_db`

## Database Schemas (Models)
1.  **User (`users`)**
    *   `id` (PK), `username`, `email`, `password`, `role` (team_leader/team_member), `google_id`.
2.  **Project (`projects`)**
    *   `id` (PK), `title`, `description`, `created_by` (User ID), `created_at`.
3.  **Task (`tasks`)**
    *   `id` (PK), `title`, `description`, `status` (e.g., 'To Do', 'In Progress', 'Done'), `priority`, `deadline`, `assigned_to` (User ID), `project_id`, `created_at`.
4.  **File (`files`)**
    *   `id` (PK), `filename`, `filepath`, `uploaded_at`.

## Core Features & Components

### 1. Authentication & User Management
*   **Registration:** Supports username, email, password, and role selection. Includes validation for email (must be `@gmail.com`) and password complexity (minimum 8 chars, letters, numbers, and special characters).
*   **Login:** Validates credentials and redirects users to their respective dashboards based on their role (`team_leader` or `team_member`).
*   **Google OAuth:** Allows users to log in or sign up using their Google accounts.
*   **Logout:** Clears the user session.

### 2. Role-Based Dashboards
*   **Team Leader Dashboard (`tl_dashboard`):**
    *   View all tasks and filter them by status.
    *   View all projects.
    *   View a list of all team members.
    *   Manage tasks (Create, Edit, Delete).
*   **Team Member Dashboard (`tm_dashboard`):**
    *   Search and view available projects.
    *   View tasks specifically assigned to them.
    *   Update the status of their assigned tasks.

### 3. Project Management
*   **Create Project:** Users can create new projects by providing a title and description. The project is associated with the creator.

### 4. Task Management
*   **Create Task:** Team leaders can create tasks, assign them to team members, set deadlines, and specify priority levels.
*   **Edit Task:** Modify task details like title, description, priority, and deadline.
*   **Update Status:** Team members can update the status of their mapped tasks (e.g., from "To Do" to "Done").
*   **Delete Task:** Removing a task entirely from the system.
*   **Filter Tasks:** Filter tasks based on their current status.

### 5. File Management
*   **Upload File:** Users can upload files which are stored locally in the `uploads/` directory and referenced in the database.
*   **View Files:** List all uploaded files.
*   **Download/View File:** Access a specific uploaded file by its ID.
*   **Delete File:** Remove a file from both the database and the local storage directory.

### 6. Chat Action System (Stub/Bot)
*   **API Endpoint (`/chat-action`):** Receives POST requests with JSON containing an `action` string.
*   **Supported Actions:** `view_tasks`, `add_task`, `delete_task`, `project_status`, `help`, `exit`.
*   Currently, these actions return stubbed string responses (e.g., "📋 Showing your tasks (coming soon)").

## Security Elements
*   Passwords are encrypted using `generate_password_hash` before saving to the database.
*   Sessions are secured using a `secret_key`.
*   OAuth Client secrets are utilized for Google login.
*   Protected routes redirect unauthorized users (without an active session) to the login or home page.

## Missing/Pending Implementation Notes
*   The "Chat Action" functions are currently returning placeholder text ("coming soon").
*   There's no rigorous authorization check on file deletion; any authenticated user might be able to delete files if they can access the route.
*   The database is created automatically (`db.create_all()`) when the app server runs, assuming the MySQL database `project_db` already exists.
