import os
import django
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'recgetup.settings')
django.setup()

from django.contrib.auth.models import User
from training.models import ClassSession, Attendance, Enrollment, BatchSchedule

def check_assignments():
    try:
        user = User.objects.get(username='n8nai17@gmail.com')
        schedules = BatchSchedule.objects.filter(tutor=user)
        
        print(f"Stats for: {user.get_full_name()} ({user.username})")
        print(f"Assigned Recurring Batches: {schedules.count()}")
        print("-" * 50)
        
        for s in schedules:
            enr_count = Enrollment.objects.filter(batch=s.batch).count()
            print(f"Batch: {s.batch.name} | Workshop: {s.batch.workshop.title} | Enrolled Students: {enr_count}")
            
        sessions = ClassSession.objects.filter(tutor=user)
        print("-" * 50)
        print(f"Total Concrete Sessions: {sessions.count()}")
            
    except User.DoesNotExist:
        print("User n8nai17@gmail.com not found.")

if __name__ == "__main__":
    check_assignments()
