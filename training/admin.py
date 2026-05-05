from django.contrib import admin
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.contrib.auth.models import User
from django.utils import timezone
import datetime

# Import Original Models (for those staying in "Training Management")
from .models import (
    Workshop, Batch, BatchSchedule, ClassSession, SpecialClass, Attendance, Resource,
    Holiday,
    # These base models are needed for logic or inlines, even if not registered directly
    Coupon, Enrollment, WorkshopPackage, ContactQuery,
    HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ
)

# Import Proxy Models (for Sales and Content sections)
from .models_proxy import (
    SalesCoupon, SalesEnrollment, SalesInquiry, SalesPackage,
    ContentHero, ContentAbout, ContentClassType, ContentTestimonial, ContentGallery, ContentFAQ
)

from .tasks import send_new_coupon_email # Moved import here if used

# ========================================================
# SECTION 1: TRAINING SALES & ENROLLMENTS (Proxy App)
# ========================================================

@admin.register(SalesPackage)
class WorkshopPackageAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SalesPackage.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name', 'price', 'duration_days')
    list_display_links = ('serial_number', 'name')
    ordering = ['-id']

@admin.register(SalesInquiry)
class ContactQueryAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SalesInquiry.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name', 'email', 'subject', 'created_at', 'is_resolved')
    list_display_links = ('serial_number', 'name')
    ordering = ['-id']
    list_filter = ('is_resolved', 'created_at')
    actions = ['mark_as_resolved']
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)

@admin.register(SalesCoupon)
class CouponAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SalesCoupon.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'code', 'batch', 'assigned_to', 'workshop_package', 'is_used')
    list_display_links = ('serial_number', 'code')
    ordering = ['-id']
    list_filter = ('is_used', 'batch')
    search_fields = ('code', 'assigned_to__email', 'assigned_to__username')
    readonly_fields = ('code',)
    
    fields = (
        ('workshop_package', 'batch'),
        'assigned_to',
        'valid_days',
        ('enrollment_valid_from', 'enrollment_valid_until'),
        ('payment_amount', 'payment_date'),
        'includes_special_access',
        'is_used',
        'code'
    )
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "assigned_to":
            # Show ONLY Students (Not Superuser, Not Tutor)
            kwargs["queryset"] = User.objects.filter(is_superuser=False).exclude(groups__name='Tutor').distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    class Media:
        js = ('admin/js/vendor/jquery/jquery.js', 'admin/js/jquery.init.js', 'training/js/coupon_admin.js')

    def save_model(self, request, obj, form, change):
        if not obj.pk:
             if obj.workshop_package:
                 if not obj.valid_days: obj.valid_days = obj.workshop_package.duration_days
                 if not obj.payment_amount: obj.payment_amount = obj.workshop_package.price
             
             if not obj.payment_date: obj.payment_date = timezone.now().date()
             if not obj.enrollment_valid_from: obj.enrollment_valid_from = obj.payment_date
             if not obj.enrollment_valid_until and obj.valid_days:
                 from datetime import timedelta
                 obj.enrollment_valid_until = obj.enrollment_valid_from + timedelta(days=obj.valid_days)
        super().save_model(request, obj, form, change)

        # --- EMAIL NOTIFICATION LOGIC ---
        should_send = False
        if obj.assigned_to and not obj.is_used:
             if not change:
                 should_send = True
             else:
                 if 'assigned_to' in form.changed_data:
                     should_send = True
        
        if should_send:
             sent = send_new_coupon_email(obj.id)
             if sent:
                 self.message_user(request, f"Email sent to {obj.assigned_to.email} with Coupon Code.", level=messages.SUCCESS)
             else:
                 self.message_user(request, "Failed to send email. Check logs.", level=messages.WARNING)

@admin.register(SalesEnrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SalesEnrollment.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'user', 'batch', 'enrolled_at', 'expires_at', 'is_active')
    list_display_links = ('serial_number', 'user')
    ordering = ['-id']
    list_filter = ('batch',)
    search_fields = ('user__username', 'user__email')


# ========================================================
# SECTION 2: WEBSITE CONTENT (Proxy App)
# ========================================================

@admin.register(ContentHero)
class HeroSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentHero.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title', 'is_active')
    list_display_links = ('serial_number', 'title')
    ordering = ['-id']
    list_editable = ('is_active',)

@admin.register(ContentAbout)
class AboutSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentAbout.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'instructor_name', 'is_active')
    list_display_links = ('serial_number', 'instructor_name')
    ordering = ['-id']
    list_editable = ('is_active',)

@admin.register(ContentClassType)
class ClassTypeAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentClassType.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title', 'price', 'order', 'is_active')
    list_display_links = ('serial_number', 'title')
    ordering = ['-id']
    list_editable = ('order', 'is_active')

@admin.register(ContentTestimonial)
class TestimonialAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentTestimonial.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'student_name', 'role', 'is_active')
    list_display_links = ('serial_number', 'student_name')
    ordering = ['-id']

@admin.register(ContentGallery)
class GalleryImageAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentGallery.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'caption', 'order', 'image', 'is_active')
    list_display_links = ('serial_number', 'caption')
    ordering = ['-id']

@admin.register(ContentFAQ)
class FAQAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ContentFAQ.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'question', 'order', 'is_active')
    list_display_links = ('serial_number', 'question')
    ordering = ['-id']


# ========================================================
# SECTION 3: TRAINING MANAGEMENT (Original App)
# ========================================================

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(Holiday.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name', 'date', 'created_at')
    list_display_links = ('serial_number', 'name')
    ordering = ['-id']

class BatchScheduleInline(admin.TabularInline):
    model = BatchSchedule
    extra = 1
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tutor":
            kwargs["queryset"] = User.objects.filter(Q(groups__name='Tutor') | Q(is_superuser=True)).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

class ResourceBatchInline(admin.TabularInline):
    model = Resource
    extra = 1

@admin.register(Workshop)
class WorkshopAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(Workshop.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title', 'created_at')
    list_display_links = ('serial_number', 'title')
    ordering = ['-id']

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(Batch.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name', 'workshop', 'is_personal', 'start_date', 'end_date')
    list_display_links = ('serial_number', 'name')
    ordering = ['-id']
    list_filter = ('workshop', 'is_personal')
    inlines = [BatchScheduleInline, ResourceBatchInline]

@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(ClassSession.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'batch', 'date', 'status')
    list_display_links = ('serial_number', 'batch')
    ordering = ['-id']
    list_filter = ('batch', 'status')
    
    fields = (
        'batch',
        ('date', 'start_time'), # New Date time
        ('status', 'tutor'),
        # Optional advanced fields in collapsed section?
        'topic', 
        'meeting_link',
        'original_date' # Critical for rescheduling logic
    )
    
    readonly_fields = ('end_time',) # Hide from input, calc automatically

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['date'].label = "Class Date (New if Rescheduling)"
        form.base_fields['start_time'].label = "Start Time"
        form.base_fields['original_date'].help_text = "Required ONLY if Rescheduling: The original date of the recurring class you are moving."
        return form

    def save_model(self, request, obj, form, change):
        # Auto-calculate end_time (default +1 hr) if not present
        if obj.start_time and not obj.end_time:
             import datetime
             dt = datetime.datetime.combine(datetime.date.today(), obj.start_time)
             obj.end_time = (dt + datetime.timedelta(hours=1)).time()
        
        # If topic missing, default to "Rescheduled Class" or Batch Name
        if not obj.topic:
             obj.topic = f"{obj.batch.name} (Session)"
             
        super().save_model(request, obj, form, change)

@admin.register(SpecialClass)
class SpecialClassAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SpecialClass.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title', 'scheduling_type', 'get_schedule', 'tutor')
    list_display_links = ('serial_number', 'title')
    ordering = ['-id']
    list_filter = ('scheduling_type', 'tutor')
    filter_horizontal = ('allowed_students',)
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('title', 'description', 'tutor', 'meeting_link', 'allowed_students')
        }),
        ('Scheduling Mode', {
            'fields': ('scheduling_type',),
            'description': "Select 'One Time' for specific dates, or 'Recurring' for weekly classes."
        }),
        ('Option 1: One Time Class', {
            'fields': ('start_datetime', 'end_datetime'),
            'classes': ('collapse',),
            'description': "Fill these only if Scheduling Type is 'One Time'"
        }),
        ('Option 2: Recurring Class', {
            'fields': ('day_of_week', 'start_time', 'end_time'),
            'classes': ('collapse',),
            'description': "Fill these only if Scheduling Type is 'Recurring'. Limits will clarify based on Student Package validity."
        }),
    )
    
    def get_schedule(self, obj):
        if obj.scheduling_type == 'recurring':
            return f"{obj.get_day_of_week_display()}s (Weekly)"
        return obj.start_datetime
    get_schedule.short_description = "Schedule"
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tutor":
            kwargs["queryset"] = User.objects.filter(Q(groups__name='Tutor') | Q(is_superuser=True)).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(Attendance.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'user', 'class_session', 'joined_at')
    list_display_links = ('serial_number', 'user')
    ordering = ['-id']
