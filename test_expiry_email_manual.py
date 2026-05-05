import os
import django
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recgetup.settings')
django.setup()

from django.contrib.auth.models import User

def send_test():
    email = 'mdnajishkhan21@gmail.com'
    user = User.objects.filter(email=email).first()
    if not user:
        print(f"User with email {email} not found. Sending to a placeholder.")
        user = User(first_name="Md", username="testuser", email=email)

    context = {
        'user': user,
        'batch_name': 'Morning Batches',
        'days_left': 3,
        'dashboard_link': 'http://127.0.0.1:8000/training/dashboard/',
    }
    
    html_content = render_to_string('training/emails/package_expiry.html', context)
    text_content = "Test Expiry Email - Design Check"
    
    print(f"Sending test email to {email}...")
    send_mail(
        "Test: Your access expires in 3 days",
        text_content,
        settings.EMAIL_HOST_USER,
        [email],
        html_message=html_content,
        fail_silently=False
    )
    print("Email sent successfully!")

if __name__ == "__main__":
    send_test()
