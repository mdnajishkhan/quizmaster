import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from quizzes.models import Quiz, Category
from django.contrib.auth.models import User

# Get the user (assuming there is only one logged in/main user or the one creating quizzes)
# Since we don't know the exact user ID from here easily, let's list all users' stats or just the first one
# But usually the user is 'admin' or similar.
# Let's check quizzes with category "AI Generated"

print("--- Checking Categories ---")
cats = Category.objects.filter(name="AI Generated")
print(f"Categories found: {cats.count()}")
for c in cats:
    print(f"Category: '{c.name}' (ID: {c.id})")

print("\n--- Checking AI Quizzes ---")
quizzes = Quiz.objects.filter(category__name="AI Generated").order_by('-id')[:10]
print(f"Recent 10 AI Quizzes:")
for q in quizzes:
    print(f"ID: {q.id} | Title: {q.title} | Type: {q.quiz_type} | Category: {q.category.name if q.category else 'None'} | Created At: {q.created_at} | By: {q.created_by.username if q.created_by else 'None'}")

print("\n--- Checking Monthly Count Logic ---")
now = timezone.now()
start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
print(f"Start of month: {start_of_month}")

users = User.objects.all()
for u in users:
    count = Quiz.objects.filter(
        created_by=u,
        quiz_type='practice',
        category__name="AI Generated",
        created_at__gte=start_of_month
    ).count()
    print(f"User: {u.username} | Count >= {start_of_month}: {count}")
    
    # Also check total count without date
    total_count = Quiz.objects.filter(
        created_by=u,
        quiz_type='practice',
        category__name="AI Generated"
    ).count()
    print(f"User: {u.username} | Total AI Quizzes: {total_count}")
