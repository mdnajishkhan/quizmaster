from django import template
from django.contrib.auth.models import User
from django.db.models import Sum
from core.models import Expense
from training.models import Coupon

register = template.Library()

@register.inclusion_tag('admin/dashboard_stats.html')
def get_admin_dashboard_stats():
    # 1. Total Students (assuming generic User count for now, or filter by role check)
    # If there is a Profile role or Group, use that. 
    # For now, let's count all non-superusers/staff or just all users? 
    # User requested "Total number of student".
    # Assuming standard users are students.
    total_students = User.objects.filter(is_staff=False).count()
    
    # 2. Total Income (Sum of Coupon payments)
    income_agg = Coupon.objects.aggregate(total=Sum('payment_amount'))
    total_income = income_agg['total'] or 0
    
    # 3. Total Expense
    expense_agg = Expense.objects.aggregate(total=Sum('amount'))
    total_expense = expense_agg['total'] or 0
    
    # 4. Recent Lists
    recent_students = User.objects.filter(is_staff=False).order_by('-date_joined')[:5]
    recent_expenses = Expense.objects.all().order_by('-date')[:5]
    recent_income = Coupon.objects.filter(payment_amount__gt=0).order_by('-payment_date')[:5]
    
    return {
        'total_students': total_students,
        'total_income': total_income,
        'total_expense': total_expense,
        'recent_students': recent_students,
        'recent_expenses': recent_expenses,
        'recent_income': recent_income,
    }
