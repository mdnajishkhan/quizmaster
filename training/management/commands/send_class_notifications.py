from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from training.models import ClassSchedule, Enrollment
from datetime import timedelta

class Command(BaseCommand):
    help = 'Send email reminders for upcoming classes (3 hours and 30 minutes before)'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        self.stdout.write(f"Checking for classes at {now}")

        # --- 3 HOUR REMINDER ---
        # Trigger ONLY if class is <= 3 hours away (but not too late, e.g. > 1 hr)
        start_range_early = now + timedelta(hours=3)
        
        # We look for classes starting anytime between NOW and 3 hours from now
        # But we rely on the 'reminder_6hr_sent' flag (repurposed for 3hr) to ensure we do it only once.
        
        classes_early = ClassSchedule.objects.filter(
            start_time__gte=now + timedelta(hours=1), # Don't send early reminder if it's already < 1 hour away
            start_time__lte=start_range_early,
            reminder_6hr_sent=False # Using existing DB field
        )

        for schedule in classes_early:
            self.send_notifications(schedule, '3hr')
            schedule.reminder_6hr_sent = True
            schedule.save()
            self.stdout.write(self.style.SUCCESS(f"Sent 3hr reminders for {schedule}"))

        # --- 30 MINUTE REMINDER ---
        # Trigger ONLY if class is <= 30 minutes away
        start_range_30m = now + timedelta(minutes=30)

        classes_30min = ClassSchedule.objects.filter(
            start_time__gte=now,
            start_time__lte=start_range_30m,
            reminder_30min_sent=False
        )

        for schedule in classes_30min:
            self.send_notifications(schedule, '30min')
            schedule.reminder_30min_sent = True
            schedule.save()
            self.stdout.write(self.style.SUCCESS(f"Sent 30min reminders for {schedule}"))

    def send_notifications(self, schedule, type_code):
        from django.urls import reverse
        batch = schedule.batch
        self.stdout.write(f"Processing batch: {batch}")
        
        # Find active enrollments
        active_enrollments = Enrollment.objects.filter(
            batch=batch,
            expires_at__gte=timezone.now()
        )
        self.stdout.write(f"Found {active_enrollments.count()} active enrollments.")
        
        # Get unique users
        users = set(e.user for e in active_enrollments if e.user.email)
        self.stdout.write(f"Found {len(users)} unique users with emails.")
        
        if not users:
            self.stdout.write(f"No active students found for {schedule}")
            return

        # Use the 6hr template but we'll update its content to be generic or 3hr specific
        template_name = 'training/emails/class_reminder_6hr.html' if type_code == '3hr' else 'training/emails/class_reminder_30min.html'
        
        # Calculate time remaining string
        now = timezone.now()
        diff = schedule.start_time - now
        minutes_left = int(diff.total_seconds() / 60)
        
        if minutes_left <= 0:
            time_str = "now"
            subject = f"Class Starting Now: {schedule.topic}"
        elif type_code == '3hr':
             time_str = "3 hours"
             subject = f"Reminder: Class in 3 Hours - {schedule.topic}"
        else:
             time_str = f"{minutes_left} minutes"
             subject = f"Class Starting in {minutes_left} Mins: {schedule.topic}"

        # Determine Dashboard Link (Absolute URL)
        if settings.DEBUG:
            base_url = "http://127.0.0.1:8000"
        else:
            base_url = "https://quizmaster.tgaystechnology.com"
        
        dashboard_link = f"{base_url}{reverse('training_program')}"

        for user in users:
            self.stdout.write(f"Attempting to send to: '{user.email}' (User: {user.username})")
            try:
                html_message = render_to_string(template_name, {
                    'user': user,
                    'class_schedule': schedule,
                    'time_str': time_str,
                    'dashboard_link': dashboard_link,
                })
                
                plain_message = f"""
Hello {user.first_name},

Your class is starting in about {time_str}.

Topic: {schedule.topic}
Start Time: {schedule.start_time.strftime('%I:%M %p')}

Link: {dashboard_link}

See you there!
"""
                
                sent_count = send_mail(
                    subject,
                    plain_message,
                    settings.EMAIL_HOST_USER, # From email
                    [user.email], # To email
                    html_message=html_message,
                    fail_silently=False
                )
                self.stdout.write(self.style.SUCCESS(f"Send_mail returned: {sent_count}"))
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to send email to {user.email}: {e}"))
