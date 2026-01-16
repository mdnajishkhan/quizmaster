@echo off
cd /d d:\quizmaster\quizsite
call python manage.py send_class_notifications >> cron.log 2>&1
