import os
import django
from django.conf import settings
from django.core.mail import send_mail

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from django.template.loader import render_to_string
from training.models import ClassSchedule

def test_email():
    print("Trying to send TEMPLATE email...")
    
    # Get a class for context
    schedule = ClassSchedule.objects.first()
    if not schedule:
        print("No class found to test with.")
        return

    user_email = 'mdnajishkhan21@gmail.com'
    
    html_message = render_to_string('training/emails/class_reminder_30min.html', {
        'user': schedule.batch.enrollments.first().user, # Grab a dummy user
        'class_schedule': schedule,
    })
    
    plain_message = f"""
Hello Test User,

This is a reminder for your upcoming class: {schedule.topic}
Start Time: {schedule.start_time}

Link: {schedule.meeting_link}
"""

    try:
        send_mail(
            f"TEST REMINDER: {schedule.topic}",
            plain_message,
            settings.EMAIL_HOST_USER,
            [user_email],
            fail_silently=False,
            html_message=html_message
        )
        print("SUCCESS: Template Email sent successfully!")
    except Exception as e:
        print(f"ERROR: Failed to send template email.\n{e}")

if __name__ == "__main__":
    test_email()
