import re
import stripe
import logging
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY
logger = logging.getLogger(__name__)

# Constants
VALID_PLATFORMS = {'linkedin', 'facebook', 'twitter', 'tiktok', 'youtube'}
USERNAME_REGEX = re.compile(r'^[a-zA-Z0-9_-]{3,30}$')
MAX_CV_TEXT_LENGTH = 20000
MAX_JOB_DESC_LENGTH = 20000


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')
        email = request.data.get('email', '').strip()
        referral_code = request.data.get('referral_code', '').strip().upper()

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not USERNAME_REGEX.match(username):
            return Response(
                {'error': 'Username must be 3-30 characters and contain only letters, numbers, underscores, and hyphens.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username__iexact=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        # Apply referral if code provided (atomic to prevent race conditions)
        if referral_code:
            try:
                with transaction.atomic():
                    referrer = User.objects.select_for_update().get(referral_code=referral_code)
                    if referrer.id != user.id:
                        user.referred_by = referrer
                        user.cv_limit += 1
                        user.save()
                        referrer.referral_count += 1
                        referrer.cv_limit += 1
                        referrer.save()
            except User.DoesNotExist:
                pass  # Invalid referral code, ignore

        return Response(
            {
                'message': 'User created successfully',
                'username': user.username,
                'referral_code': user.referral_code,
            },
            status=status.HTTP_201_CREATED
        )


class UserProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'is_premium': user.is_premium,
            'cv_limit': user.cv_limit,
            'subscription_status': user.subscription_status,
            'referral_code': user.referral_code,
            'referral_count': user.referral_count,
        })


class CreateCheckoutSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not settings.STRIPE_PRICE_ID:
            logger.error('Stripe checkout attempted but STRIPE_PRICE_ID is not configured')
            return Response({'error': 'Stripe price not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={'user_id': user.id}
            )
            user.stripe_customer_id = customer.id
            user.save()

        frontend_url = settings.FRONTEND_URL.rstrip('/')
        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=f"{frontend_url}/subscription/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{frontend_url}/subscription/cancel",
        )
        logger.info(f"Stripe checkout session created for user {user.id}")
        return Response({'checkout_url': session.url})


class SubscriptionStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            'is_premium': user.is_premium,
            'subscription_status': user.subscription_status,
            'cv_limit': user.cv_limit,
        })


class CancelSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.stripe_subscription_id:
            return Response({'error': 'No active subscription'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            stripe.Subscription.delete(user.stripe_subscription_id)
            user.is_premium = False
            user.subscription_status = 'canceled'
            user.save()
            logger.info(f"Subscription canceled for user {user.id}")
            return Response({'message': 'Subscription canceled'})
        except stripe.error.StripeError as e:
            logger.warning(f"Stripe cancel failed for user {user.id}: {e}")
            return Response({'error': 'Failed to cancel subscription. Please try again.'}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        if not sig_header:
            logger.warning("Stripe webhook received without signature header")
            return Response({'error': 'Missing signature header'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            logger.warning("Stripe webhook received invalid payload")
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            logger.warning("Stripe webhook signature verification failed")
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"Stripe webhook received: {event['type']}")

        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            customer_id = session.get('customer')
            subscription_id = session.get('subscription')
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                user.stripe_subscription_id = subscription_id
                user.is_premium = True
                user.subscription_status = 'active'
                user.save()
                logger.info(f"User {user.id} upgraded to premium via Stripe")
            except User.DoesNotExist:
                logger.error(f"Stripe webhook: No user found for customer {customer_id}")

        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                user.subscription_status = 'past_due'
                user.save()
                logger.info(f"User {user.id} subscription marked past_due")
            except User.DoesNotExist:
                logger.error(f"Stripe webhook: No user found for customer {customer_id}")

        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            try:
                user = User.objects.get(stripe_subscription_id=subscription_id)
                user.is_premium = False
                user.subscription_status = 'canceled'
                user.save()
                logger.info(f"User {user.id} subscription deleted")
            except User.DoesNotExist:
                logger.error(f"Stripe webhook: No user found for subscription {subscription_id}")

        return Response({'status': 'success'})


class ReferralInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        referrals = User.objects.filter(referred_by=user).values('username', 'date_joined')
        return Response({
            'referral_code': user.referral_code,
            'referral_count': user.referral_count,
            'referral_link': f"{settings.FRONTEND_URL.rstrip('/')}/login?ref={user.referral_code}",
            'referrals': list(referrals),
        })


class ApplyReferralView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        referral_code = request.data.get('referral_code', '').strip().upper()
        user = request.user

        if not referral_code:
            return Response({'error': 'Referral code is required'}, status=status.HTTP_400_BAD_REQUEST)

        if user.referred_by:
            return Response({'error': 'You have already applied a referral code'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                referrer = User.objects.select_for_update().get(referral_code=referral_code)
                if referrer.id == user.id:
                    return Response({'error': 'Cannot refer yourself'}, status=status.HTTP_400_BAD_REQUEST)

                user.referred_by = referrer
                user.cv_limit += 1
                user.save()
                referrer.referral_count += 1
                referrer.cv_limit += 1
                referrer.save()

            return Response({
                'message': 'Referral applied successfully! You both got +1 free optimization.',
                'cv_limit': user.cv_limit,
            })
        except User.DoesNotExist:
            return Response({'error': 'Invalid referral code'}, status=status.HTTP_400_BAD_REQUEST)


class TrackSocialShareView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        platform = request.data.get('platform', '').lower()
        cv_id = request.data.get('cv_id')

        if platform not in VALID_PLATFORMS:
            return Response({'error': 'Invalid platform'}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user

        # Track share on CV if cv_id provided
        if cv_id:
            from cv.models import CV
            try:
                cv = CV.objects.get(id=cv_id, user=request.user)
                if platform not in cv.shared_platforms:
                    cv.shared_platforms.append(platform)
                    cv.shared_on_social = True
                    cv.save()
            except CV.DoesNotExist:
                pass

        # Reward user for sharing (first time only per platform) — now properly persisted
        if platform not in user.shared_platforms:
            user.shared_platforms.append(platform)
            user.cv_limit += 1
            user.save()
            return Response({
                'message': f'Thanks for sharing on {platform.title()}! You got +1 free optimization.',
                'cv_limit': user.cv_limit,
            })

        return Response({'message': f'Share tracked for {platform.title()}.'})

