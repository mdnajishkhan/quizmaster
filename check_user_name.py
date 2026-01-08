import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.contrib.auth.models import User

try:
    user = User.objects.get(email='mdnajishkhan21@gmail.com')
    print(f"User: {user.email}")
    print(f"First Name: '{user.first_name}'")
    print(f"Last Name: '{user.last_name}'")
    print(f"Full Name (calculated): '{user.first_name} {user.last_name}'.strip()")
except User.DoesNotExist:
    print("User not found")
except Exception as e:
    print(f"Error: {e}")
