# cv/models.py

from django.db import models
from django.conf import settings


class CV(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('optimized', 'Optimized'),
        ('shared', 'Shared'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    name = models.CharField(max_length=100, default='My CV')
    job_title = models.CharField(max_length=200, blank=True, default='')
    original_text = models.TextField()
    optimized_text = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    version = models.IntegerField(default=1)
    is_template = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Social sharing tracking
    shared_on_social = models.BooleanField(default=False)
    shared_platforms = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.user.username}'s CV - {self.name}"
