# cv/views.py

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import CV
from django.conf import settings
from openai import OpenAI

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def cv_history(request):
    user = request.user
    if not user.is_premium:
        return Response({"error": "History is a premium feature. Upgrade to access."}, status=403)
    cvs = CV.objects.filter(user=user).order_by('-created_at')
    data = [
        {
            'id': cv.id,
            'original_text': cv.original_text[:200] + '...' if len(cv.original_text) > 200 else cv.original_text,
            'optimized_text': cv.optimized_text[:200] + '...' if cv.optimized_text and len(cv.optimized_text) > 200 else cv.optimized_text,
            'created_at': cv.created_at.isoformat(),
        }
        for cv in cvs
    ]
    return Response(data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def optimize_cv(request):
    user = request.user

    if not user.is_premium and user.cv_limit <= 0:
        return Response({"error": "Limit reached. Upgrade to continue."}, status=403)

    cv_text = request.data.get("cv_text")
    job_desc = request.data.get("job_description")

    if not cv_text or not job_desc:
        return Response({"error": "Both CV text and job description are required."}, status=400)

    if not settings.OPENAI_API_KEY:
        return Response({"error": "OpenAI API key is not configured."}, status=500)

    prompt = f"""
    Rewrite this CV to match the job description.
    Make it ATS-friendly and impactful.

    CV:
    {cv_text}

    Job Description:
    {job_desc}
    """

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        optimized = response.choices[0].message.content
    except Exception as e:
        return Response({"error": f"AI optimization failed: {str(e)}"}, status=500)

    CV.objects.create(
        user=user,
        original_text=cv_text,
        optimized_text=optimized
    )

    if not user.is_premium:
        user.cv_limit -= 1
        user.save()

    return Response({"optimized_cv": optimized})
