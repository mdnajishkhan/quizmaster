from django.urls import path
from . import views

app_name = 'landingpage'

urlpatterns = [
    path('', views.workshop_landing, name='workshop_landing'),
    path('submit-query/', views.submit_query, name='submit_query'),
    path('register-lead/', views.register_workshop, name='register_workshop'),
]
