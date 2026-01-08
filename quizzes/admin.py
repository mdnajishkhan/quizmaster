from django.contrib import admin
from .models import Quiz, Question, Choice, Attempt, Answer, QuizAccessGrant, Profile, College, Category, HackathonResult
from django.urls import path
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db.models import Avg
import pandas as pd
from .forms import QuestionImportForm
from nested_admin import NestedModelAdmin, NestedTabularInline, NestedStackedInline

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

@admin.register(Quiz)
class QuizAdmin(NestedModelAdmin):
    list_display = ('title', 'category', 'quiz_type', 'difficulty', 'is_active', 'coupon_code')
    list_filter = ('category', 'quiz_type', 'difficulty', 'is_active')
    search_fields = ('title', 'coupon_code')
    ordering = ('-id',)
    list_editable = ('is_active',)
    inlines = [QuestionInline]
    fieldsets = (
        ('Quiz Info', {'fields': ('title', 'description', 'category', 'quiz_type', 'difficulty', 'duration_minutes', 'passing_percentage', 'is_active', 'generate_certificate')}),
        ('Access Control', {'fields': ('coupon_code', 'start_time', 'end_time')}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:object_id>/import-questions/',
                self.admin_site.admin_view(self.import_questions),
                name='quiz-import-questions',
            ),
        ]
        return custom_urls + urls

    def import_questions(self, request, object_id):
        quiz = self.get_object(request, object_id)
        if request.method == 'POST':
            form = QuestionImportForm(request.POST, request.FILES)
            if form.is_valid():
                file = request.FILES['file']
                try:
                    if file.name.endswith('.csv'):
                        df = pd.read_csv(file)
                    else:
                        df = pd.read_excel(file)
                    
                    # Expected columns: Question, Option A, Option B, Option C, Option D, Correct Answer
                    # Normalize headers
                    df.columns = [c.strip() for c in df.columns]
                    
                    count = 0
                    for index, row in df.iterrows():
                        question_text = row.get('Question')
                        if not question_text:
                            continue
                        
                        # Create Question
                        question = Question.objects.create(quiz=quiz, text=question_text)
                        
                        # Options
                        options = {
                            'A': row.get('Option A'),
                            'B': row.get('Option B'),
                            'C': row.get('Option C'),
                            'D': row.get('Option D')
                        }
                        
                        correct_ans = str(row.get('Correct Answer')).strip().upper()
                        
                        for key, text in options.items():
                            if pd.isna(text):
                                continue
                            
                            is_correct = False
                            # Check if correct answer matches the option key (A, B, C, D) or the text itself
                            if correct_ans == key:
                                is_correct = True
                            elif correct_ans == str(text).strip().upper():
                                is_correct = True
                                
                            Choice.objects.create(
                                question=question,
                                text=text,
                                is_correct=is_correct
                            )
                        count += 1
                    
                    messages.success(request, f"Successfully imported {count} questions.")
                    return redirect('admin:quizzes_quiz_change', object_id)
                    
                except Exception as e:
                    messages.error(request, f"Error importing file: {e}")
        else:
            form = QuestionImportForm()

        context = {
            'form': form,
            'object': quiz,
            'opts': self.model._meta,
            'object_id': object_id,
            'title': f'Import Questions for {quiz.title}'
        }
        return render(request, 'admin/quizzes/quiz/import_questions.html', context)

@admin.register(HackathonResult)
class HackathonResultAdmin(admin.ModelAdmin):
    change_list_template = None # Use default list template
    list_display = ('title', 'start_time', 'end_time', 'get_participant_count', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('title',)
    ordering = ('-start_time',)

    def get_queryset(self, request):
        # 🔍 Only show Hackathon Quizzes
        return super().get_queryset(request).filter(quiz_type=Quiz.HACKATHON)

    def get_participant_count(self, obj):
        return obj.attempt_set.count()
    get_participant_count.short_description = "Participants"

    def has_add_permission(self, request):
        return False # 🚫 Read-only: Cannot create quizzes here

    def has_delete_permission(self, request, obj=None):
        return False # 🚫 Read-only: Cannot delete here

    def change_view(self, request, object_id, form_url='', extra_context=None):
        # 📊 Custom Logic for Dashboard View
        quiz = self.get_object(request, object_id)
        
        # 1. Fetch all attempts (passed only? or all? usually all for leaderboard but ranked by score)
        # 1. Fetch COMPLETED attempts for Leaderboard
        completed_attempts = Attempt.objects.filter(quiz=quiz, finished_at__isnull=False).select_related('user').order_by('-score', 'finished_at')
        
        # 2. Compute Stats (Total Participants = All Attempts, including incomplete)
        all_attempts_count = Attempt.objects.filter(quiz=quiz).count()
        
        avg_score = completed_attempts.aggregate(Avg('score'))['score__avg'] or 0
        top_scorer = completed_attempts.first()

        # 3. Prepare Leaderboard Data
        leaderboard = []
        for index, attempt in enumerate(completed_attempts):
            time_taken = "N/A"
            if attempt.finished_at and attempt.created_at:
                duration = attempt.finished_at - attempt.created_at
                total_seconds = int(duration.total_seconds())
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                time_taken = f"{minutes}m {seconds}s"

            # Safely get college (handle missing profile)
            college_name = "-"
            if hasattr(attempt.user, 'profile') and attempt.user.profile.college:
                college_name = attempt.user.profile.college.name

            percentage = 0
            max_score = quiz.questions.count()
            if max_score > 0:
                percentage = round((attempt.score / max_score) * 100, 1)

            leaderboard.append({
                'rank': index + 1,
                'user': attempt.user,
                'score': attempt.score,
                'max_score': max_score,
                'percentage': percentage, # Added Percentage
                'passed': attempt.passed,
                'time_taken': time_taken,
                'submitted_at': attempt.finished_at,
                'college_name': college_name,
            })

        extra_context = extra_context or {}
        extra_context['show_save_and_continue'] = False
        extra_context['show_save'] = False
        extra_context['title'] = f"Results: {quiz.title}"
        
        # Pass data to template
        extra_context.update({
            'quiz': quiz,
            'total_participants': all_attempts_count, # Show ALL attempts count
            'completed_count': completed_attempts.count(),
            'avg_score': round(avg_score, 1),
            'top_scorer': top_scorer,
            'leaderboard': leaderboard,
        })
        
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )
    change_form_template = 'admin/quizzes/hackathonresult/change_form.html'


admin.site.register(Question, QuestionAdmin)
@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_college_name', 'quiz', 'score', 'passed', 'finished_at')
    list_filter = ('quiz', 'passed', 'finished_at', 'user__profile__college')
    date_hierarchy = 'finished_at'
    ordering = ('-score', 'finished_at')

    def get_college_name(self, obj):
        if hasattr(obj.user, 'profile') and obj.user.profile.college:
            return obj.user.profile.college.name
        return "-"
    get_college_name.short_description = 'College'
admin.site.register(QuizAccessGrant)
admin.site.register(Profile)
admin.site.register(College)
admin.site.register(Category)
