# Django Quiz Management System

A web-based quiz platform built with Django that allows admins to create and manage quizzes and users to attempt them.

## Features
- User authentication
- Quiz creation & management
- Question & answer models
- Template-based UI
- Admin panel integration

## Tech Stack
- Python
- Django
- SQLite (dev)
- HTML / CSS
- Git & GitHub

## Project Structure
- quizzes/ – quiz logic and models
- templates/ – frontend templates
- media/ – ignored in Git
- manage.py – Django entry point

## Setup Instructions
```bash
git clone <repo-url>
cd project
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
