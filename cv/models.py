# cv/models.py

from django.db import models
from django.conf import settings

class CV(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    original_text = models.TextField()
    optimized_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Social sharing tracking
    shared_on_social = models.BooleanField(default=False)
    shared_platforms = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.user.username}'s CV"
