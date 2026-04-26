# cv/urls.py
from django.urls import path
from .views import optimize_cv, cv_history

urlpatterns = [
    path('optimize/', optimize_cv),
    path('history/', cv_history),
]
