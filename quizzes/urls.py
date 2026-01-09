from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from .forms import UserLoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('categories/', views.category_list, name='category_list'),
    path('quizzes/', views.quiz_list, name='quiz_list'),
    path('quizzes/<int:category_id>/', views.quiz_list, name='quiz_list_by_category'),
    path('quiz/<int:pk>/', views.quiz_detail, name='quiz_detail'),
    path('quiz/<int:pk>/start/', views.start_quiz, name='start_quiz'),
    path('attempt/<int:attempt_id>/question/<int:question_id>/', views.take_quiz, name='take_quiz'),
    path('attempt/<int:attempt_id>/result/', views.result, name='result'),
    path('activate/<uidb64>/<token>/', views.activate, name='activate'),
    
    # Password Reset
    path('password-reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),

    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='quizzes/password_reset_done.html'
    ), name='password_reset_done'),

    path('password-reset-confirm/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('certificate/<int:attempt_id>/', views.certificate_view, name='certificate'),
    path('profile/', views.profile_view, name='profile'),
    path('my-history/', views.my_history, name='my_history'),
    path('password-change/', auth_views.PasswordChangeView.as_view(template_name='quizzes/password_change.html'), name='password_change'),
    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='quizzes/password_change_done.html'), name='password_change_done'),
    path('ask-ai/', views.ask_ai, name='ask_ai'),
    path('analyze-progress/', views.analyze_progress, name='analyze_progress'),
    path('generate-quiz/', views.generate_quiz_page, name='generate_quiz_page'),
    path('api/generate-quiz/', views.generate_quiz_api, name='generate_quiz_api'),
    path('api/use-lifeline/', views.use_lifeline_api, name='use_lifeline_api'),
]
