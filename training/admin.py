from django.contrib import admin
from django import forms
from django.contrib import messages
from django.db.models import Q
from django.shortcuts import render
from django.contrib.auth.models import User
from django.http import HttpResponseRedirect
import datetime

from .models import (
    Workshop, Batch, BatchSchedule, ClassSession, SpecialClass, Coupon, Enrollment, Attendance, Resource,
    HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ, ContactQuery,
    WorkshopPackage, Holiday
)
from django.contrib.admin import SimpleListFilter
from django.utils import timezone

@admin.register(WorkshopPackage)
class WorkshopPackageAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'duration_days')

@admin.register(Holiday)
class HolidayAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'created_at')
    list_filter = ('date',)
    ordering = ('-date',)

@admin.register(ContactQuery)
class ContactQueryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'created_at', 'is_resolved')
    list_filter = ('is_resolved', 'created_at')
    actions = ['mark_as_resolved']
    def mark_as_resolved(self, request, queryset):
        queryset.update(is_resolved=True)

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
    list_display = ('title', 'created_at')

@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('name', 'workshop', 'is_personal', 'start_date', 'end_date')
    list_filter = ('workshop', 'is_personal')
    inlines = [BatchScheduleInline, ResourceBatchInline]

@admin.register(ClassSession)
class ClassSessionAdmin(admin.ModelAdmin):
    list_display = ('batch', 'date', 'status') # Simplified list
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
        # Maybe customize label for date/start_time to be 'New Date/Time'
        form.base_fields['date'].label = "Class Date (New if Rescheduling)"
        form.base_fields['start_time'].label = "Start Time"
        form.base_fields['original_date'].help_text = "Required ONLY if Rescheduling: The original date of the recurring class you are moving."
        return form

    def save_model(self, request, obj, form, change):
        # Auto-calculate end_time (default +1 hr) if not present
        if obj.start_time and not obj.end_time:
             # A bit of hack to add 1 hour to time object
             import datetime
             dt = datetime.datetime.combine(datetime.date.today(), obj.start_time)
             obj.end_time = (dt + datetime.timedelta(hours=1)).time()
        
        # If topic missing, default to "Rescheduled Class" or Batch Name
        if not obj.topic:
             obj.topic = f"{obj.batch.name} (Session)"
             
        super().save_model(request, obj, form, change)

@admin.register(SpecialClass)
class SpecialClassAdmin(admin.ModelAdmin):
    list_display = ('title', 'start_datetime', 'tutor')
    filter_horizontal = ('allowed_students',)
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "tutor":
            kwargs["queryset"] = User.objects.filter(Q(groups__name='Tutor') | Q(is_superuser=True)).distinct()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'batch', 'assigned_to', 'workshop_package', 'is_used')
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
        # Requirement: Send Email IF Assigned to Student AND Not Used (Checked=False)
        # Avoid spamming:
        # 1. New Record (not change)
        # 2. Existing Record (change) but ONLY if 'assigned_to' just changed
        
        should_send = False
        if obj.assigned_to and not obj.is_used:
             if not change:
                 # New Creation + Valid User + Unused
                 should_send = True
             else:
                 # Update: Check if 'assigned_to' was the field that changed
                 if 'assigned_to' in form.changed_data:
                     should_send = True
        
        if should_send:
             from .tasks import send_new_coupon_email
             # Synchronous call as requested/safety
             sent = send_new_coupon_email(obj.id)
             if sent:
                 self.message_user(request, f"Email sent to {obj.assigned_to.email} with Coupon Code.", level=messages.SUCCESS)
             else:
                 self.message_user(request, "Failed to send email. Check logs.", level=messages.WARNING)

@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'batch', 'enrolled_at', 'expires_at', 'is_active')
    list_filter = ('batch',)
    search_fields = ('user__username', 'user__email')

@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'class_session', 'joined_at')


# --- CONTENTS ---
@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active')
    list_editable = ('is_active',)

@admin.register(AboutSection)
class AboutSectionAdmin(admin.ModelAdmin):
    list_display = ('instructor_name', 'is_active')
    list_editable = ('is_active',)

@admin.register(ClassType)
class ClassTypeAdmin(admin.ModelAdmin):
    list_display = ('title', 'price', 'order', 'is_active')
    list_editable = ('order', 'is_active')

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('student_name', 'role', 'is_active')

@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('caption', 'order', 'image', 'is_active')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order', 'is_active')
