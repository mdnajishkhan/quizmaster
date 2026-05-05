from django.contrib import admin
from .models import Quiz, Question, Choice, Attempt, Answer, QuizAccessGrant, Profile, Category, HackathonResult, Announcement, Expense
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg, Sum, Count
from django.db.models.functions import TruncDate, TruncMonth, TruncWeek
from django.core.serializers.json import DjangoJSONEncoder
import json
import pandas as pd
from .forms import QuestionImportForm
from nested_admin import NestedModelAdmin, NestedTabularInline, NestedStackedInline
from .models import Quiz, Question, Choice, Attempt, Answer, QuizAccessGrant, Profile, Category, HackathonResult, Announcement, Expense, AdminDashboard
from training.models import Coupon
from background_task.models import Task, CompletedTask

@admin.register(AdminDashboard)
class AdminDashboardAdmin(admin.ModelAdmin):
    change_list_template = 'admin/dashboard_view.html'

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
        
    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        
        # --- STATS ---
        from django.contrib.auth.models import User
        
        # Filter: Students = Not Staff, Not Superuser, Not in 'Tutor' group
        student_qs = User.objects.exclude(is_staff=True).exclude(is_superuser=True).exclude(groups__name='Tutor')
        
        total_students = student_qs.count()
        income_agg = Coupon.objects.aggregate(total=Sum('payment_amount'))
        total_income = income_agg['total'] or 0
        expense_agg = Expense.objects.aggregate(total=Sum('amount'))
        total_expense = expense_agg['total'] or 0
        
        extra_context['total_students'] = total_students
        extra_context['total_income'] = total_income
        extra_context['total_expense'] = total_expense
        extra_context['net_profit'] = total_income - total_expense
        
        # --- TODAY'S SCHEDULE ---
        from training.models import BatchSchedule
        from django.utils import timezone
        
        today_date = timezone.localtime(timezone.now()).date()
        weekday = today_date.weekday() # 0=Mon
        
        schedules = BatchSchedule.objects.filter(day_of_week=weekday).select_related('batch__workshop', 'tutor').order_by('start_time')
        todays_classes = []
        for s in schedules:
            todays_classes.append({
                'time': s.start_time.strftime('%I:%M %p'),
                'batch': s.batch.name,
                'topic': s.topic,
                'tutor': s.tutor.get_full_name() if s.tutor else 'Unassigned'
            })
            
        extra_context['todays_classes'] = todays_classes
        
        # --- LISTS ---
        extra_context['recent_students'] = student_qs.order_by('-date_joined')[:5]
        extra_context['recent_expenses'] = Expense.objects.all().order_by('-date')[:5]
        extra_context['recent_income'] = Coupon.objects.filter(payment_amount__gt=0).order_by('-payment_date')[:5]

        # Custom Render to avoid Table Query
        context = {
            **admin.site.each_context(request),
            'title': 'Project Dashboard',
            'app_list': admin.site.get_app_list(request),
            **extra_context,
        }
        return render(request, self.change_list_template, context)


class ChoiceInline(NestedTabularInline):
    model = Choice
    extra = 2


class QuestionAdmin(admin.ModelAdmin):
    inlines = [ChoiceInline]
    list_display = ('quiz', 'short_text')

    def short_text(self, obj):
        return obj.text[:60]


class QuestionInline(NestedStackedInline):
    model = Question
    extra = 1
    inlines = [ChoiceInline]

# @admin.register(Quiz)
class QuizAdmin(NestedModelAdmin):
    # ... (code hidden)
    pass

# @admin.register(HackathonResult)
class HackathonResultAdmin(admin.ModelAdmin):
   # ... (code hidden)
   pass

# admin.site.register(Question, QuestionAdmin) # 🚫 Hiding Question from top-level
# @admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_location', 'quiz', 'score', 'passed', 'finished_at')
    # Removed user__profile__college, added user__profile__city and user__profile__state
    list_filter = ('quiz', 'passed', 'finished_at', 'user__profile__city', 'user__profile__state')
    date_hierarchy = 'finished_at'
    ordering = ('-score', 'finished_at')

    def get_location(self, obj):
        if hasattr(obj.user, 'profile'):
            parts = []
            if obj.user.profile.city: parts.append(obj.user.profile.city)
            if obj.user.profile.state: parts.append(obj.user.profile.state)
            return ", ".join(parts) if parts else "-"
        return "-"
    get_location.short_description = 'Location'
# admin.site.register(QuizAccessGrant) # 🚫 Hiding low-level access grants
admin.site.register(Profile)
# admin.site.register(Category)
@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'created_at')
    list_editable = ('is_active',)
    list_filter = ('is_active',)
    list_filter = ('is_active',)

@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('title', 'amount', 'category', 'date')
    list_filter = ('category', 'date')
    search_fields = ('title', 'description')
    date_hierarchy = 'date'

# 🚫 Hide Background Tasks from Admin (Client Request)
admin.site.unregister(Task)
admin.site.unregister(CompletedTask)
