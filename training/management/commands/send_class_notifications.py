from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from training.models import ClassSession, Enrollment, SpecialClass
from django.contrib.auth.models import User
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Send email reminders for upcoming classes (3 hours and 30 minutes before)'

    def handle(self, *args, **kwargs):
        # Convert UTC 'now' to Local Time (IST) because database fields (date/time) are stored as naive local time.
        now = timezone.localtime(timezone.now()) 
        self.stdout.write(f"Checking for classes at {now} (Local Time)")

        # Define narrow windows (assuming cron runs every 5 minutes)
        # Window: [Target - 2.5 min, Target + 2.5 min]
        # This ensures we catch the event roughly once per cron cycle.
        
        # --- 3 HOUR REMINDER (Target: 180 mins) ---
        range_3h_start = now + timedelta(minutes=177) # 180 - 3
        range_3h_end = now + timedelta(minutes=183)   # 180 + 3
        
        self.check_and_send(range_3h_start, range_3h_end, '3hr', now)

        # --- 30 MINUTE REMINDER (Target: 30 mins) ---
        range_30m_start = now + timedelta(minutes=27) # 30 - 3
        range_30m_end = now + timedelta(minutes=33)   # 30 + 3
        
        self.check_and_send(range_30m_start, range_30m_end, '30min', now)

    def check_and_send(self, start_range, end_range, type_code, now):
        # 1. Regular Sessions
        classes = ClassSession.objects.filter(
            date=now.date(),
            start_time__gte=start_range.time(),
            start_time__lte=end_range.time(),
            status='scheduled'
        )
        for session in classes:
            self.send_notifications(session, type_code)
            self.stdout.write(self.style.SUCCESS(f"Sent {type_code} reminders for session: {session}"))

        # 2. Special Classes
        # One Time
        sc_ot = SpecialClass.objects.filter(
            scheduling_type='one_time',
            start_datetime__gte=start_range,
            start_datetime__lte=end_range
        )
        # Recurring
        sc_rec = SpecialClass.objects.filter(
            scheduling_type='recurring',
            day_of_week=now.weekday(),
            start_time__gte=start_range.time(),
            start_time__lte=end_range.time()
        )
        
        for sc in list(sc_ot) + list(sc_rec):
            self.send_notifications(sc, type_code, is_special=True)
            self.stdout.write(self.style.SUCCESS(f"Sent {type_code} reminders for special: {sc}"))

    def send_notifications(self, schedule, type_code, is_special=False):
        from django.urls import reverse
        
        # Common data extraction
        if is_special:
            topic = schedule.title
            tutor = schedule.tutor
            batch_name = "Special Class"
            # Get start_time
            if schedule.scheduling_type == 'one_time':
                start_time_val = schedule.start_datetime.time()
                date_val = schedule.start_datetime.date()
                start_dt = schedule.start_datetime
            else:
                start_time_val = schedule.start_time
                date_val = timezone.now().date()
                start_dt = timezone.make_aware(datetime.combine(date_val, start_time_val))
        else:
            topic = schedule.topic
            tutor = schedule.tutor
            batch_name = schedule.batch.name
            start_time_val = schedule.start_time
            date_val = schedule.date
            start_dt = timezone.make_aware(datetime.combine(date_val, start_time_val))

        # Determine Dashboard Link (Absolute URL)
        if settings.DEBUG:
            base_url = "http://127.0.0.1:8000"
        else:
            base_url = "https://recgetupmusic.in"
        
        dashboard_link = f"{base_url}{reverse('training_program')}"
        
        # Calculate time remaining string
        if type_code == '3hr':
             time_str = "3 hours"
             subject = f"Reminder: Class in 3 Hours - {topic}"
        else:
             time_str = "30 minutes"
             subject = f"Class Starting Soon: {topic}"

        # --- SEND TUTOR REMINDER (ONLY 30 MIN BEFORE) ---
        if type_code == '30min' and tutor and tutor.email:
            self.stdout.write(f"Processing Tutor Reminder for: {tutor.username}")
            
            tutor_dashboard_link = f"{base_url}{reverse('tutor_dashboard')}"
            tutor_subject = f"Action Required: Class in {time_str} - {topic}"
            
            try:
                tutor_html = render_to_string('training/emails/tutor_class_reminder.html', {
                    'user': tutor,
                    'class_schedule': schedule,
                    'is_special': is_special, 
                    'topic': topic,
                    'start_time': start_time_val,
                    'batch_name': batch_name,
                    'time_str': time_str,
                    'dashboard_link': tutor_dashboard_link,
                })
                
                tutor_text = f"Hello {tutor.first_name},\n\nYou have a class to teach in about {time_str}.\n\nTopic: {topic}\nType: {batch_name}\nStart Time: {start_time_val.strftime('%I:%M %p')}\n\nLink: {tutor_dashboard_link}\n\nPlease be on time."
                
                send_mail(
                    tutor_subject,
                    tutor_text,
                    settings.DEFAULT_FROM_EMAIL,
                    [tutor.email],
                    html_message=tutor_html,
                    fail_silently=False
                )
                self.stdout.write(self.style.SUCCESS(f"Sent Tutor reminder to {tutor.email}"))
            except Exception as e:
                 self.stderr.write(self.style.ERROR(f"Failed to send Tutor email: {e}"))

        # --- SEND STUDENT REMINDERS ---
        # Both 3hr and 30min triggers send to students
        users = set()
        
        try:
            if is_special:
                # 1. Explicitly allowed students (M2M)
                users.update(list(schedule.allowed_students.filter(email__isnull=False)))
                # 2. Students with Special Access pass
                users.update(list(User.objects.filter(
                    enrollments__has_special_access=True,
                    enrollments__expires_at__gte=timezone.now(),
                    email__isnull=False
                ).distinct()))
            else:
                # Regular Batch Students
                active_enrollments = Enrollment.objects.filter(
                    batch=schedule.batch,
                    expires_at__gte=timezone.now()
                ).select_related('user')
                
                # Filter locally to avoid complex joins if needed, or just iterate
                for enr in active_enrollments:
                    if enr.user.email:
                        users.add(enr.user)
                        
        except Exception as e:
             self.stderr.write(self.style.ERROR(f"Error fetching users: {e}"))
             return

        if not users:
            self.stdout.write(f"No active students found for {topic}")
            return
            
        # Select Template
        template_name = 'training/emails/class_reminder_6hr.html' if type_code == '3hr' else 'training/emails/class_reminder_30min.html'

        for user in users:
            # Skip if user is the tutor
            if tutor and user.id == tutor.id:
                 continue
            
            try:
                html_message = render_to_string(template_name, {
                    'user': user,
                    'class_schedule': schedule,
                    'is_special': is_special,
                    'topic': topic,
                    'start_time': start_dt,
                    'time_str': time_str,
                    'dashboard_link': dashboard_link,
                })
                
                plain_message = f"Hello {user.first_name},\n\nYour class is starting in about {time_str}.\n\nTopic: {topic}\nStart Time: {start_time_val.strftime('%I:%M %p')}\n\nLink: {dashboard_link}\n\nSee you there!"
                
                send_mail(
                    subject,
                    plain_message,
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    html_message=html_message,
                    fail_silently=False
                )
                self.stdout.write(f"Sent Student reminder to {user.email}")
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to send email to {user.email}: {e}"))
