# QuizMaster

QuizMaster is a Django-based web application for creating and managing quizzes.  
This project demonstrates practical Django development, including modular apps, template rendering, and secure environment-based configuration.

---

## 🚀 Features

- User authentication
- Quiz creation and management
- Question and answer handling
- Django admin integration
- Template-based frontend
- Environment variable–based configuration

---

## 🛠 Tech Stack

- Python
- Django
- SQLite / MySQL (configurable)
- HTML, CSS
- Git & GitHub
- python-dotenv

---

## 📁 Project Structure

quizsite/
├── quizzes/ # Quiz logic and models
├── templates/ # HTML templates
├── quizsite/ # Project settings and configuration
├── media/ # Media files (ignored in Git)
├── manage.py # Django entry point
├── requirements.txt
└── README.md

---

## ⚙️ Setup Instructions (Local)

### 1️⃣ Clone the repository
```bash
git clone https://github.com/mdnajishkhan/quizmaster.git
cd quizmaster
2️⃣ Create and activate virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# Linux / macOS
source venv/bin/activate

3️⃣ Install dependencies
pip install -r requirements.txt

4️⃣ Configure environment variables

Create a .env file in the project root:

SECRET_KEY=your_secret_key
DEBUG=True

5️⃣ Run migrations and start server
python manage.py migrate
python manage.py runserver

Open:
http://127.0.0.1:8000

🔐 Security Notes

Sensitive data is managed using environment variables

.env, database files, and media files are excluded via .gitignore

Suitable for public portfolio and learning purposes

📌 Purpose of This Project

This project is built to demonstrate:

Real-world Django project structure

Backend logic and template usage

Best practices for configuration and security

Version control workflows using Git

👤 Author
Md Najish Khan
Python / Django Developer
GitHub: https://github.com/mdnajishkhan

