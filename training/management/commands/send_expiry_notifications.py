from django.core.management.base import BaseCommand
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from training.models import Enrollment
from datetime import timedelta
from django.urls import reverse

class Command(BaseCommand):
    help = 'Send email reminders for package expiry (3 days and 1 day before)'

    def handle(self, *args, **kwargs):
        now = timezone.now()
        today = now.date()
        self.stdout.write(f"Checking for package expiries at {now}")

        # Determine Dashboard Link (Absolute URL)
        if settings.DEBUG:
            base_url = "http://127.0.0.1:8000"
        else:
            base_url = "https://platform.recgetupmusic.com"
        
        dashboard_link = f"{base_url}{reverse('training_program')}"

        # --- 1. CHECK FOR 3-DAY EXPIRY ---
        target_3d = today + timedelta(days=3)
        enrollments_3d = Enrollment.objects.filter(
            expires_at__date=target_3d,
            expiry_3d_sent=False
        ).select_related('user', 'batch')

        for enr in enrollments_3d:
            if enr.user.email:
                self.send_expiry_email(enr, 3, dashboard_link)
                enr.expiry_3d_sent = True
                enr.save()
                self.stdout.write(self.style.SUCCESS(f"Sent 3-day expiry reminder to {enr.user.email}"))

        # --- 2. CHECK FOR 1-DAY EXPIRY ---
        target_1d = today + timedelta(days=1)
        enrollments_1d = Enrollment.objects.filter(
            expires_at__date=target_1d,
            expiry_1d_sent=False
        ).select_related('user', 'batch')

        for enr in enrollments_1d:
            if enr.user.email:
                self.send_expiry_email(enr, 1, dashboard_link)
                enr.expiry_1d_sent = True
                enr.save()
                self.stdout.write(self.style.SUCCESS(f"Sent 1-day expiry reminder to {enr.user.email}"))

    def send_expiry_email(self, enrollment, days_left, dashboard_link):
        subject = f"Action Required: Your access expires in {days_left} day{'s' if days_left > 1 else ''}"
        
        try:
            html_message = render_to_string('training/emails/package_expiry.html', {
                'user': enrollment.user,
                'batch_name': enrollment.batch.name,
                'days_left': days_left,
                'dashboard_link': dashboard_link,
            })
            
            plain_message = (
                f"Hello {enrollment.user.first_name},\n\n"
                f"Your access to {enrollment.batch.name} will expire in {days_left} day{'s' if days_left > 1 else ''}.\n\n"
                f"Please renew your package from your dashboard: {dashboard_link}\n\n"
                f"Note: If you have already upgraded or renewed your package, please ignore this message."
            )
            
            send_mail(
                subject,
                plain_message,
                settings.EMAIL_HOST_USER,
                [enrollment.user.email],
                html_message=html_message,
                fail_silently=False
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to send expiry email to {enrollment.user.email}: {e}"))
