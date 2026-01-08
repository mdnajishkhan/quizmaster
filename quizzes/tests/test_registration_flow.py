from django.test import TestCase, Client
from django.contrib.auth.models import User
from quizzes.models import College, Profile

class RegistrationTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.college = College.objects.create(name="Test University")

    def test_registration_flow(self):
        response = self.client.post('/register/', {
            'full_name': 'John Doe',
            'email': 'john@example.com',
            'college': self.college.id,
            'password': 'password123',
            'confirm_password': 'password123'
        })

        # Check redirection (success)
        if response.status_code != 302:
            print(f"Form errors: {response.context['form'].errors}")
        
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/quizzes/') # Assuming redirect to quiz_list which is usually /quizzes/ or similar. Let's check urls.py later if this fails.

        # Check User
        user = User.objects.get(email='john@example.com')
        self.assertEqual(user.username, 'john@example.com')
        self.assertEqual(user.first_name, 'John')
        self.assertEqual(user.last_name, 'Doe')

        # Check Profile
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.college, self.college)
        print("Registration test passed!")
