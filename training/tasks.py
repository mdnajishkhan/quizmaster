from background_task import background
from django.core.mail import send_mail
from django.conf import settings

@background(schedule=0)
def send_contact_email_task(subject, message, recipient_list):
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            fail_silently=False
        )
        print(f"Successfully sent email to {recipient_list}")
    except Exception as e:
        print(f"Failed to send email to {recipient_list}: {e}")

# SYNC TASK (No Background) for reliability
def send_new_coupon_email(coupon_id):
    from .models import Coupon
    from django.template.loader import render_to_string
    from django.urls import reverse
    import datetime
    
    try:
        coupon = Coupon.objects.get(id=coupon_id)
        if not coupon.assigned_to or not coupon.assigned_to.email:
            print(f"Coupon {coupon_id} has no assigned user with email.")
            return

        user = coupon.assigned_to
        email = user.email
        
        # Context
        dashboard_link = "https://recgetupmusic.in/training/" 
        # Better to try reverse if possible, but context irrelevant of request
        # Just use generic link or what 
        context = {
            'user': user,
            'code': coupon.code,
            'batch_name': coupon.batch.name if coupon.batch else "Your Batch",
            'valid_until': coupon.enrollment_valid_until,
            'dashboard_link': "https://recgetupmusic.in" + "/training/" # Approximation
        }
        
        html_message = render_to_string('training/emails/coupon_new.html', context)
        subject = f"Your Access Code: {coupon.batch.name}"
        
        send_mail(
            subject=subject,
            message="Your access code is " + coupon.code,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False
        )
        print(f"Coupon Email sent to {email}")
        return True
    except Exception as e:
        print(f"Error sending coupon email: {e}")
        return False
