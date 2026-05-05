from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta, date, datetime, time
import calendar as py_calendar
from .models import (
    Coupon, Enrollment, Batch, BatchSchedule, ClassSession, SpecialClass, Attendance,
    HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ, Holiday
)
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
import json
from django.http import JsonResponse, HttpResponseRedirect
# We need to add imports if missing, or use existing.
# Existing: import json, from django.http import HttpResponseRedirect
from django.http import JsonResponse

from django.core.exceptions import PermissionDenied

# Holidays Removed as per user request

def check_is_tutor(user):
    if user.is_superuser: return True
    if user.groups.filter(name='Tutor').exists(): return True
    if BatchSchedule.objects.filter(tutor=user).exists(): return True
    return False

def generate_recurring_events(batch_schedules, start_date, end_date):
    """
    Helper to generate event objects from patterns for a given date range.
    Returns list of dicts: {'date', 'start', 'end', 'title', 'tutor', 'status', 'batch_id', 'is_pattern': True}
    """
    events = []
    # Pre-process schedules by day: { 0: [sched1, sched2], 1: [...] }
    sched_map = {}
    for s in batch_schedules:
        d = s.day_of_week
        if d not in sched_map: sched_map[d] = []
        sched_map[d].append(s)
    
    curr = start_date
    while curr <= end_date:
        wd = curr.weekday()
        if wd in sched_map:
            for s in sched_map[wd]:
                # Construct DateTime
                # Note: Timezone handling omitted for simplicity (using naive)
                start_dt = timezone.make_aware(datetime.combine(curr, s.start_time))
                end_dt = timezone.make_aware(datetime.combine(curr, s.end_time))
                
                events.append({
                    'original_sched': s,
                    'batch_id': s.batch.id,
                    'date': curr,
                    'start': start_dt,
                    'end': end_dt,
                    'title': s.topic,
                    'topic': s.topic, # Explicit topic key for template
                    'tutor': s.tutor,
                    'meeting_link': s.meeting_link,
                    'status': 'scheduled',
                    'is_pattern': True,
                    'batch_name': s.batch.name,
                    'resources': s.batch.resources.all() # Expose compatible queryset
                })
        curr += timedelta(days=1)
    return events

@login_required
def training_program(request):
    is_tutor = check_is_tutor(request.user)
    # Redirect removed to allow tutors to see the calendar
    
    # --- 1. HANDLE COUPON SUBMISSION ---
    if request.method == 'POST' and 'coupon_code' in request.POST:
        code = request.POST.get('coupon_code', '').strip().upper()
        try:
            coupon = Coupon.objects.get(code=code)
            if coupon.is_used:
                messages.error(request, "This code has already been used.")
            elif coupon.assigned_to and coupon.assigned_to != request.user:
                messages.error(request, "This code is not assigned to you.")
                # We do NOT check expired here for redemption? 
                # If expired code is used, it grants access to past batch? Maybe.
                # But let's block strictly expired logic if needed.
            elif coupon.enrollment_valid_until and coupon.enrollment_valid_until < timezone.now().date():
                 messages.error(request, "This coupon has expired.")
            else:
                expires_dt = None
                if coupon.enrollment_valid_until:
                    expires_dt = timezone.make_aware(datetime.combine(coupon.enrollment_valid_until, datetime.max.time()))
                else:
                    expires_dt = timezone.now() + timedelta(days=coupon.valid_days)

                enrollment, created = Enrollment.objects.get_or_create(
                    user=request.user,
                    batch=coupon.batch,
                    defaults={'expires_at': expires_dt}
                )

                if created and request.user.email:
                    # Welcome Email logic (omitted for brevity, same as before)
                    pass

                coupon.is_used = True
                coupon.save()
                messages.success(request, f"Welcome to {coupon.batch.workshop.title}! You're in.")
                return redirect('training_program')

        except Coupon.DoesNotExist:
            messages.error(request, "Invalid access code.")
        return render(request, 'training/enter_coupon.html')

    # --- 2. CHECK ENROLLMENT ---
    now = timezone.now()
    active_enrollments = Enrollment.objects.filter(
        user=request.user, 
        expires_at__gt=now
    ).select_related('batch', 'batch__workshop')

    if not is_tutor and not active_enrollments.exists():
        all_enrollments = Enrollment.objects.filter(user=request.user)
        context = {'subscription_info': get_subscription_info(request.user, all_enrollments)}
        return render(request, 'training/enter_coupon.html', context)

    # --- 3. RENDER CALENDAR GRID ---
    today = now.date()
    try:
        current_year = int(request.GET.get('year', today.year))
        current_month = int(request.GET.get('month', today.month))
    except ValueError:
        current_year = today.year
        current_month = today.month

    cal = py_calendar.Calendar(firstweekday=6)
    month_days = cal.monthdayscalendar(current_year, current_month)

    # Date Range for View
    month_start = date(current_year, current_month, 1)
    # End of month
    _, last_day = py_calendar.monthrange(current_year, current_month)
    month_end = date(current_year, current_month, last_day)

    # A. Get Recurring Events
    all_events = []
    
    if is_tutor:
        # For Tutors: Show all classes they teach
        my_patterns = BatchSchedule.objects.filter(tutor=request.user)
        generated = generate_recurring_events(my_patterns, month_start, month_end)
        all_events.extend(generated)
    else:
        # For Students: Show only enrolled classes
        for enrollment in active_enrollments:
            enr_start = enrollment.enrolled_at.date()
            enr_end = enrollment.expires_at.date()
            range_start = max(month_start, enr_start)
            range_end = min(month_end, enr_end)
            if range_start <= range_end:
                patterns = BatchSchedule.objects.filter(batch=enrollment.batch)
                generated = generate_recurring_events(patterns, range_start, range_end)
                all_events.extend(generated)

    # B. Handling EXCEPTIONS (ClassSession)
    # Fetch sessions for these batches in this month
    all_batch_ids = list(active_enrollments.values_list('batch_id', flat=True))
    if is_tutor:
        teaching_batch_ids = BatchSchedule.objects.filter(tutor=request.user).values_list('batch_id', flat=True)
        session_batch_ids = ClassSession.objects.filter(tutor=request.user).values_list('batch_id', flat=True)
        all_batch_ids = list(set(all_batch_ids) | set(teaching_batch_ids) | set(session_batch_ids))

    sessions = ClassSession.objects.filter(
        batch__id__in=all_batch_ids,
        date__range=[month_start, month_end]
    )
    
    # Process Exceptions:
    # 1. Map session to (batch_id, date, start_time) to enable overriding
    # 2. Add extra sessions (extras)
    
    session_map = {} # Key: (batch_id, date) -> List of sessions
    for s in sessions:
        key = (s.batch.id, s.date)
        if key not in session_map: session_map[key] = []
        session_map[key].append(s)

    final_events = []
    
    # 1. Filter generated events if overridden
    for evt in all_events:
        # Check if any session exists that overrides this?
        # A session overrides a pattern if it links to it via `pattern_ref` OR simply if logic dictates.
        # User requirement: "Admin can reschedule that specific class"
        # Since pattern generates events, how do we know which session replaces which pattern event?
        # Matching by (Batch, Date, StartTime) is fuzzy if time changed.
        # Ideally, we rely on the fact that if a session exists for a specific day, it might be the only truth?
        # No, extra classes coexist.
        # We need to know if a session IS a replacement.
        # Simplified logic: Show pattern UNLESS cancel/reschedule logic found. 
        # For MVP, let's just show BOTH, but highlight Sessions.
        # Actually, let's just list the generated events. 
        # If we implement robust rescheduling, we'd need a "Pattern Exclusion" model.
        # For now, let's assume ClassSession is purely ADDITIVE or Manual. 
        # Wait, user said "Reschedule... Only the missed class is rescheduled... Automted recurring continues".
        # This implies the original slot on that day is GONE.
        # To do this without complex exclusion tables:
        # We can scan ClassSessions. If one has `original_date` matching the pattern event, we hide the pattern event.
        
        is_overridden = False
        # Check sessions for this batch
        if (evt['batch_id'], evt['date']) in session_map:
            for s in session_map[(evt['batch_id'], evt['date'])]:
                if s.status == 'rescheduled' and s.original_date == evt['date']:
                     # This session claims to be the rescheduled version of something on this date.
                     # Assuming 1 class per day per batch for simplicity? 
                     # Or check if start_times match?
                     # Let's match roughly.
                     is_overridden = True
                if s.status == 'cancelled' and s.date == evt['date']:
                     is_overridden = True

        if not is_overridden:
            evt['id'] = evt['original_sched'].id
            final_events.append(evt)

    # 2. Add Sessions (The concrete ones)
    for s in sessions:
        start_dt = timezone.make_aware(datetime.combine(s.date, s.start_time))
        end_dt = timezone.make_aware(datetime.combine(s.date, s.end_time))
        final_events.append({
            'id': s.id,
            'original_sched': None,
            'class_session': s,
            'batch_id': s.batch.id,
            'date': s.date,
            'start': start_dt,
            'end': end_dt,
            'title': s.topic,
            'topic': s.topic,
            'tutor': s.tutor,
            'meeting_link': s.meeting_link,
            'status': s.status,
            'is_pattern': False,
            'resources': s.batch.resources.all()
        })
    
    # C. Special Classes
    special_access = active_enrollments.filter(has_special_access=True).exists()
    if special_access:
        special_classes = SpecialClass.objects.filter(
            start_datetime__date__range=[month_start, month_end]
        )
        for sc in special_classes:
            final_events.append({
                'title': f"⭐ {sc.title}",
                'start': sc.start_datetime,
                'end': sc.end_datetime,
                'status': 'special',
                'tutor': sc.tutor,
                'meeting_link': sc.meeting_link
            })

    # Fetch user attendances for the current month
    user_attendances = Attendance.objects.filter(
        user=request.user,
        class_session__date__range=[month_start, month_end]
    ).values_list('class_session_id', flat=True)

    # Prepare Events Map for Template
    events_map = {}
    for evt in final_events:
        d = evt['start'].day
        if d not in events_map: events_map[d] = []
        
        # Determine display status
        display_status = evt['status']
        is_past = evt['end'] < timezone.now()
        
        if is_past:
             if 'class_session' in evt:
                 # It's a concrete session, check if user attended
                 if evt['class_session'].id in user_attendances:
                     display_status = 'joined'
                 else:
                     display_status = 'missed'
             else:
                 # It's a pattern event (no concrete session created yet)
                 # If it's in the past, it's missed unless a session was created for it
                 # (But we already handled overrides, so if we're here, no session exists)
                 display_status = 'missed'
        
        events_map[d].append({
            'schedule': evt, 
            'status': display_status,
            'is_past': is_past
        })

    month_name = py_calendar.month_name[current_month]
    
    # 🎊 Fetch Holidays from Database
    holidays = Holiday.objects.filter(date__range=[month_start, month_end])
    month_holidays = {h.date.day: h.name for h in holidays}

    def get_month_link(y, m):
        if m > 12: return f"?year={y+1}&month=1"
        if m < 1: return f"?year={y-1}&month=12"
        return f"?year={y}&month={m}"

    context = {
        'enrollments': active_enrollments,
        'month_days': month_days,
        'events_map': events_map,
        'month_holidays': month_holidays,
        'current_year': current_year,
        'current_month': current_month,
        'month_name': month_name,
        'next_link': get_month_link(current_year, current_month + 1),
        'prev_link': get_month_link(current_year, current_month - 1),
        'today': today,
        'subscription_info': get_subscription_info(request.user, active_enrollments)
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'training/partials/calendar_grid.html', context)

    return render(request, 'training/calendar.html', context)

def get_subscription_info(user, enrollments):
    info_list = []
    for enrollment in enrollments:
        coupons = Coupon.objects.filter(assigned_to=user, batch=enrollment.batch).order_by('-created_at')
        payment_history = [{
            'amount': c.payment_amount,
            'date': c.payment_date,
            'valid_from': c.enrollment_valid_from,
            'valid_until': c.enrollment_valid_until,
        } for c in coupons]

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
    # Try to find a Session first
    session = ClassSession.objects.filter(id=schedule_id).first()
    if session:
        Attendance.objects.get_or_create(user=request.user, class_session=session)
        if session.meeting_link:
            return HttpResponseRedirect(session.meeting_link)
    
    # If it was a pattern ID, find the BatchSchedule
    pattern = BatchSchedule.objects.filter(id=schedule_id).first()
    if pattern and pattern.meeting_link:
        return HttpResponseRedirect(pattern.meeting_link)

    messages.warning(request, "Meeting link not available.")
    return redirect('training_program')

@login_required
def payment_history(request):
    coupons = Coupon.objects.filter(assigned_to=request.user).select_related('batch', 'batch__workshop').order_by('-created_at')
    formatted_history = []
    for coupon in coupons:
        status = 'Expired'
        if coupon.enrollment_valid_until and coupon.enrollment_valid_until >= timezone.now().date():
            status = 'Active'
        elif not coupon.enrollment_valid_until and coupon.valid_days:
            if coupon.is_used: status = 'Redeemed'
            else: status = 'Unused'

        formatted_history.append({
            'program': coupon.batch.workshop.title,
            'batch': coupon.batch.name,
            'amount': coupon.payment_amount,
            'date': coupon.payment_date or coupon.created_at.date(),
            'valid_from': coupon.enrollment_valid_from,
            'valid_until': coupon.enrollment_valid_until,
            'code': coupon.code,
            'status': status
        })
    return render(request, 'training/payment_history.html', {'history': formatted_history})

def training_overview(request):
    hero = HeroSection.objects.filter(is_active=True).first()
    about = AboutSection.objects.filter(is_active=True).first()
    classes = ClassType.objects.filter(is_active=True).order_by('order')
    testimonials = Testimonial.objects.filter(is_active=True)
    gallery = GalleryImage.objects.filter(is_active=True).order_by('order')
    faqs = FAQ.objects.filter(is_active=True).order_by('order')
    context = {'hero': hero, 'about': about, 'classes': classes, 'testimonials': testimonials, 'gallery': gallery, 'faqs': faqs}
    return render(request, 'training/training_overview.html', context)

@login_required
def tutor_dashboard(request):
    if not check_is_tutor(request.user): return redirect('training_program')
    
    now = timezone.now()
    today = now.date()
    
    # 1. Fetch Today's Teaching Schedule (List View)
    end_date = today # Only today
    
    # A. Patterns
    my_patterns = BatchSchedule.objects.filter(tutor=request.user)
    generated = generate_recurring_events(my_patterns, today, end_date)
    
    # B. Sessions (Overrides/Concrete)
    my_sessions = ClassSession.objects.filter(tutor=request.user, date__range=[today, end_date])
    
    # Merge for List View
    teaching_list = []
    
    # Add generated patterns
    for evt in generated:
        # Check if cancelled/rescheduled
        # Simplified check
        teaching_list.append({
            'start': evt['start'],
            'end': evt['end'],
            'title': evt['title'],
            'batch_id': evt['batch_id'],
            'batch_name': evt['batch_name'],
            'meeting_link': evt['meeting_link'],
            'status': 'scheduled'
        })
        
    # Add Sessions
    for s in my_sessions:
        teaching_list.append({
            'start': timezone.make_aware(datetime.combine(s.date, s.start_time)),
            'end': timezone.make_aware(datetime.combine(s.date, s.end_time)),
            'title': s.topic,
            'batch_id': s.batch.id,
            'batch_name': s.batch.name,
            'meeting_link': s.meeting_link,
            'status': s.status
        })
        
    # Sort chronological
    teaching_list.sort(key=lambda x: x['start'])
    upcoming_teaching_list = teaching_list # No limit, show all today

    my_batches_schedules = BatchSchedule.objects.filter(tutor=request.user).values_list('batch_id', flat=True)
    my_sessions_batches = ClassSession.objects.filter(tutor=request.user).values_list('batch_id', flat=True)
    my_batch_ids = list(set(my_batches_schedules) | set(my_sessions_batches))
    my_batches = Batch.objects.filter(id__in=my_batch_ids).select_related('workshop')

    # 3. Calculate Average Attendance (Last 10 sessions)
    past_sessions = ClassSession.objects.filter(tutor=request.user, date__lt=today).order_by('-date')[:10]
    total_att_pct = 0
    if past_sessions.exists():
        for s in past_sessions:
            total_students_count = Enrollment.objects.filter(batch=s.batch).count()
            present_students = Attendance.objects.filter(class_session=s).count()
            if total_students_count > 0:
                total_att_pct += (present_students / total_students_count) * 100
        avg_att = round(total_att_pct / past_sessions.count(), 1)
    else:
        avg_att = 0

    # 4. Fetch Recently Enrolled Students (Last 5)
    recent_students = Enrollment.objects.filter(batch__id__in=my_batch_ids).select_related('user', 'batch').order_by('-enrolled_at')[:5]

    context = {
        'upcoming_teaching_list': upcoming_teaching_list,
        'my_batches': my_batches,
        'recent_students': recent_students,
        'total_students': Enrollment.objects.filter(batch__id__in=my_batch_ids).distinct().count(),
        'avg_attendance': avg_att,
        'total_sessions': ClassSession.objects.filter(tutor=request.user, date__lt=today).count()
    }
    return render(request, 'training/tutor_dashboard.html', context)

@login_required
def get_batch_students(request, batch_id):
    if not check_is_tutor(request.user):
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    batch = get_object_or_404(Batch, id=batch_id)
    # Security: Ensure this tutor is actually assigned to this batch
    is_authorized = BatchSchedule.objects.filter(batch=batch, tutor=request.user).exists() or \
                    ClassSession.objects.filter(batch=batch, tutor=request.user).exists() or \
                    request.user.is_superuser
    
    if not is_authorized:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    enrollments = Enrollment.objects.filter(batch=batch).select_related('user').order_by('user__last_name')
    students = []
    for enr in enrollments:
        students.append({
            'name': enr.user.get_full_name() or enr.user.username,
            'email': enr.user.email,
            'joined': enr.enrolled_at.strftime('%d %b %Y'),
            'expires': enr.expires_at.strftime('%d %b %Y'),
        })
    
    return JsonResponse({
        'batch_name': batch.name,
        'students': students,
        'count': len(students)
    })

@staff_member_required
def get_package_details(request, package_id):
    from .models import WorkshopPackage
    pkg = get_object_or_404(WorkshopPackage, id=package_id)
    return JsonResponse({
        'price': pkg.price,
        'duration': pkg.duration_days
    })

@login_required
def student_dashboard(request):
    if check_is_tutor(request.user):
        return redirect('tutor_dashboard')
        
    # 1. Active Enrollments
    now = timezone.now()
    active_enrollments = Enrollment.objects.filter(
        user=request.user, 
        expires_at__gt=now
    ).select_related('batch', 'batch__workshop')

    # 2. Upcoming Classes (Global Preview)
    # Fetch upcoming for ALL active batches
    upcoming_classes = []
    if active_enrollments.exists():
        end_range = now + timedelta(days=14)
        patterns = BatchSchedule.objects.filter(batch__enrollments__in=active_enrollments).distinct()
        generated = generate_recurring_events(patterns, now.date(), end_range.date())
        
        # Sort and take top 2
        generated.sort(key=lambda x: x['start'])
        upcoming_classes = generated[:2]

    # 3. Fetch Mentor (Primary Tutor)
    # Finding the first assigned tutor from the student's active batches
    mentor = None
    if active_enrollments.exists():
        # Look for a schedule with a tutor assigned
        pattern_with_tutor = BatchSchedule.objects.filter(
            batch__enrollments__in=active_enrollments, 
            tutor__isnull=False
        ).select_related('tutor').first()
        
        if pattern_with_tutor:
            mentor = pattern_with_tutor.tutor
    
    # 4. Next Holiday
    next_holiday = Holiday.objects.filter(date__gte=now.date()).order_by('date').first()

    context = {
        'enrollments': active_enrollments,
        'upcoming_classes': upcoming_classes,
        'mentor': mentor,
        'next_holiday': next_holiday,
    }
    return render(request, 'training/student_dashboard.html', context)
