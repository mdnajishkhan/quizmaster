import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recgetup.settings')
django.setup()

from django.contrib.auth import get_user_model
from training.models import Enrollment, ClassSchedule, Batch

User = get_user_model()
now = timezone.now()

print(f"Current Time: {now}")

# Find user 'Md' or similar
users = User.objects.filter(first_name__icontains='Md') | User.objects.filter(username__icontains='Md')

for user in users:
    print(f"\nUser: {user.username} (ID: {user.id}, Name: {user.get_full_name()})")
    
    # Check Enrollments
    enrollments = Enrollment.objects.filter(user=user)
    print(f"  Total Enrollments: {enrollments.count()}")
    
    active = enrollments.filter(expires_at__gt=now)
    print(f"  Active Enrollments: {active.count()}")
    
    for enr in enrollments:
        status = " ACTIVE" if enr.expires_at > now else " EXPIRED"
        print(f"    - Batch: {enr.batch.name} | Expires: {enr.expires_at} | {status}")
        
    # Check Active Batches
    batch_ids = active.values_list('batch_id', flat=True)
    
    # Check Upcoming Classes
    upcoming = ClassSchedule.objects.filter(batch__id__in=batch_ids, start_time__gt=now).order_by('start_time')
    print(f"  Upcoming Classes: {upcoming.count()}")
    for cls in upcoming:
        print(f"    - {cls.topic} @ {cls.start_time} (Batch: {cls.batch.name})")
        
    # Check ALL Classes for this batch
    all_classes = ClassSchedule.objects.filter(batch__id__in=batch_ids).order_by('start_time')
    print(f"  Total Classes in Batch: {all_classes.count()}")
    for cls in all_classes:
         print(f"    - {cls.topic} @ {cls.start_time} (Batch: {cls.batch.name})")

print("\n--------------------------------")
