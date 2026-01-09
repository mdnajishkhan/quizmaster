from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Workshop(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='training/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Training Program"
        verbose_name_plural = "Training Programs"


class Batch(models.Model):
    workshop = models.ForeignKey(Workshop, related_name='batches', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="e.g. 'January 2025 Batch'")
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Batches"

    def __str__(self):
        return f"{self.workshop.title} - {self.name}"


class ClassSchedule(models.Model):
    batch = models.ForeignKey(Batch, related_name='classes', on_delete=models.CASCADE)
    topic = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_time = models.DateTimeField(null=True, blank=True, help_text="Class start time")
    end_time = models.DateTimeField(null=True, blank=True, help_text="Class end time")
    meeting_link = models.URLField(max_length=500, blank=True, null=True, help_text="Zoom/Google Meet link")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        time_str = self.start_time.strftime('%Y-%m-%d %H:%M') if self.start_time else "TBA"
        return f"{self.topic} ({time_str})"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    batch = models.ForeignKey(Batch, related_name='coupons', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, related_name='coupons', on_delete=models.SET_NULL, null=True, blank=True, help_text="Student for whom this coupon is generated")
    valid_days = models.PositiveIntegerField(default=30, blank=True, null=True, help_text="Duration in days (if specific dates below are not set)")
    enrollment_valid_from = models.DateField(null=True, blank=True, help_text="Start of access (overrides valid_days)")
    enrollment_valid_until = models.DateField(null=True, blank=True, help_text="End of access (overrides valid_days)")
    
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount paid in INR")
    payment_date = models.DateField(null=True, blank=True, help_text="Date of payment")
    next_payment_date = models.DateField(null=True, blank=True, help_text="Next installment/renewal date")

    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
             # Generate a simple 12-char separate code e.g. "PYTH-7A8B-9C0D"
             # For simplicity, using uuid hex
             self.code = str(uuid.uuid4()).upper()[:12]
        
        super().save(*args, **kwargs)

        # --- AUTO-SYNC ENROLLMENT EXPIRY ---
        # If Admin edits a used coupon (e.g. extending date), update the Enrollment
        if self.assigned_to and self.batch:
            # Re-calculate max expiry from ALL coupons for this user/batch
            # This ensures if we fix a date, the enrollment reflects the best valid date
            
            # Find related enrollment
            enrollment = Enrollment.objects.filter(user=self.assigned_to, batch=self.batch).first()
            if enrollment:
                all_coupons = Coupon.objects.filter(assigned_to=self.assigned_to, batch=self.batch)
                max_date = None
                
                for c in all_coupons:
                    if c.enrollment_valid_until:
                        # Convert Date to DateTime (End of Day)
                        from datetime import datetime, time
                        dt = datetime.combine(c.enrollment_valid_until, time.max)
                        dt = datetime.combine(c.enrollment_valid_until, time.max)
                        # USE_TZ=False, so keep naive
                        # dt = timezone.make_aware(dt)
                        
                        if not max_date or dt > max_date:
                            max_date = dt
                
                # If we found a valid max date from coupons, sync the enrollment
                if max_date:
                    enrollment.expires_at = max_date
                    enrollment.save()

    def __str__(self):
        return f"{self.code} ({self.batch.name})"


class Enrollment(models.Model):
    user = models.ForeignKey(User, related_name='enrollments', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, related_name='enrollments', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When user access to this batch expires")
    
    class Meta:
        unique_together = ('user', 'batch')

    def is_active(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.user.username} -> {self.batch.name}"


class Attendance(models.Model):
    user = models.ForeignKey(User, related_name='attendances', on_delete=models.CASCADE)
    class_schedule = models.ForeignKey(ClassSchedule, related_name='attendances', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'class_schedule')

    def __str__(self):
        return f"{self.user.username} joined {self.class_schedule.topic}"
