from django.test import TestCase
from quizzes.admin import QuizAdmin, QuestionInline, ChoiceInline
from nested_admin import NestedModelAdmin, NestedStackedInline, NestedTabularInline

class NestedAdminTest(TestCase):
    def test_quiz_admin_inheritance(self):
        # Check if QuizAdmin inherits from NestedModelAdmin
        self.assertTrue(issubclass(QuizAdmin, NestedModelAdmin))

    def test_question_inline_inheritance(self):
        # Check if QuestionInline inherits from NestedStackedInline
        self.assertTrue(issubclass(QuestionInline, NestedStackedInline))

    def test_choice_inline_inheritance(self):
        # Check if ChoiceInline inherits from NestedTabularInline
        self.assertTrue(issubclass(ChoiceInline, NestedTabularInline))

    def test_nested_structure(self):
        # Check if QuestionInline has ChoiceInline in inlines
        self.assertIn(ChoiceInline, QuestionInline.inlines)
        # Check if QuizAdmin has QuestionInline in inlines
        self.assertIn(QuestionInline, QuizAdmin.inlines)
