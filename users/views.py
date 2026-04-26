import stripe
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import get_user_model
from .models import User

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class RegisterView(APIView):
    permission_classes = []

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        referral_code = request.data.get('referral_code', '').strip().upper()

        if not username or not password:
            return Response(
                {'error': 'Username and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Username already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email
        )

        # Apply referral if code provided
        if referral_code:
            try:
                referrer = User.objects.get(referral_code=referral_code)
                if referrer.id != user.id:
                    user.referred_by = referrer
                    user.cv_limit += 1  # Bonus for being referred
                    user.save()
                    referrer.referral_count += 1
                    referrer.cv_limit += 1  # Bonus for referring
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
            return Response({'error': 'Stripe price not configured'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.username,
                metadata={'user_id': user.id}
            )
            user.stripe_customer_id = customer.id
            user.save()

        session = stripe.checkout.Session.create(
            customer=user.stripe_customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price': settings.STRIPE_PRICE_ID,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=request.build_absolute_uri('/subscription/success?session_id={CHECKOUT_SESSION_ID}'),
            cancel_url=request.build_absolute_uri('/subscription/cancel'),
        )
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
            return Response({'message': 'Subscription canceled'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({'error': 'Invalid payload'}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

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
            except User.DoesNotExist:
                pass

        elif event['type'] == 'invoice.payment_failed':
            invoice = event['data']['object']
            customer_id = invoice.get('customer')
            try:
                user = User.objects.get(stripe_customer_id=customer_id)
                user.subscription_status = 'past_due'
                user.save()
            except User.DoesNotExist:
                pass

        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            subscription_id = subscription.get('id')
            try:
                user = User.objects.get(stripe_subscription_id=subscription_id)
                user.is_premium = False
                user.subscription_status = 'canceled'
                user.save()
            except User.DoesNotExist:
                pass

        return Response({'status': 'success'})


class ReferralInfoView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        referrals = User.objects.filter(referred_by=user).values('username', 'date_joined')
        return Response({
            'referral_code': user.referral_code,
            'referral_count': user.referral_count,
            'referral_link': f"{settings.FRONTEND_URL}/login?ref={user.referral_code}",
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
            referrer = User.objects.get(referral_code=referral_code)
            if referrer.id == user.id:
                return Response({'error': 'Cannot refer yourself'}, status=status.HTTP_400_BAD_REQUEST)

            user.referred_by = referrer
            user.cv_limit += 1  # Bonus for being referred
            user.save()
            referrer.referral_count += 1
            referrer.cv_limit += 1  # Bonus for referring
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

        if platform not in ['linkedin', 'facebook', 'twitter', 'tiktok', 'youtube']:
            return Response({'error': 'Invalid platform'}, status=status.HTTP_400_BAD_REQUEST)

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

        # Reward user for sharing (first time only per platform)
        user = request.user
        share_key = f'shared_{platform}'
        if not getattr(user, share_key, False):
            user.cv_limit += 1
            setattr(user, share_key, True)
            user.save()
            return Response({
                'message': f'Thanks for sharing on {platform.title()}! You got +1 free optimization.',
                'cv_limit': user.cv_limit,
            })

        return Response({'message': f'Share tracked for {platform.title()}.'})
