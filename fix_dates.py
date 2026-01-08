import os
import django
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

from quizzes.models import Quiz

# Find AI Quizzes with no creation date
# We assume if it has no date, it's recent enough (since this feature is new) 
# and should count towards the current limit to prevent abuse.
quizzes_to_fix = Quiz.objects.filter(category__name="AI Generated", created_at__isnull=True)
count = quizzes_to_fix.count()

print(f"Found {count} AI quizzes with missing dates.")

if count > 0:
    # Set them to now so they count for this month
    now = timezone.now()
    updated = quizzes_to_fix.update(created_at=now)
    print(f"Successfully backfilled date for {updated} quizzes.")
else:
    print("No quizzes needed fixing.")

# Verify count for specific user if known, or just general check
from django.contrib.auth.models import User
users = User.objects.all()
start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

print("\n--- New Counts ---")
for u in users:
    c = Quiz.objects.filter(
        created_by=u, 
        category__name="AI Generated", 
        created_at__gte=start_of_month
    ).count()
    if c > 0:
        print(f"User {u.username}: {c} AI Quizzes this month.")
