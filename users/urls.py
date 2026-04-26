from django.urls import path
from .views import (
    RegisterView, UserProfileView, CreateCheckoutSessionView,
    SubscriptionStatusView, CancelSubscriptionView, StripeWebhookView,
    ReferralInfoView, ApplyReferralView, TrackSocialShareView
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('me/', UserProfileView.as_view(), name='user_profile'),
    path('checkout/', CreateCheckoutSessionView.as_view(), name='checkout'),
    path('subscription-status/', SubscriptionStatusView.as_view(), name='subscription_status'),
    path('cancel-subscription/', CancelSubscriptionView.as_view(), name='cancel_subscription'),
    path('webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('referral-info/', ReferralInfoView.as_view(), name='referral_info'),
    path('apply-referral/', ApplyReferralView.as_view(), name='apply_referral'),
    path('track-share/', TrackSocialShareView.as_view(), name='track_share'),
]

