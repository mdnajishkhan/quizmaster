import os
import django
from django.utils import timezone
import datetime

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recgetup.settings')
django.setup()

from training.models import Batch, ClassSchedule, Enrollment

# Get the batch
batch_name = "Morning Batch"
batch = Batch.objects.filter(name=batch_name).first()

if not batch:
    print(f"Batch '{batch_name}' not found!")
else:
    print(f"Found batch: {batch.name} (Workshop: {batch.workshop.title})")
    
    # Check for Tutor (using first available user for now if no tutor defined on batch, 
    # but ClassSchedule requires a tutor. Usually batch has a tutor or we pick one.
    # The debug script showed a class with a tutor, so we can reuse that tutor or pick a superuser.
    
    # Find a tutor (Assuming first superuser or staff for demo)
    from django.contrib.auth import get_user_model
    User = get_user_model()
    tutor = User.objects.filter(is_staff=True).first()
    
    if not tutor:
        print("No tutor found to assign to classes!")
    else:
        # Create timestamps for tomorrow and next week
        now = timezone.now()
        tomorrow = now + datetime.timedelta(days=1)
        next_week = now + datetime.timedelta(days=3)
        
        # Class 1
        c1 = ClassSchedule.objects.create(
            batch=batch,
            tutor=tutor,
            topic="Advanced Composition Techniques",
            description="Learning how to layer instruments effectively.",
            start_time=tomorrow.replace(hour=10, minute=0, second=0),
            end_time=tomorrow.replace(hour=11, minute=30, second=0),
            meeting_link="https://meet.google.com/abc-defg-hij"
        )
        print(f"Created class: {c1.topic} at {c1.start_time}")

        # Class 2
        c2 = ClassSchedule.objects.create(
            batch=batch,
            tutor=tutor,
            topic="Mixing & Mastering Basics",
            description="Introduction to EQ and Compression.",
            start_time=next_week.replace(hour=10, minute=0, second=0),
            end_time=next_week.replace(hour=11, minute=30, second=0),
            meeting_link="https://meet.google.com/xyz-uvw-rst"
        )
        print(f"Created class: {c2.topic} at {c2.start_time}")
