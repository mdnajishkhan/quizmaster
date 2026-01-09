from django.urls import path
from . import views

urlpatterns = [
    path('', views.training_program, name='training_program'),
    path('join/<int:schedule_id>/', views.track_attendance, name='track_attendance'),
    path('history/', views.payment_history, name='payment_history'),
]
