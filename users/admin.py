from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Extra Info', {'fields': ('is_premium', 'cv_limit', 'subscription_status', 'stripe_customer_id', 'stripe_subscription_id', 'referral_code', 'referred_by', 'referral_count')}),
    )
    list_display = UserAdmin.list_display + ('is_premium', 'subscription_status', 'cv_limit', 'referral_count', 'referral_code')
    search_fields = UserAdmin.search_fields + ('referral_code',)
