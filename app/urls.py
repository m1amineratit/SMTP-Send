from django.urls import path
from . import views

urlpatterns = [
    path('trigger-email/', views.trigger_email, name='trigger_email'),
]