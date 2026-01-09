from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, date, datetime
import calendar as py_calendar
from .models import Coupon, Enrollment, Batch, ClassSchedule, Attendance

@login_required
def training_program(request):
    """
    Gatekeeper View:
    1. Check if user has ANY active enrollment.
    2. If NO -> Show Coupon Entry Page.
    3. If YES -> Show Calendar Grid.
    """
    
    # --- 1. HANDLE COUPON SUBMISSION (POST) ---
    if request.method == 'POST' and 'coupon_code' in request.POST:
        code = request.POST.get('coupon_code', '').strip().upper()
        try:
            coupon = Coupon.objects.get(code=code)
            
            if coupon.is_used:
                messages.error(request, "This code has already been used.")
            elif coupon.assigned_to and coupon.assigned_to != request.user:
                messages.error(request, "This code is not assigned to you.")
            elif coupon.enrollment_valid_until and coupon.enrollment_valid_until < timezone.now().date():
                messages.error(request, "This coupon has expired.")
            else:
                # Enroll User
                # Determine Expiry: Fixed Date > Valid Days
                if coupon.enrollment_valid_until:
             	    # Make it end of day to be generous? Or strictly 00:00? 
             	    # Usually date() is 00:00, so we might want to set time to 23:59:59 
             	    # But Enrollment.expires_at is DateTimeField.
             	    # Let's combine date with max time for friendly access.
                    expires_dt = datetime.combine(coupon.enrollment_valid_until, datetime.max.time())
                    # Ensure timezone awareness
                    expires_dt = datetime.combine(coupon.enrollment_valid_until, datetime.max.time())
                    # USE_TZ=False, so we keep it naive. 
                    # expires_dt = timezone.make_aware(expires_dt) # Removed to avoid MySQL error
                else:
                    expires_dt = timezone.now() + timedelta(days=coupon.valid_days)

                Enrollment.objects.get_or_create(
                    user=request.user,
                    batch=coupon.batch,
                    defaults={'expires_at': expires_dt}
                )
                # Mark used
                coupon.is_used = True
                coupon.save()
                messages.success(request, f"Welcome to {coupon.batch.workshop.title}! You're in.")
                return redirect('training_program') # Reload to see calendar
                
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid access code.")
        
        # If error, Render Entry Page again
        return render(request, 'training/enter_coupon.html')

    # --- 2. CHECK ENROLLMENT ---
    # --- 2. CHECK ENROLLMENT ---
    # Fetch potentially active enrollments
    candidates = Enrollment.objects.filter(
        user=request.user, 
        expires_at__gt=timezone.now()
    ).select_related('batch', 'batch__workshop')

    # STRICT CHECK: Verify against Coupon Limit (Hybrid logic for strictness)
    valid_enrollment_ids = []
    for enr in candidates:
        # Check if stricter logic applies from Coupon
        # Check ALL coupons for this batch to see if ANY give valid access
        # This handles cases where user adds past coupons for history, which shouldn't block current access
        coupons = Coupon.objects.filter(assigned_to=request.user, batch=enr.batch)
        
        is_technically_expired = False
        if coupons.exists():
            # Assume expired until proven active
            is_technically_expired = True 
            max_coupon_expiry = None
            
            for c in coupons:
                # Track max expiry to detect manual extensions later
                if c.enrollment_valid_until:
                    if not max_coupon_expiry or c.enrollment_valid_until > max_coupon_expiry:
                         max_coupon_expiry = c.enrollment_valid_until
                
                # If ANY coupon is valid for today (or has no expiry set), we grant access
                if not c.enrollment_valid_until or timezone.now().date() <= c.enrollment_valid_until:
                    is_technically_expired = False
                    break
            
            # SAFEGUARD: Manual Extension
            # If all coupons are expired, BUT the Enrollment extends significantly beyond the active coupons,
            # we assume the Admin manually extended the user (e.g. by 1 month).
            if is_technically_expired and max_coupon_expiry:
                 # Check if Enrollment expires AFTER the latest coupon (with 1 day buffer for timezone checks)
                 enrollment_expiry_date = enr.expires_at.date()
                 if enrollment_expiry_date > max_coupon_expiry:
                     is_technically_expired = False
        
        if not is_technically_expired:
            valid_enrollment_ids.append(enr.id)

    active_enrollments = candidates.filter(id__in=valid_enrollment_ids)

    if not active_enrollments.exists():
        # 🚫 GATEKEEPER BLOCKED -> Show Entry Form
        # But first, fetch history to show in modal
        all_enrollments = Enrollment.objects.filter(user=request.user)
        context = {
            'subscription_info': get_subscription_info(request.user, all_enrollments)
        }
        return render(request, 'training/enter_coupon.html', context)


    # --- 3. RENDER CALENDAR GRID (For Enrolled Users) ---
    # Get current month/year from GET params or default to now
    today = timezone.now().date()
    # today = datetime.now().date() 
    
    try:
        current_year = int(request.GET.get('year', today.year))
        current_month = int(request.GET.get('month', today.month))
    except ValueError:
        current_year = today.year
        current_month = today.month

    # Create Calendar Matrix
    cal = py_calendar.Calendar(firstweekday=6) # Sunday start
    month_days = cal.monthdayscalendar(current_year, current_month)

    # Fetch Events for this month
    batch_ids = active_enrollments.values_list('batch_id', flat=True)
    
    # Filter schedules for this month
    schedules = ClassSchedule.objects.filter(
        batch__id__in=batch_ids,
        start_time__year=current_year,
        start_time__month=current_month
    ).order_by('start_time')

    attended_ids = Attendance.objects.filter(user=request.user).values_list('class_schedule_id', flat=True)

    # Map Events to Dates: { day_int: [list of events] }
    events_map = {}
    for sched in schedules:
        if not sched.start_time: continue
        
        day = sched.start_time.day
        if day not in events_map: events_map[day] = []
        
        # Determine Color Logic
        now_dt = timezone.now()
        
        status = 'upcoming'
        color_class = 'bg-yellow-100 text-yellow-800 border-yellow-300'
        
        if sched.id in attended_ids:
            status = 'joined'
            color_class = 'bg-green-100 text-green-800 border-green-300'
        elif sched.end_time and now_dt > sched.end_time:
            status = 'missed'
            color_class = 'bg-red-100 text-red-800 border-red-300'
            
            
        events_map[day].append({
            'schedule': sched,
            'status': status,
            'color': color_class,
            'is_past': sched.end_time and now_dt > sched.end_time
        })

    # Prepare Month Name
    month_name = py_calendar.month_name[current_month]
    
    # Next/Prev Links
    def get_month_link(y, m):
        if m > 12: return f"?year={y+1}&month=1"
        if m < 1: return f"?year={y-1}&month=12"
        return f"?year={y}&month={m}"
        
    next_link = get_month_link(current_year, current_month + 1)
    prev_link = get_month_link(current_year, current_month - 1)

    context = {
        'enrollments': active_enrollments,
        'month_days': month_days, # Matrix of [0, 0, 1, 2...]
        'events_map': events_map,
        'current_year': current_year,
        'current_month': current_month,
        'month_name': month_name,
        'next_link': next_link,
        'prev_link': prev_link,
        'today': today,
        'subscription_info': get_subscription_info(request.user, active_enrollments)
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'training/partials/calendar_grid.html', context)

    return render(request, 'training/calendar.html', context)


def get_subscription_info(user, enrollments):
    """
    Helper to extract payment/validity info from Coupons linked to enrollments.
    """
    info_list = []
    info_list = []
    for enrollment in enrollments:
        # Fetch ALL coupons (Payment History)
        coupons = Coupon.objects.filter(
            assigned_to=user, 
            batch=enrollment.batch
        ).order_by('-created_at')
        
        payment_history = []
        for coupon in coupons:
            payment_history.append({
                'amount': coupon.payment_amount,
                'date': coupon.payment_date,
                'valid_from': coupon.enrollment_valid_from,
                'valid_until': coupon.enrollment_valid_until,
                'next_due': coupon.next_payment_date
            })

        info = {
            'program': enrollment.batch.workshop.title,
            'batch': enrollment.batch.name,
            'status': 'Active' if enrollment.is_active() else 'Expired',
            'expires_at': enrollment.expires_at,
            'joined_at': enrollment.enrolled_at,
            'history': payment_history
        }
        
        info_list.append(info)
    return info_list


@login_required
def track_attendance(request, schedule_id):
    schedule = get_object_or_404(ClassSchedule, id=schedule_id)
    
    # Check if user is enrolled
    is_enrolled = Enrollment.objects.filter(
        user=request.user, 
        batch=schedule.batch,
        expires_at__gt=timezone.now()
    ).exists()
    
    if not is_enrolled:
        messages.error(request, "Access denied.")
        return redirect('training_program')
        
    # Mark Attendance
    Attendance.objects.get_or_create(user=request.user, class_schedule=schedule)
    
    # Redirect to Meeting
    return redirect(schedule.meeting_link)


@login_required
def payment_history(request):
    """
    View to display user's payment/coupon history.
    Accessible even if subscription is expired.
    """
    # Fetch ALL coupons assigned to the user
    coupons = Coupon.objects.filter(assigned_to=request.user).select_related('batch', 'batch__workshop').order_by('-created_at')
    
    formatted_history = []
    for coupon in coupons:
        status = 'Expired'
        if coupon.enrollment_valid_until and coupon.enrollment_valid_until >= timezone.now().date():
            status = 'Active'
        elif not coupon.enrollment_valid_until and coupon.valid_days:
            # Check if associated enrollment is active? 
            # This is complex because enrollment depends on when it was activated.
            # Simplified check:
            if coupon.is_used:
                 # Try to find enrollment? 
                 # For list view, 'Redeemed' might be better if we can't easily calculate dynamic expiry.
                 status = 'Redeemed'
            else:
                 status = 'Unused'

        formatted_history.append({
            'program': coupon.batch.workshop.title,
            'batch': coupon.batch.name,
            'amount': coupon.payment_amount,
            'date': coupon.payment_date or coupon.created_at.date(), # Fallback to created_at if payment_date null
            'valid_from': coupon.enrollment_valid_from,
            'valid_until': coupon.enrollment_valid_until,
            'code': coupon.code,
            'status': status
        })

    context = {
        'history': formatted_history
    }
    return render(request, 'training/payment_history.html', context)
