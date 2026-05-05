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
from django.db.models import Q, Max
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
    # A. Get Recurring Events
    all_events = []
    
    # 1. Tutor Role: Teaching Schedules (No Date Lock)
    if is_tutor:
        my_patterns = BatchSchedule.objects.filter(tutor=request.user)
        generated = generate_recurring_events(my_patterns, month_start, month_end)
        all_events.extend(generated)

    # 2. Student Role: Enrolled Schedules (Locked to Enrollment Date)
    # Even Tutors/Admins can be students
    for enrollment in active_enrollments:
        enr_start = enrollment.enrolled_at.date()
        enr_end = enrollment.expires_at.date()
        range_start = max(month_start, enr_start)
        range_end = min(month_end, enr_end)
        
        # Avoid duplicate patterns if user is ALSO the tutor for this batch (Unlikely but possible)
        # We assume if they teach it, they want full visibility. 
        # So check if we already added patterns for this batch? 
        # Generating again with restriction is fine, logic below handles duplicates or we just show both.
        # Ideally: If I teach it, I see full. If I don't teach but study, I see restricted.
        
        is_teaching_this_batch = False
        if is_tutor and BatchSchedule.objects.filter(batch=enrollment.batch, tutor=request.user).exists():
             is_teaching_this_batch = True
        
        if not is_teaching_this_batch and range_start <= range_end:
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
    
    # Filter Sessions: Ensure they fall within valid enrollment period (for Student Role)
    # Map Enrollments
    batch_start_map = {}
    batch_end_map = {}
    for enr in active_enrollments:
        d_start = enr.enrolled_at.date()
        d_end = enr.expires_at.date()
        if enr.batch.id not in batch_start_map:
            batch_start_map[enr.batch.id] = d_start
            batch_end_map[enr.batch.id] = d_end
        else:
            batch_start_map[enr.batch.id] = min(batch_start_map[enr.batch.id], d_start)
            batch_end_map[enr.batch.id] = max(batch_end_map[enr.batch.id], d_end)

    valid_sessions = []
    for s in sessions:
        # Check if this is an Enrolled Batch?
        if s.batch.id in batch_start_map:
             # I am a student in this batch.
             # Check if I am ALSO a tutor for it?
             is_teaching = False
             if is_tutor and (s.batch.id in teaching_batch_ids or s.batch.id in session_batch_ids):
                  # I teach this batch, so I see EVERYTHING.
                  is_teaching = True
             
             if is_teaching:
                 valid_sessions.append(s)
             else:
                 # Strictly Student: Apply Date Filter
                 if s.date >= batch_start_map[s.batch.id] and s.date <= batch_end_map[s.batch.id]:
                     valid_sessions.append(s)
        else:
             # Not an enrolled batch (so must be a Teaching batch), allow it.
             valid_sessions.append(s)
             
    sessions = valid_sessions
    
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
    # Check for general 'Special Access' privilege via Enrollment OR Coupon (Fallback)
    has_special_access = active_enrollments.filter(has_special_access=True).exists()
    
    if not has_special_access:
        # Fallback: Check valid coupons directly (in case Sync failed)
        has_special_access = Coupon.objects.filter(
            assigned_to=request.user,
            includes_special_access=True,
            is_used=True 
        ).exists()

    # Base Query: Fetch ALL potentially relevant special classes
    # 1. One Time: In date range
    one_time_q = Q(scheduling_type='one_time', start_datetime__date__range=[month_start, month_end])
    # 2. Recurring: All queries (filtered later)
    recurring_q = Q(scheduling_type='recurring')
    
    special_classes = SpecialClass.objects.filter(one_time_q | recurring_q)

    # Calculate earliest enrollment start for filtering special classes (Students only)
    earliest_enr_date = month_start
    if active_enrollments.exists() and not is_tutor:
        from django.db.models import Min
        earliest_enr_dt = active_enrollments.aggregate(Min('enrolled_at'))['enrolled_at__min']
        if earliest_enr_dt:
            earliest_enr_date = earliest_enr_dt.date()

    # Filter: If NO special access, restrict to explicitly allowed students
    if not has_special_access:
        # Allow if student has access OR if current user is the tutor
        special_classes = special_classes.filter(
            Q(allowed_students=request.user) | Q(tutor=request.user)
        ).distinct()

    for sc in special_classes:
        if sc.scheduling_type == 'one_time':
            if sc.start_datetime and sc.start_datetime.date() >= earliest_enr_date:
                final_events.append({
                    'id': sc.id,
                    'title': sc.title, # Clean title
                    'topic': sc.title,
                    'start': sc.start_datetime,
                    'end': sc.end_datetime,
                    'status': 'scheduled',
                    'tutor': sc.tutor,
                    'meeting_link': sc.meeting_link,
                    'is_special': True
                })
        elif sc.scheduling_type == 'recurring':
            # Generate Pattern Events for this Month
            validity_limit = month_end 
            
            if sc.tutor != request.user and active_enrollments.exists():
                max_enr = active_enrollments.aggregate(Max('expires_at'))['expires_at__max']
                if max_enr:
                    limit_date = max_enr.date()
                    if limit_date < month_end:
                        validity_limit = limit_date

            # Generate
            curr = max(month_start, earliest_enr_date)
            while curr <= validity_limit:
                 if curr.weekday() == sc.day_of_week:
                     start_dt = timezone.make_aware(datetime.combine(curr, sc.start_time))
                     if sc.end_time:
                         end_dt = timezone.make_aware(datetime.combine(curr, sc.end_time))
                     else:
                         end_dt = start_dt + timedelta(hours=1)

                     final_events.append({
                        'id': sc.id,
                        'title': sc.title, # Clean title
                        'topic': sc.title,
                        'start': start_dt,
                        'end': end_dt, 
                        'status': 'scheduled',
                        'tutor': sc.tutor,
                        'meeting_link': sc.meeting_link,
                        'is_special': True
                     })
                 curr += timedelta(days=1)

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
    # Check type via query param to avoid ID collision
    # ?type=special -> SpecialClass
    is_special = request.GET.get('type') == 'special'
    
    if is_special:
        special_class = get_object_or_404(SpecialClass, id=schedule_id)
        # TODO: Add logic to track attendance for special class if needed (need a ManyToMany field or Attendance model update)
        # For now just redirect
        if special_class.meeting_link:
             return HttpResponseRedirect(special_class.meeting_link)
        else:
             messages.warning(request, "Meeting link not available.")
             return redirect('training_program')

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
        
    # C. Special Classes (Added for Tutor Agenda)
    my_special_classes = SpecialClass.objects.filter(tutor=request.user)
    for sc in my_special_classes:
        is_today = False
        start_dt = None
        end_dt = None
        
        if sc.scheduling_type == 'one_time':
            if sc.start_datetime and sc.start_datetime.date() == today:
                is_today = True
                start_dt = sc.start_datetime
                end_dt = sc.end_datetime
        elif sc.scheduling_type == 'recurring':
            if sc.day_of_week == today.weekday():
                is_today = True
                start_dt = timezone.make_aware(datetime.combine(today, sc.start_time))
                if sc.end_time:
                    end_dt = timezone.make_aware(datetime.combine(today, sc.end_time))
                else:
                    end_dt = start_dt + timedelta(hours=1)
        
        if is_today and start_dt:
            teaching_list.append({
                'start': start_dt,
                'end': end_dt,
                'title': sc.title,
                'batch_id': None, # Special classes check
                'batch_name': "Special Class",
                'meeting_link': sc.meeting_link,
                'status': 'scheduled',
                'is_special': True
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

    # 1.5 Check for Expiring Enrollments (Notification Logic)
    expiring_enrollments = []
    for enrollment in active_enrollments:
        days_remaining = (enrollment.expires_at.date() - now.date()).days
        if 0 <= days_remaining <= 7:
            expiring_enrollments.append({
                'batch_name': enrollment.batch.name,
                'days_left': days_remaining,
                'program_title': enrollment.batch.workshop.title
            })

    # 2. Upcoming Classes (Global Preview)
    # Fetch upcoming for ALL active batches
    upcoming_classes = []
    
    # A. Regular Batches
    if active_enrollments.exists():
        end_range = now + timedelta(days=14)
        patterns = BatchSchedule.objects.filter(batch__enrollments__in=active_enrollments).distinct()
        generated = generate_recurring_events(patterns, now.date(), end_range.date())
        
        # Filter out classes that have already ended
        generated = [evt for evt in generated if evt['end'] > now]
        upcoming_classes.extend(generated)
        
    # B. Special Classes (Fix: Fetch and Append)
    # Check Access
    has_special_access = active_enrollments.filter(has_special_access=True).exists()
    if not has_special_access:
        has_special_access = Coupon.objects.filter(
            assigned_to=request.user, includes_special_access=True, is_used=True 
        ).exists()
        
    end_date_sc = (now + timedelta(days=14)).date()
    
    # 1. One Time
    one_time_q = Q(scheduling_type='one_time', start_datetime__date__range=[now.date(), end_date_sc], start_datetime__gt=now) # Future only
    recurring_q = Q(scheduling_type='recurring')
    
    special_qs = SpecialClass.objects.filter(one_time_q | recurring_q)
    if not has_special_access:
        special_qs = special_qs.filter(allowed_students=request.user)
        
    for sc in special_qs:
        if sc.scheduling_type == 'one_time':
            # Already filtered by date/time
             upcoming_classes.append({
                'id': sc.id,
                'title': sc.title, # Clean title
                'topic': sc.title,
                'start': sc.start_datetime,
                'end': sc.end_datetime,
                'status': 'scheduled',
                'meeting_link': sc.meeting_link,
                'is_special': True
             })
        elif sc.scheduling_type == 'recurring':
             # Generate for next 14 days
             curr = now.date()
             # Logic for validity same as calendar
             # Simplified: just show up to 14 days or expiry
             limit_date = end_date_sc
             if active_enrollments.exists():
                  max_enr = active_enrollments.aggregate(Max('expires_at'))['expires_at__max']
                  if max_enr and max_enr.date() < limit_date:
                      limit_date = max_enr.date()
             
             while curr <= limit_date:
                 if curr.weekday() == sc.day_of_week:
                     start_dt = timezone.make_aware(datetime.combine(curr, sc.start_time))
                     if sc.end_time:
                         end_dt = timezone.make_aware(datetime.combine(curr, sc.end_time))
                     else:
                         end_dt = start_dt + timedelta(hours=1)
                     
                     if end_dt > now:
                         upcoming_classes.append({
                            'id': sc.id,
                            'title': sc.title, # Clean title
                            'topic': sc.title,
                            'start': start_dt,
                            'end': end_dt, 
                            'status': 'scheduled',
                            'meeting_link': sc.meeting_link,
                            'is_special': True
                         })
                 curr += timedelta(days=1)

    # Sort and take top 2
    upcoming_classes.sort(key=lambda x: x['start'])
    upcoming_classes = upcoming_classes[:2]

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
    # 4. Next Holiday
    next_holiday = Holiday.objects.filter(date__gte=now.date()).order_by('date').first()

    # 5. Total Classes This Month (Stats)
    # Calculate total classes for the current month to show in header
    month_start = date(now.year, now.month, 1)
    _, last_day = py_calendar.monthrange(now.year, now.month)
    month_end = date(now.year, now.month, last_day)
    
    total_classes = 0
    
    # A. Recurring Patterns
    # reusing active_enrollments
    for enrollment in active_enrollments:
        enr_start = enrollment.enrolled_at.date()
        enr_end = enrollment.expires_at.date()
        range_start = max(month_start, enr_start)
        range_end = min(month_end, enr_end)
        
        if range_start <= range_end:
            patterns = BatchSchedule.objects.filter(batch=enrollment.batch)
            generated = generate_recurring_events(patterns, range_start, range_end)
            total_classes += len(generated)

    # B. Sessions (Exceptions/Extras)
    # Note: If a session overrides a pattern, we ideally shouldn't double count.
    # But simple addition often suffices if override just replaces.
    # However, if 'rescheduled', it technically moves the class.
    # For a simple "Total Classes" stat, counting sessions + patterns is slightly inaccurate if overrides exist.
    # Better: List all potential dates and uniquify? 
    # Or: Check overrides.
    
    # Let's do a more robust count:
    # 1. Gather all pattern events
    # 2. Gather all session events
    # 3. Handle overrides
    
    monthly_events = []
    
    # (Repeat generation for proper counting)
    for enrollment in active_enrollments:
        enr_start = enrollment.enrolled_at.date()
        enr_end = enrollment.expires_at.date()
        range_start = max(month_start, enr_start)
        range_end = min(month_end, enr_end)
        if range_start <= range_end:
            patterns = BatchSchedule.objects.filter(batch=enrollment.batch)
            generated = generate_recurring_events(patterns, range_start, range_end)
            monthly_events.extend(generated)
            
    all_batch_ids = list(active_enrollments.values_list('batch_id', flat=True))
    sessions = ClassSession.objects.filter(
        batch__id__in=all_batch_ids,
        date__range=[month_start, month_end]
    )
    
    # Filter sessions by enrollment
    batch_map = {e.batch.id: (e.enrolled_at.date(), e.expires_at.date()) for e in active_enrollments}
    valid_sessions = []
    for s in sessions:
        if s.batch.id in batch_map:
             estart, eend = batch_map[s.batch.id]
             if s.date >= estart and s.date <= eend:
                 valid_sessions.append(s)
                 
    # Map for overrides
    session_map = {}
    for s in valid_sessions:
        key = (s.batch.id, s.date)
        if key not in session_map: session_map[key] = []
        session_map[key].append(s)
        
    final_count = 0
    # Count Patterns (if not overridden)
    for evt in monthly_events:
        is_overridden = False
        if (evt['batch_id'], evt['date']) in session_map:
             for s in session_map[(evt['batch_id'], evt['date'])]:
                 if s.status == 'cancelled' or s.status == 'rescheduled':
                     is_overridden = True
        if not is_overridden:
            final_count += 1
            
    # Count Sessions (Concrete)
    final_count += len(valid_sessions)
    
    # C. Special Classes
    # Helper to check special class count
    # Calculate earliest enrollment start for filtering (Students only)
    earliest_enr_date = month_start
    if active_enrollments.exists():
        from django.db.models import Min
        earliest_enr_dt = active_enrollments.aggregate(Min('enrolled_at'))['enrolled_at__min']
        if earliest_enr_dt:
            earliest_enr_date = earliest_enr_dt.date()

    if not has_special_access:
         special_qs_month = SpecialClass.objects.filter(
             (Q(scheduling_type='one_time', start_datetime__date__range=[month_start, month_end]) |
              Q(scheduling_type='recurring')),
             allowed_students=request.user
         )
    else:
         special_qs_month = SpecialClass.objects.filter(
             Q(scheduling_type='one_time', start_datetime__date__range=[month_start, month_end]) |
             Q(scheduling_type='recurring')
         )

    for sc in special_qs_month:
        if sc.scheduling_type == 'one_time':
             if sc.start_datetime and sc.start_datetime.date() >= earliest_enr_date:
                 final_count += 1
        elif sc.scheduling_type == 'recurring':
             curr = max(month_start, earliest_enr_date)
             limit_date = month_end
             if active_enrollments.exists():
                 max_enr = active_enrollments.aggregate(Max('expires_at'))['expires_at__max']
                 if max_enr and max_enr.date() < limit_date:
                     limit_date = max_enr.date()
             
             while curr <= limit_date:
                 if curr.weekday() == sc.day_of_week:
                     final_count += 1
                 curr += timedelta(days=1)

    # 6. 📊 Dedication Graph Data
    # Heatmap for last 365 days
    end_date_graph = now.date()
    start_date_graph = end_date_graph - timedelta(days=364) # 52 weeks approx
    
    # Fetch all attendance dates
    attendance_dates = Attendance.objects.filter(
        user=request.user,
        class_session__date__range=[start_date_graph, end_date_graph]
    ).values_list('class_session__date', flat=True)
    
    # Process into map: { date_obj: count }
    # Since multiple classes can happen in one day, we count density
    date_counts = {}
    for d in attendance_dates:
        date_counts[d] = date_counts.get(d, 0) + 1
        
    # Calculate Streaks (Weekly)
    # Logic: Count consecutive WEEKS with at least one attendance.
    # Because classes are 2-3 times a week, a daily streak is impossible.
    
    current_streak = 0
    longest_streak = 0
    
    # Get all unique weeks attended (Year, WeekNum)
    # attendance_dates is list of dates.
    attended_weeks = set()
    for d in attendance_dates:
        attended_weeks.add(d.isocalendar()[:2]) # (Year, WeekNum)
        
    sorted_weeks = sorted(list(attended_weeks), reverse=True)
    
    if sorted_weeks:
        # 1. Provide Current Streak
        # Check if the most recent attended week is "current" enough (This week or Last week)
        this_year, this_week, _ = now.isocalendar()
        last_attended = sorted_weeks[0]
        
        # Helper to get previous week
        def get_prev_week(y, w):
            if w > 1: return (y, w-1)
            return (y-1, 52) # approx, or use date math logic for exactness if needed. 
                             # For simple streak, date math is safer.
        
        # Better: Convert weeks back to Monday dates to check continuity
        # Or just use date comparisons?
        # Let's use logic: If last_attended is within last 14 days? 
        # No, strict week number.
        
        is_active = False
        if last_attended == (this_year, this_week):
            is_active = True
        else:
             # Check if it was last week
             # Using date math to be safe against year boundaries
             # Last attended week's "Monday"
             # Simply: (ThisWeek) - 1 == (LastAttended)?
             # Complex due to Year change.
             
             # Robust approach:
             # Iterate backwards from This Week.
             pass

        # Re-calc Streaks by iterating sorted weeks
        # Convert set to sorted list descending
        
        # Calculate Longest Streak
        # Iterate and count consecutive drops by 1 week
        # We need a reliable "weeks_diff" function
        pass

    # Simplified Robust Logic for Streaks:
    # from datetime import timedelta <- REDUNDANT
    
    # Map all dates to their "Monday" (Week Start)
    attended_mondays = set()
    for d in attendance_dates:
        monday = d - timedelta(days=d.weekday())
        attended_mondays.add(monday)
        
    sorted_mondays = sorted(list(attended_mondays), reverse=True)
    
    # 1. Current Streak
    # Valid only if latest attendance is This Week (Monday) or Last Week (Monday)
    current_monday = now.date() - timedelta(days=now.date().weekday())
    last_monday = current_monday - timedelta(days=7)
    
    streak_mondays = sorted_mondays # copy
    current_streak = 0
    
    if not streak_mondays:
        current_streak = 0
    else:
        latest = streak_mondays[0]
        if latest == current_monday or latest == last_monday:
            # Streak is active
            current_streak = 1
            expected = latest - timedelta(days=7)
            for i in range(1, len(streak_mondays)):
                if streak_mondays[i] == expected:
                    current_streak += 1
                    expected -= timedelta(days=7)
                else:
                    break
        else:
            current_streak = 0
            
    # 2. Longest Streak
    longest_streak = 0
    temp_streak = 0
    if streak_mondays:
        temp_streak = 1
        for i in range(0, len(streak_mondays) - 1):
             curr_m = streak_mondays[i]
             next_m = streak_mondays[i+1] # older
             diff = (curr_m - next_m).days
             if diff == 7:
                 temp_streak += 1
             else:
                 longest_streak = max(longest_streak, temp_streak)
                 temp_streak = 1
        longest_streak = max(longest_streak, temp_streak)

    
    # Build Graph Grid (Rows=7 Days, Cols=53 Weeks)
    dedication_grid = []
    curr = start_date_graph
    while curr <= end_date_graph:
        count = date_counts.get(curr, 0)
        level = 0
        if count == 1: level = 1
        elif count == 2: level = 2
        elif count >= 3: level = 3
        
        dedication_grid.append({
            'date': curr,
            'count': count,
            'level': level
        })
        curr += timedelta(days=1)

    context = {
        'expiring_enrollments': expiring_enrollments,
        'enrollments': active_enrollments,
        'upcoming_classes': upcoming_classes,
        'mentor': mentor,
        'next_holiday': next_holiday,
        'total_classes_this_month': final_count,
        'current_month_name': now.strftime('%B'),
        'dedication_grid': dedication_grid,
        'current_streak': current_streak,
        'longest_streak': longest_streak
    }
    return render(request, 'training/student_dashboard.html', context)
