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

        # Determine Dashboard Link (Absolute URL)
        if settings.DEBUG:
            base_url = "http://127.0.0.1:8000"
        else:
            base_url = "https://platform.recgetupmusic.com"
        
        dashboard_link = f"{base_url}{reverse('training_program')}"
        
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

        # --- SEND TUTOR REMINDER (ONLY 30 MIN BEFORE) ---
        if type_code == '30min' and schedule.tutor and schedule.tutor.email:
            tutor = schedule.tutor
            self.stdout.write(f"Found assigned tutor: {tutor.username}")
            
            tutor_dashboard_link = f"{base_url}{reverse('tutor_dashboard')}"
            tutor_subject = f"Action Required: Class in {time_str} - {schedule.topic}"
            
            try:
                tutor_html = render_to_string('training/emails/tutor_class_reminder.html', {
                    'user': tutor,
                    'class_schedule': schedule,
                    'time_str': time_str,
                    'dashboard_link': tutor_dashboard_link,
                })
                
                tutor_text = f"Hello {tutor.first_name},\n\nYou have a class to teach in about {time_str}.\n\nTopic: {schedule.topic}\nBatch: {schedule.batch.name}\nStart Time: {schedule.start_time.strftime('%I:%M %p')}\n\nLink: {tutor_dashboard_link}\n\nPlease be on time."
                
                send_mail(
                    tutor_subject,
                    tutor_text,
                    settings.EMAIL_HOST_USER,
                    [tutor.email],
                    html_message=tutor_html,
                    fail_silently=False
                )
                self.stdout.write(self.style.SUCCESS(f"Sent Tutor reminder to {tutor.email}"))
            except Exception as e:
                 self.stderr.write(self.style.ERROR(f"Failed to send Tutor email: {e}"))

        # --- SEND STUDENT REMINDERS ---
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
            
        # Select Template
        template_name = 'training/emails/class_reminder_6hr.html' if type_code == '3hr' else 'training/emails/class_reminder_30min.html'

        # Exclude Tutors from Student List
        excluded_ids = self.check_is_tutor_bulk(list(users))
        
        for user in users:
            if user.id in excluded_ids or user.is_superuser:
                 self.stdout.write(f"Skipping tutor/admin: {user.username}")
                 continue

            self.stdout.write(f"Attempting to send to: '{user.email}' (User: {user.username})")
            try:
                html_message = render_to_string(template_name, {
                    'user': user,
                    'class_schedule': schedule,
                    'time_str': time_str,
                    'dashboard_link': dashboard_link,
                })
                
                plain_message = f"Hello {user.first_name},\n\nYour class is starting in about {time_str}.\n\nTopic: {schedule.topic}\nStart Time: {schedule.start_time.strftime('%I:%M %p')}\n\nLink: {dashboard_link}\n\nSee you there!"
                
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

    def check_is_tutor_bulk(self, users):
        """
        Identify which users in the provided list are effectively Tutors.
        Returns a set of User IDs that should be excluded.
        """
        if not users:
            return set()
            
        user_ids = [u.id for u in users]
        
        # 1. Check Group 'Tutor'
        from django.contrib.auth.models import User
        group_tutor_ids = set(User.objects.filter(id__in=user_ids, groups__name='Tutor').values_list('id', flat=True))
        
        # 2. Check if they are assigned as Tutor for ANY schedule
        schedule_tutor_ids = set(ClassSchedule.objects.filter(tutor_id__in=user_ids).values_list('tutor_id', flat=True))
        
        return group_tutor_ids | schedule_tutor_ids
