# cv/urls.py
from django.urls import path
from .views import (
    cv_list, cv_detail, cv_duplicate, cv_history, 
    optimize_cv, cv_pdf, cv_suggestions, cv_analyze
)

urlpatterns = [
    # CRUD endpoints
    path('', cv_list, name='cv_list'),
    path('<int:cv_id>/', cv_detail, name='cv_detail'),
    path('<int:cv_id>/duplicate/', cv_duplicate, name='cv_duplicate'),
    
    # Legacy endpoint
    path('history/', cv_history, name='cv_history'),
    
    # Features
    path('optimize/', optimize_cv, name='optimize_cv'),
    path('<int:cv_id>/pdf/', cv_pdf, name='cv_pdf'),
    path('<int:cv_id>/suggestions/', cv_suggestions, name='cv_suggestions'),
    path('<int:cv_id>/analyze/', cv_analyze, name='cv_analyze'),
]
