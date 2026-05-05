from .models import Announcement

def active_announcement(request):
    """
    Returns the latest active announcement based on user type.
    """
    from django.utils import timezone
    # Avoid circular import by importing inside function if needed, 
    # but Enrollment is in 'training', Announcement in 'core'.
    # We need to detect if user is an 'Active Student'.
    
    is_student = False
    if request.user.is_authenticated:
        # Check for any active enrollment
        # We perform a raw check or import model. 
        # Better to do a safe import.
        try:
            from training.models import Enrollment
            is_student = Enrollment.objects.filter(
                user=request.user, 
                expires_at__gt=timezone.now()
            ).exists()
        except ImportError:
            pass

    # Filter Announcements
    # 1. Base: Active
    base_query = Announcement.objects.filter(is_active=True)
    
    # 2. Audience Filter
    if is_student:
        # Students see 'ALL' and 'STUDENTS'
        final_query = base_query.filter(target_audience__in=['ALL', 'STUDENTS'])
    else:
        # Visitors (Anon or Inactive) see 'ALL' and 'VISITORS'
        final_query = base_query.filter(target_audience__in=['ALL', 'VISITORS'])
        
    # 3. Get Latest
    announcement = final_query.order_by('-created_at').first()
    
    return {'active_announcement': announcement}
