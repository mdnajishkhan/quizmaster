from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from django.core.exceptions import ValidationError

# --- EXISTING MODELS ---

class Workshop(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='training/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Program / Subject"
        verbose_name_plural = "Programs / Subjects"


class Batch(models.Model):
    workshop = models.ForeignKey(Workshop, related_name='batches', on_delete=models.CASCADE)
    name = models.CharField(max_length=100, help_text="e.g. 'January 2025 Batch' or 'John Doe Private'")
    
    # Batch might technically have a start/end dates for administrative purposes, 
    # but the student's access is controlled by their Enrollment/Coupon validity.
    # We keep these as optional purely for metadata.
    # Batch might technically have a start/end dates for administrative purposes, 
    # but the student's access is controlled by their Enrollment/Coupon validity.
    # We keep these as optional purely for metadata.
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Flag to distinguish Personal (1-on-1) batches from Group batches
    is_personal = models.BooleanField(default=False, help_text="Check if this batch is for 1-on-1 Personal Classes")

    class Meta:
        verbose_name = "Batch"
        verbose_name_plural = "Batches (Groups & Personal)"

    def __str__(self):
        return f"{self.workshop.title} - {self.name}"


class BatchSchedule(models.Model):
    """
    Defines the RECURRING pattern for a batch.
    e.g. Mondays at 6:00 PM.
    """
    DAY_CHOICES = [
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
    ]

    batch = models.ForeignKey(Batch, related_name='schedules', on_delete=models.CASCADE)
    day_of_week = models.IntegerField(choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    tutor = models.ForeignKey(User, related_name='teaching_schedules', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.CharField(max_length=255, default="Class Session")
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    
    def __str__(self):
        return f"{self.get_day_of_week_display()} {self.start_time.strftime('%H:%M')} - {self.batch.name}"
    
    class Meta:
        ordering = ['day_of_week', 'start_time']


class ClassSession(models.Model):
    """
    Represents EXCEPTIONS or CONCRETE INSTANCES (if needed for attendance/rescheduling).
    Logic:
    - Dynamic Calendar shows BatchSchedule patterns.
    - If a ClassSession exists for a specific Date+BatchSchedule, it OVERRIDES the pattern.
      (e.g. Rescheduled from 6pm to 8pm, or Cancelled).
    - Can also represent 'Extra Classes' not in pattern.
    """
    STATUS_CHOICES = [
        ('scheduled', 'Scheduled (Manual)'),
        ('rescheduled', 'Rescheduled'),
        ('cancelled', 'Cancelled'),
        ('completed', 'Completed'),
    ]

    batch = models.ForeignKey(Batch, related_name='sessions', on_delete=models.CASCADE)
    # Optional link to the pattern it overrides
    pattern_ref = models.ForeignKey(BatchSchedule, null=True, blank=True, on_delete=models.SET_NULL, help_text="If overriding a pattern class")
    
    date = models.DateField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    
    tutor = models.ForeignKey(User, related_name='session_tutor', on_delete=models.SET_NULL, null=True, blank=True)
    topic = models.CharField(max_length=255)
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='scheduled')
    
    # If this is a rescheduling of a specific date from the pattern
    original_date = models.DateField(null=True, blank=True, help_text="The original date of the class if rescheduled")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.topic} on {self.date} ({self.status})"

    class Meta:
        verbose_name = "Reschedule / Extra Class"
        verbose_name_plural = "Reschedule / Extra Classes"


class SpecialClass(models.Model):
    """
    One-off or special events that students can be granted access to.
    """
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    tutor = models.ForeignKey(User, related_name='special_classes', on_delete=models.SET_NULL, null=True, blank=True)
    meeting_link = models.URLField(max_length=500, blank=True, null=True)
    
    # Access Control logic could be here or via a join table.
    # User requested a dropdown to see 'access'.
    allowed_students = models.ManyToManyField(User, related_name='special_class_access', blank=True)
    
    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "Special Classes"

# Re-using previous package models with minor tweaks if needed

class WorkshopPackage(models.Model):
    name = models.CharField(max_length=100, help_text="e.g. 'Allied', 'Pro', 'Supreme', 'Monthly', 'Yearly'")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.PositiveIntegerField(default=30, help_text="30=1 Month, 90=3 Months, 365=1 Year")
    description = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.name} (₹{self.price})"

    class Meta:
        verbose_name = "Pricing Package"
        verbose_name_plural = "Pricing Packages"


class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, editable=False)
    workshop_package = models.ForeignKey(WorkshopPackage, on_delete=models.SET_NULL, null=True, blank=True)
    batch = models.ForeignKey(Batch, related_name='coupons', on_delete=models.CASCADE)
    assigned_to = models.ForeignKey(User, related_name='coupons', on_delete=models.SET_NULL, null=True, blank=True, help_text="Student for whom this coupon is generated")
    valid_days = models.PositiveIntegerField(default=30, blank=True, null=True, help_text="Duration in days")
    enrollment_valid_from = models.DateField(null=True, blank=True)
    enrollment_valid_until = models.DateField(null=True, blank=True)
    
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount paid in INR")
    payment_date = models.DateField(null=True, blank=True, help_text="Date of payment")
    
    # Explicit override for Special Access
    includes_special_access = models.BooleanField(default=False, help_text="Check to grant Special Class access to this student/coupon")
    
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.code:
             self.code = str(uuid.uuid4()).upper()[:12]
        
        # Auto-set from Package if new and not manually set
        if self.workshop_package and self.pk is None:
             # Only if user hasn't explicitly set it (default is False, so hard to distinguish)
             # But if package has it, we default to True. 
             # Admin can uncheck it if they want (but we need to set it before super.save if we want UI default?)
             # Actually, simpler: If package has it, set it to True. Admin changes it in Form clean usually.
             # Here we just enforce logic if needed.
             pass

        super().save(*args, **kwargs)

        # --- AUTO-SYNC ENROLLMENT EXPIRY & ACCESS ---
        if self.assigned_to and self.batch:
            # Check if enrollment exists
            enrollment = Enrollment.objects.filter(user=self.assigned_to, batch=self.batch).first()
            if enrollment:
                # Recalculate max expiry from ALL coupons
                all_coupons = Coupon.objects.filter(assigned_to=self.assigned_to, batch=self.batch)
                max_date = None
                grant_special = False
                
                for c in all_coupons:
                    if c.includes_special_access:
                        grant_special = True
                        
                    if c.enrollment_valid_until:
                        from datetime import datetime, time
                        dt = datetime.combine(c.enrollment_valid_until, time.max)
                        if not max_date or dt > max_date:
                            max_date = dt # Keep naive or make aware later
                
                if max_date:
                    enrollment.expires_at = max_date
                
                enrollment.has_special_access = grant_special
                enrollment.save()

    def __str__(self):
        return f"{self.code} ({self.batch.name})"

    class Meta:
        verbose_name = "Coupon / Assign Student"
        verbose_name_plural = "Coupons / Assign Student"


class Enrollment(models.Model):
    user = models.ForeignKey(User, related_name='enrollments', on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, related_name='enrollments', on_delete=models.CASCADE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(help_text="When user access to this batch expires")
    has_special_access = models.BooleanField(default=False, help_text="Can access Special Classes")
    
    # Expiry Reminders
    expiry_3d_sent = models.BooleanField(default=False)
    expiry_1d_sent = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('user', 'batch')
        verbose_name_plural = "Active Enrollments"

    def is_active(self):
        return self.expires_at > timezone.now()

    def __str__(self):
        return f"{self.user.username} -> {self.batch.name}"


class Attendance(models.Model):
    user = models.ForeignKey(User, related_name='attendances', on_delete=models.CASCADE)
    
    # Attendance can link to a Session OR a Date+BatchSchedule pattern
    # Simplest: Attendance links to ClassSession (created on fly if needed?)
    # OR: Generic link?
    # Let's link to ClassSession. Means we need to create a Session record when someone joins a Pattern class? 
    # Yes, "Lazy Creation" of ClassSession on join is a good pattern.
    class_session = models.ForeignKey(ClassSession, related_name='attendances', on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'class_session')
        verbose_name_plural = "Student Attendance"

    def __str__(self):
        return f"{self.user.username} joined {self.class_session}"


class Resource(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='resources', null=True, blank=True)
    # Removed direct link to schedule since schedules are now patterns. 
    # Resources are usually Batch-wide or Topic-wide.
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to='training/resources/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Class Resource"
        verbose_name_plural = "Class Resources"


# --- LANDING PAGE MODELS (Unchanged) ---
class HeroSection(models.Model):
    title = models.CharField(max_length=255, default="Master Your Sound")
    subtitle = models.TextField(blank=True, default="Learn music from the best. Join our exclusive online classes.")
    background_image = models.ImageField(upload_to='landing/hero/', help_text="High resolution background image")
    cta_text = models.CharField(max_length=50, default="Join Now")
    cta_link = models.CharField(max_length=255, default="#contact", help_text="Link for the CTA button")
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.title
    class Meta: verbose_name = "Landing - Hero Section"

class AboutSection(models.Model):
    instructor_name = models.CharField(max_length=100, default="Master Instructor")
    bio = models.TextField()
    image = models.ImageField(upload_to='landing/instructor/', blank=True, null=True)
    experience_years = models.CharField(max_length=20, default="10+")
    students_trained = models.CharField(max_length=20, default="500+")
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.instructor_name
    class Meta: verbose_name = "Landing - About Section"

class ClassType(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    price = models.CharField(max_length=50, blank=True)
    image = models.ImageField(upload_to='landing/classes/', blank=True, null=True)
    icon = models.CharField(max_length=50, default="🎵")
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ['order']; verbose_name = "Landing - Class Type"
    def __str__(self): return self.title

class Testimonial(models.Model):
    student_name = models.CharField(max_length=100)
    quote = models.TextField()
    student_image = models.ImageField(upload_to='landing/testimonials/', blank=True, null=True)
    role = models.CharField(max_length=100, blank=True, default="Student")
    is_active = models.BooleanField(default=True)
    def __str__(self): return self.student_name
    class Meta: verbose_name = "Landing - Testimonial"

class GalleryImage(models.Model):
    caption = models.CharField(max_length=100, blank=True)
    image = models.ImageField(upload_to='landing/gallery/')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ['order']; verbose_name = "Landing - Gallery Image"

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    class Meta: ordering = ['order']; verbose_name = "Landing - FAQ"

class ContactQuery(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=200, default="General Inquiry")
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)
    class Meta: 
        ordering = ['-created_at']
        verbose_name = "Website Inquiry"
        verbose_name_plural = "Website Inquiries"
    def __str__(self): return f"{self.name} - {self.subject}"

class Holiday(models.Model):
    name = models.CharField(max_length=200, help_text="e.g. 'Eid-ul-Fitr', 'Diwali'")
    date = models.DateField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.date})"
