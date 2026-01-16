import os
import django
from django.conf import settings
from django.utils import timezone
import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from training.models import ClassSchedule, Enrollment, Batch
from django.core.mail import send_mail

def debug_logic():
    print("--- START DEBUG ---")
    
    # 1. Find the Class (Fuzzy match like the command)
    print(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
    now = timezone.now()
    print(f"Current Time: {now}")
    
    print("Fetching ID 3 directly...")
    try:
        c3 = ClassSchedule.objects.get(id=3)
        print(f"ID 3: Topic={c3.topic}, Start={c3.start_time}")
    except ClassSchedule.DoesNotExist:
        print("ID 3 DOES NOT EXIST in this database.")

    classes = ClassSchedule.objects.filter(
        start_time__date=datetime.date(2026, 1, 10)
    )
    
    # DUMP ALL CLASSES
    all_classes = ClassSchedule.objects.all().order_by('-id')[:5]
    print(f"Total Classes in DB: {ClassSchedule.objects.count()}")
    print("Latest 5 Classes:")
    for c in all_classes:
        print(f" - ID: {c.id}, Topic: {c.topic}, Start: {c.start_time}")
        
    # CREATE PROBE
    probe_topic = "DEBUG_PROBE_CLASS"
    if not ClassSchedule.objects.filter(topic=probe_topic).exists():
        print(f"Creating probe class '{probe_topic}'...")
        # Need a batch first
        batch = Batch.objects.first()
        if not batch:
            print("No batch found, cannot create probe.")
            return
            
        ClassSchedule.objects.create(
            batch=batch,
            topic=probe_topic,
            start_time=timezone.now() + datetime.timedelta(days=365)
        )
        print("Probe class created!")
    else:
        print("Probe class already exists.")
        
    schedule = classes.first()
    if not schedule:
        print("No class found for today to test enrollments.")
        return

    # 3. Try Sending
    print("\n--- ATTEMPTING SEND ---")
    for user in users:
        print(f"Sending to: {user.email}")
        try:
            send_mail(
                f"DEBUG REMINDER: {schedule.topic}",
                "This is a debug email. If you get this, the logic works.",
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False
            )
            print("SUCCESS: Send_mail returned without error.")
        except Exception as e:
            print(f"ERROR: Send_mail failed! {e}")

if __name__ == "__main__":
    debug_logic()
