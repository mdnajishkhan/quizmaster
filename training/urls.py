from django.urls import path
from . import views

urlpatterns = [
    path('', views.training_program, name='training_program'),
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('join/<int:schedule_id>/', views.track_attendance, name='track_attendance'),
    path('history/', views.payment_history, name='payment_history'),
    path('explore/', views.training_overview, name='training_overview'),
    path('api/package-details/<int:package_id>/', views.get_package_details, name='get_package_details'),
    path('tutor/', views.tutor_dashboard, name='tutor_dashboard'),
    path('api/batch-students/<int:batch_id>/', views.get_batch_students, name='get_batch_students'),
]
