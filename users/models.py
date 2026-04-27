# users/models.py

import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    SUBSCRIPTION_STATUS_CHOICES = [
        ('inactive', 'Inactive'),
        ('active', 'Active'),
        ('canceled', 'Canceled'),
        ('past_due', 'Past Due'),
    ]

    is_premium = models.BooleanField(default=False)
    cv_limit = models.IntegerField(default=1)
    stripe_customer_id = models.CharField(max_length=255, blank=True, default='')
    stripe_subscription_id = models.CharField(max_length=255, blank=True, default='')
    subscription_status = models.CharField(
        max_length=20,
        choices=SUBSCRIPTION_STATUS_CHOICES,
        default='inactive'
    )

    # Referral system fields
    referral_code = models.CharField(max_length=12, unique=True, blank=True, null=True)
    referred_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='referrals'
    )
    referral_count = models.PositiveIntegerField(default=0)

    # Social share tracking (prevents infinite exploit)
    shared_platforms = models.JSONField(default=list, blank=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            self.referral_code = self._generate_referral_code()
        super().save(*args, **kwargs)

    def _generate_referral_code(self):
        return str(uuid.uuid4())[:8].upper()

    def __str__(self):
        return self.username
