from django.utils import timezone
from .models import Enrollment

def training_context(request):
    """
    Global context processor to check if the current user
    is an active student (has any active enrollment).
    """
    is_active_student = False
    if request.user.is_authenticated:
        # Check against ALL active enrollments
        is_active_student = Enrollment.objects.filter(
            user=request.user, 
            expires_at__gt=timezone.now()
        ).exists()
        
    return {
        'is_active_student': is_active_student
    }
