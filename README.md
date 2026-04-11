# Smart College Course Registration System

[![Live Demo](https://img.shields.io/badge/🚀_Live_Demo-Render-blue?style=for-the-badge)](https://smart-college-course-registration-system.onrender.com)

**[📱 Open Live Application](https://smart-college-course-registration-system.onrender.com)**

A modular Python project for managing students, courses, registrations, waiting lists, and analytics with a web interface and an optional terminal UI.

## Features

- Course management: add, update, delete, and view details
- Student management: register and view profile
- Smart enrollment with duplicate prevention and waiting lists
- Search and filter by course ID/name, branch, instructor, and category
- Persistent file storage using JSON
- Analytics report generation
- Login and logout support
- Role-based web dashboards (Admin and Student)
- Enrollment trend charts on web dashboard
- Password hashing, student signup, and password reset flow
- Rich terminal UI/UX when `rich` is installed

## Default Login

- Username: `admin`
- Password: `admin123`

## Quick Start

### Run Website

```bash
pip install -r backend/requirements.txt
python run.py
```

Then open `http://127.0.0.1:5000` in your browser.

## Live Deployment

🌐 **Live Application:** https://smart-college-course-registration-system.onrender.com

- **Platform:** Render (Free Tier)
- **Status:** ✅ Active and Running
- **Default Login:**
  - Username: `admin`
  - Password: `admin123`

---

```bash
pip install -r backend/requirements.txt
python backend/cli_app.py
```

## Project Structure

```
├── backend/                    # Server-side code
│   ├── app.py                 # Flask application and routes
│   ├── cli_app.py             # Terminal UI entry point
│   ├── src/
│   │   ├── core/              # Business logic
│   │   │   ├── auth_manager.py
│   │   │   ├── registration_manager.py
│   │   │   └── storage.py
│   │   └── models/            # Data models
│   │       ├── course.py
│   │       └── student.py
│   ├── data/                  # JSON persistence files
│   │   ├── courses.json
│   │   ├── students.json
│   │   ├── users.json
│   │   └── enrollment_log.json
│   └── requirements.txt
├── frontend/                  # Client-side code
│   ├── templates/            # HTML templates
│   │   ├── base.html
│   │   ├── landing.html
│   │   ├── login.html
│   │   ├── signup.html
│   │   ├── dashboard.html
│   │   ├── student_dashboard.html
│   │   ├── admin_dashboard.html
│   │   ├── student_profile.html
│   │   └── reset_password.html
│   └── static/               # CSS/JS assets
│       ├── css/
│       └── js/
└── run.py                    # Main entry point for website
```

## Setup

1. Install dependencies:
```bash
pip install -r backend/requirements.txt
```

2. Run the application:
```bash
python run.py
```

3. Open your browser and navigate to `http://127.0.0.1:5000`
