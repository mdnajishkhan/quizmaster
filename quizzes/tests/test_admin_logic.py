from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from quizzes.models import Attempt, Quiz, College, Profile
from quizzes.admin import AttemptAdmin

class AttemptAdminTest(TestCase):
    def test_attempt_admin_configuration(self):
        # Verify list_filter and ordering
        self.assertIn('user__profile__college', AttemptAdmin.list_filter)
        self.assertEqual(AttemptAdmin.ordering, ('-score', 'finished_at'))

    def test_attempt_sorting_logic(self):
        # Setup
        user1 = User.objects.create(username='user1')
        user2 = User.objects.create(username='user2')
        user3 = User.objects.create(username='user3')
        
        quiz = Quiz.objects.create(title="Test Quiz")
        
        now = timezone.now()
        
        # Attempt 1: Score 100, finished now
        a1 = Attempt.objects.create(user=user1, quiz=quiz, score=100, finished_at=now)
        
        # Attempt 2: Score 100, finished earlier (should be ranked higher than a1 if tie-breaking by time)
        a2 = Attempt.objects.create(user=user2, quiz=quiz, score=100, finished_at=now - timezone.timedelta(minutes=5))
        
        # Attempt 3: Score 90, finished earlier (should be ranked lower than a1 and a2)
        a3 = Attempt.objects.create(user=user3, quiz=quiz, score=90, finished_at=now - timezone.timedelta(minutes=10))
        
        # Query with the admin ordering
        attempts = Attempt.objects.order_by('-score', 'finished_at')
        
        # Expected order: a2 (100, earlier), a1 (100, later), a3 (90)
        self.assertEqual(list(attempts), [a2, a1, a3])
