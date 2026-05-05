from django.test import TestCase
from quizzes.models import Quiz, Question
from quizzes.admin import QuizAdmin, QuestionInline
from django.contrib import admin

class QuizAdminInlineTest(TestCase):
    def test_question_inline_in_quiz_admin(self):
        # Check if QuestionInline is in QuizAdmin.inlines
        self.assertIn(QuestionInline, QuizAdmin.inlines)
