from django.contrib import admin
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from .models import Workshop, Batch, ClassSchedule, Coupon, Enrollment, Attendance
from django.contrib import messages

class ClassScheduleInline(admin.TabularInline):
    model = ClassSchedule
    extra = 1

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'workshop', 'start_date', 'end_date')
    list_filter = ('workshop',)
    inlines = [ClassScheduleInline]

@admin.register(ClassSchedule)
class ClassScheduleAdmin(admin.ModelAdmin):
    list_display = ('topic', 'batch', 'start_time', 'end_time')
    list_filter = ('batch', 'start_time')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'batch', 'assigned_to', 'enrollment_valid_until', 'payment_date', 'is_used')
    list_filter = ('is_used', 'batch')
    search_fields = ('code', 'assigned_to__email', 'assigned_to__username')
    readonly_fields = ('code',)
    
    # Organize fields: Group related dates together
    fields = (
        ('batch', 'assigned_to'),
        'valid_days',
        ('enrollment_valid_from', 'enrollment_valid_until'),
        ('payment_amount', 'payment_date'),
        'is_used',
        'code'
    )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Make enrollment_valid_until readonly in the UI (but still submittable)
        if 'enrollment_valid_until' in form.base_fields:
            form.base_fields['enrollment_valid_until'].widget.attrs['readonly'] = True
            form.base_fields['enrollment_valid_until'].widget.attrs['style'] = 'background-color: #f0f0f0; cursor: not-allowed;'
        return form

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None
        
        # Auto-set payment information if new
        if is_new:
             if not obj.payment_date:
                 obj.payment_date = timezone.now().date()
             
             if not obj.enrollment_valid_from:
                 obj.enrollment_valid_from = obj.payment_date
            
             # Calculate End Date based on valid_days if not set manually
             if not obj.enrollment_valid_until and obj.valid_days:
                 from datetime import timedelta
                 obj.enrollment_valid_until = obj.enrollment_valid_from + timedelta(days=obj.valid_days)
                 
                 # Rough logic for Next Payment Date (e.g. 1 month later)
                 if not obj.next_payment_date:
                     # e.g., if valid for > 30 days, maybe set next payment in 30 days
                     # or just leave it empty if full payment is done.
                     # For now, let's auto-set next payment to 30 days if valid_days > 45
                     pass 

        super().save_model(request, obj, form, change)
        
        if is_new and obj.assigned_to:
            try:
                self.send_coupon_email(obj)
                messages.success(request, f"Coupon generated and emailed to {obj.assigned_to.email}!")
            except Exception as e:
                messages.warning(request, f"Coupon generated but email failed: {e}")

    class Media:
        js = ('training/js/coupon_admin.js',)

    def send_coupon_email(self, coupon):
        subject = f"Your Access Code for {coupon.batch.workshop.title}"
        
        # Helper to get domain (assuming localhost for dev, should be dynamic in prod)
        domain = "127.0.0.1:8000" 
        
        html_message = render_to_string('training/emails/coupon_email.html', {
            'user': coupon.assigned_to,
            'coupon': coupon,
            'code': coupon.code,
            'batch': coupon.batch,
            'valid_days': coupon.valid_days,
            'domain': domain,
        })
        
        plain_message = f"""
Hello {coupon.assigned_to.first_name},

You have been granted access to {coupon.batch.workshop.title} ({coupon.batch.name}).
Your access code is: {coupon.code}

Redeem it here: http://{domain}/training-program/
"""
        
        send_mail(
            subject,
            plain_message,
            settings.EMAIL_HOST_USER,
            [coupon.assigned_to.email],
            fail_silently=False,
            html_message=html_message
        )

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'batch', 'enrolled_at', 'expires_at', 'is_active')
    list_filter = ('batch',)
    search_fields = ('user__username', 'user__email')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_schedule', 'joined_at')
    list_filter = ('class_schedule__batch',)
