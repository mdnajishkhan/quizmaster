from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from training.models import Batch, ClassSession, Attendance
from django.utils import timezone
from datetime import timedelta, time, date

class Command(BaseCommand):
    help = 'Generates dummy class data for testing status visualization'

    def handle(self, *args, **kwargs):
        # 1. Target User
        target_email = 'mdnajishkhan21@gmail.com'
        try:
            user = User.objects.get(email=target_email)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"User with email {target_email} not found."))
            return

        # 2. Target Batch
        batch = Batch.objects.filter(enrollments__user=user).first()
        if not batch:
            self.stdout.write(self.style.ERROR(f"User {user.username} is not enrolled in any batch."))
            return

        # 3. Clean up existing dummy sessions for this user/batch to avoid duplicates if re-run
        ClassSession.objects.filter(batch=batch, topic__startswith='Demo:').delete()

        now = timezone.now()
        today = now.date()

        # A. COMPLETED/ATTENDED CLASS (Yesterday)
        yesterday = today - timedelta(days=1)
        session_attended = ClassSession.objects.create(
            batch=batch,
            date=yesterday,
            start_time=time(10, 0),
            end_time=time(11, 0),
            topic='Demo: Attended Class (Green)',
            status='completed',
            tutor=user # placeholder tutor
        )
        Attendance.objects.get_or_create(user=user, class_session=session_attended)
        self.stdout.write(self.style.SUCCESS(f"Created Attended Class on {yesterday}"))

        # B. MISSED CLASS (2 days ago)
        two_days_ago = today - timedelta(days=2)
        ClassSession.objects.create(
            batch=batch,
            date=two_days_ago,
            start_time=time(14, 0),
            end_time=time(15, 0),
            topic='Demo: Missed Class (Red)',
            status='completed', # Logic: Past class + no attendance = Missed
            tutor=user
        )
        self.stdout.write(self.style.SUCCESS(f"Created Missed Class on {two_days_ago}"))

        # C. UPCOMING CLASS (Tomorrow)
        tomorrow = today + timedelta(days=1)
        ClassSession.objects.create(
            batch=batch,
            date=tomorrow,
            start_time=time(9, 0),
            end_time=time(10, 0),
            topic='Demo: Upcoming Class (Blue)',
            status='scheduled',
            tutor=user,
            meeting_link='https://meet.google.com/demo-link'
        )
        self.stdout.write(self.style.SUCCESS(f"Created Upcoming Class on {tomorrow}"))

        self.stdout.write(self.style.SUCCESS("Successfully generated dummy data for visualization."))
