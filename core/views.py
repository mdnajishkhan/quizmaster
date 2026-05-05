from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.paginator import Paginator

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.db import models
from django.db.models import Sum, Count, F, Avg, Max
from django.db.models.functions import Coalesce
from core.models import Quiz, Question, Choice, Attempt, Answer, QuizAccessGrant, Category
from core.models import Quiz, Question, Choice, Attempt, Answer, QuizAccessGrant, Category
from training.models import Enrollment, BatchSchedule, ClassSession
from training.views import generate_recurring_events
from core.forms import UserRegistrationForm, UserLoginForm, EmailValidationPasswordResetForm, CustomSetPasswordForm, UserUpdateForm, ProfileUpdateForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth.models import User
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy
from django.http import FileResponse
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.clickjacking import xframe_options_sameorigin
from core.utils import generate_certificate_pdf, EmailThread

# 🧠 Utility: Send Hackathon Email
def send_hackathon_result_email(request, attempt):
    if attempt.quiz.quiz_type != 'hackathon':
        return

    try:
        current_site = get_current_site(request)
        total_questions = attempt.quiz.questions.count()
        percentage = round((attempt.score / total_questions) * 100, 1) if total_questions > 0 else 0
        
        mail_subject = f"Your Hackathon Results: {attempt.quiz.title}"
        html_message = render_to_string('core/hackathon_result_email.html', {
            'user': request.user,
            'quiz': attempt.quiz,
            'attempt': attempt,
            'score': attempt.score,
            'total': total_questions,
            'percentage': percentage,
            'passed': attempt.passed,
            'domain': current_site.domain,
        })
        plain_message = f"You scored {percentage}% in {attempt.quiz.title}. Check your results on the dashboard."
        
        EmailThread(
            subject=mail_subject,
            message=plain_message,
            from_email='recgetup.music@gmail.com',
            recipient_list=[request.user.email],
            fail_silently=True,
            html_message=html_message
        ).start()
    except Exception as e:
        print(f"Error sending hackathon result email: {e}")

from training.models import HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ, ContactQuery
from django.contrib import messages
# from training.tasks import send_contact_email_task # Deprecated

# 🏠 Home page (Public Access)
def home(request):
    if request.user.is_authenticated:
        return redirect('student_dashboard')
    
    if request.method == 'POST':
        # Handle Contact Form
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone = request.POST.get('phone')
        subject = request.POST.get('subject', 'General Inquiry')
        message = request.POST.get('message')
        
        if name and email and message:
            # 1. Save to DB (Fast)
            ContactQuery.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message
            )
            
            # 2. Schedule Emails (Async - Very Fast Response)
            # Notification to Admin
            # 2. Schedule Emails (Async - Very Fast Response)
            # Notification to Admin
            EmailThread(
                subject=f"New Contact Query: {subject}",
                message=f"Name: {name}\nEmail: {email}\nPhone: {phone}\n\nMessage:\n{message}",
                recipient_list=['mdnajishkhan21@gmail.com'],
                from_email='recgetup.music@gmail.com'
            ).start()

            # Auto-reply to User
            EmailThread(
                subject="We received your query - Recgetup Music",
                message=f"Hi {name},\n\nThank you for reaching out to Recgetup Music! We have received your query regarding '{subject}'.\n\nOur team will review your message and get back to you shortly.\n\nBest Regards,\nRecgetup Music Team",
                recipient_list=[email],
                from_email='recgetup.music@gmail.com'
            ).start()

            messages.success(request, "Your message has been sent successfully! We will contact you soon.")
            return redirect('home')
        else:
            messages.error(request, "Please fill in all required fields.")

    # Fetch dynamic content for Landing Page
    context = {
        'hero': HeroSection.objects.filter(is_active=True).first(),
        'about': AboutSection.objects.filter(is_active=True).first(),
        'classes': ClassType.objects.filter(is_active=True).order_by('order'),
        'testimonials': Testimonial.objects.filter(is_active=True),
        'gallery': GalleryImage.objects.filter(is_active=True).order_by('order'),
        'faqs': FAQ.objects.filter(is_active=True).order_by('order'),
    }
    return render(request, 'training/training_overview.html', context)

# 🏠 Home page (Old Quiz Logic - Deprecated)
def home_deprecated_quiz_logic(request):
    if request.user.is_authenticated:
        user = request.user
        
        # 1. 📊 User Stats
        user_stats = Attempt.objects.filter(user=user).aggregate(
            total_score=Sum('score'),
            quizzes_passed=Count('id', filter=models.Q(passed=True))
        )
        total_score = user_stats['total_score'] or 0
        quizzes_passed = user_stats['quizzes_passed'] or 0
        
        # 2. 🔥 Resume Journey (Last unfinished attempt)
        active_attempt = Attempt.objects.filter(user=user, finished_at__isnull=True).order_by('-created_at').first()
        
        if active_attempt:
            # Find the first unanswered question
            last_answer = active_attempt.answers.order_by('-question__id').first()
            if last_answer:
                # Get next question after the last answered one
                next_q = active_attempt.quiz.questions.filter(id__gt=last_answer.question.id).order_by('id').first()
                if next_q:
                    active_attempt.resume_question_id = next_q.id
                else:
                    # All questions answered? Go to first question to review
                    first_q = active_attempt.quiz.questions.order_by('id').first()
                    active_attempt.resume_question_id = first_q.id if first_q else 1
            else:
                # No answers yet, go to first question
                first_q = active_attempt.quiz.questions.order_by('id').first()
                active_attempt.resume_question_id = first_q.id if first_q else 1
        
        # 3. 🏆 Leaderboards (Helper)
        # Exclude admins and staff
        base_users = User.objects.filter(is_superuser=False, is_staff=False).select_related('profile', 'profile__college')
        
        def get_leaderboard(scope_users, time_filter='all', type_filter='all'):
            # Base Filters
            filters = models.Q(attempt__passed=True)
            
            # Time Filter
            if time_filter == 'today':
                start_date = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
                filters &= models.Q(attempt__finished_at__gte=start_date)
            elif time_filter == 'weekly':
                start_date = timezone.now() - timezone.timedelta(days=7)
                filters &= models.Q(attempt__finished_at__gte=start_date)
            
            # Type Filter
            if type_filter == 'hackathon':
                filters &= models.Q(attempt__quiz__quiz_type='hackathon')
            elif type_filter == 'practice':
                filters &= models.Q(attempt__quiz__quiz_type='practice')
                
            # Annotation Name (dynamic to avoid conflicts if needed, but 'xp' is fine since we calculate per call)
            # TIE-BREAKER: Sort by High XP, then by Earliest Finish Time (First to score wins)
            return scope_users.annotate(
                xp=Coalesce(Sum('attempt__score', filter=filters), 0),
                last_played=Max('attempt__finished_at', filter=filters)
            ).filter(xp__gt=0).order_by('-xp', 'last_played')[:3]

        # Generate Context Data for ALL combinations
        # Dimensions: 
        #   Scope: Global (base_users), College (college_users)
        #   Time: All (all), Weekly (weekly), Today (today)
        #   Type: All (all), Hackathon (hack), Practice (prac)
        
        leaderboard_data = {}
        
        scopes = {'global': base_users}
        scopes = {'global': base_users}
        # College scope removed as College model is deprecated.
        # if hasattr(user, 'profile') and user.profile.city:
        #    scopes['city'] = base_users.filter(profile__city=user.profile.city)
            
        times = ['all', 'weekly', 'today']
        types = ['all', 'hackathon', 'practice']
        
        for scope_name, scope_qs in scopes.items():
            for t in times:
                for typ in types:
                    # Key format: global_all_all, college_weekly_hackathon, etc.
                    key = f"{scope_name}_{t}_{typ}" 
                    leaderboard_data[key] = get_leaderboard(scope_qs, t, typ)

        # 4. 🔥 Daily Streak
        attempts_dates = Attempt.objects.filter(
            user=user, passed=True
        ).annotate(
            date=models.functions.TruncDate('finished_at')
        ).values_list('date', flat=True).distinct().order_by('-date')

        streak = 0
        current_check_date = timezone.now().date()
        
        if attempts_dates and attempts_dates[0] == current_check_date:
            streak = 1
            check_idx = 1
            current_check_date -= timezone.timedelta(days=1)
        elif attempts_dates and attempts_dates[0] == current_check_date - timezone.timedelta(days=1):
            streak = 0
            check_idx = 0
            current_check_date -= timezone.timedelta(days=1)
        else:
            check_idx = 0

        for date in attempts_dates[check_idx:]:
            if date == current_check_date:
                streak += 1
                current_check_date -= timezone.timedelta(days=1)
            else:
                break

        # 5. 📈 Performance Graph (Last 5 attempts)
        recent_qs = Attempt.objects.filter(user=user, finished_at__isnull=False).order_by('-finished_at')
        graph_attempts = recent_qs[:5]
        graph_attempts = reversed(list(graph_attempts)) # Show chronological for graph

        # For "My History" card
        latest_attempts = recent_qs.select_related('quiz', 'quiz__category')[:3]
        
        # 5. 📈 Performance Graph Data (Helper)
        def get_graph_data(attempts):
            labels = []
            data = []
            # Reverse to show chronological order (oldest -> newest) on graph
            for a in reversed(attempts):
                labels.append(a.quiz.title[:10] + '...')
                total_q = a.quiz.questions.count()
                percentage = 0
                if total_q > 0:
                     percentage = round((a.score / total_q) * 100, 1)
                data.append(percentage)
            return labels, data

        # Fetch Data
        qs_base = Attempt.objects.filter(user=user, finished_at__isnull=False).select_related('quiz')
        
        # 1. All
        attempts_all = qs_base.order_by('-finished_at')[:10]
        labels_all, data_all = get_graph_data(attempts_all)
        
        # 2. Hackathon
        attempts_hack = qs_base.filter(quiz__quiz_type='hackathon').order_by('-finished_at')[:10]
        labels_hack, data_hack = get_graph_data(attempts_hack)

        # 3. Practice
        attempts_prac = qs_base.filter(quiz__quiz_type='practice').order_by('-finished_at')[:10]
        labels_prac, data_prac = get_graph_data(attempts_prac)

        # 6. 🏅 Badges
        badges = []
        if Attempt.objects.filter(user=user, score=100).exists():
            badges.append({'icon': '🎯', 'name': 'Sharpshooter', 'desc': 'Scored 100% on a quiz'})
        
        if quizzes_passed >= 10:
            badges.append({'icon': '🎓', 'name': 'Scholar', 'desc': 'Passed 10+ quizzes'})
        
        if streak >= 7:
            badges.append({'icon': '🔥', 'name': 'Unstoppable', 'desc': '7 Day Learning Streak'})
            
        if total_score >= 1000:
            badges.append({'icon': '👑', 'name': 'Grandmaster', 'desc': 'Earned 1000+ XP'})

        # 7. 📅 Upcoming Classes (Training)
        # 7. 📅 Upcoming Classes (Training)
        upcoming_classes = []
        is_tutor_user = False
        
        # Check if user is a designated tutor (Mirroring 'check_is_tutor' logic)
        if user.is_superuser or user.groups.filter(name='Tutor').exists() or ClassSchedule.objects.filter(tutor=user).exists():
            is_tutor_user = True
            
        if is_tutor_user:
             # If Tutor, Show Teaching Schedule (Priority)
             # Use naive 'now' since DB might be naive or aware depending on settings, 
             # but helper expects date range.
             # Let's get next 5 days of events.
             end_range = timezone.now() + timezone.timedelta(days=7)
             patterns = BatchSchedule.objects.filter(tutor=user)
             events = generate_recurring_events(patterns, timezone.now().date(), end_range.date())
             
             # Convert to simplified object list for template compatibility
             # Template expects: topic, start_time, etc.
             # events is list of dicts.
             if events:
                 upcoming_classes = sorted(events, key=lambda x: x['start'])[:2]

        else:
            # If Student, Show Enrolled Classes
            active_enrollments = Enrollment.objects.filter(
                user=user, 
                expires_at__gt=timezone.now()
            )
            if active_enrollments.exists():
                 # Fetch recurring events for these batches
                 end_range = timezone.now() + timezone.timedelta(days=7)
                 patterns = BatchSchedule.objects.filter(batch__enrollments__in=active_enrollments).distinct()
                 events = generate_recurring_events(patterns, timezone.now().date(), end_range.date())
                 
                 if events:
                     upcoming_classes = sorted(events, key=lambda x: x['start'])[:2]
                     # Inject 'start_time' attribute for template since it might expect object attribute access
                     # Actually template likely uses {{ c.start_time }}.
                     # Dict access in template is {{ c.start }}.
                     # We need to ensure template can handle this. 
                     # Let's wrap in a simple class or modify template.
                     # Modifying template is safer.
                     # But 'home.html' is core. Let's check it? 
                     # No, let's just make it dict access compatible or object compatible.
                     # A dict in Django template *can* be accessed via dot notation for keys.
                     # {{ c.start_time }} -> in dict {{ c.start }}.
                     # We might need to map keys to match old model fields.
                     # Old: start_time. New: start.
                     for e in upcoming_classes:
                         e['start_time'] = e['start']
                         e['topic'] = e['title']


        context = {
            'total_score': total_score,
            'quizzes_passed': quizzes_passed,
            'active_attempt': active_attempt,
            'streak': streak,
            'latest_attempts': attempts_all[:3], # Show top 3 recent in history box
            'badges': badges,
            
            # Graph Data (JSON ready)
            'graph_labels_all': labels_all,
            'graph_data_all': data_all,
            'graph_labels_hack': labels_hack,
            'graph_data_hack': data_hack,
            'graph_labels_prac': labels_prac,
            'graph_data_prac': data_prac,
            
            'leaderboard_data': leaderboard_data, # New Matrix Data
            'has_college': False,
            'upcoming_classes': upcoming_classes,
        }
        return render(request, 'core/home.html', context)
    
    # Guest User: Show Landing Page
    return render(request, 'core/home.html')


# 👤 User Registration
def register(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False  # Deactivate until verified
            user.set_password(form.cleaned_data['password'])
            user.save()
            
            # Save Profile Data (Country, State, City)
            if hasattr(user, 'profile'):
                user.profile.country = form.cleaned_data.get('country')
                user.profile.state = form.cleaned_data.get('state')
                user.profile.city = form.cleaned_data.get('city')
                user.profile.phone_number = f"+91{form.cleaned_data.get('phone_number')}"
                user.profile.save()
            else:
                 # Should adhere to signals, but just in case
                from .models import Profile
                Profile.objects.create(
                    user=user,
                    country=form.cleaned_data.get('country'),
                    state=form.cleaned_data.get('state'),
                    city=form.cleaned_data.get('city'),
                    phone_number=f"+91{form.cleaned_data.get('phone_number')}"
                )

            # Send Verification Email
            current_site = get_current_site(request)
            mail_subject = 'Activate your account.'
            message = render_to_string('core/acc_active_email.html', {
                'user': user,
                'domain': current_site.domain,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                'protocol': 'https' if request.is_secure() else 'http',
            })
            to_email = form.cleaned_data.get('email')
            EmailThread(mail_subject, message, [to_email], from_email='recgetup.music@gmail.com').start()
            
            messages.success(request, "Please check your email to verify your account.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
        
    context = {
        'login_form': UserLoginForm(),      # Always use 'login_form' for Login (Front Face)
        'register_form': form,        # Always use 'register_form' for Register (Back Face)
        'password_reset_form': EmailValidationPasswordResetForm(),
        'page_type': 'register'
    }
    return render(request, 'core/login.html', context)


# 🔓 Activate Account
def activate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except(TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()

        # Send Welcome Email
        try:
            current_site = get_current_site(request)
            mail_subject = 'Welcome to Recgetup Music!'
            html_message = render_to_string('core/welcome_email.html', {
                'user': user,
                'domain': current_site.domain,
            })
            plain_message = "Welcome to Recgetup Music! We are thrilled to welcome you to our platform."
            to_email = user.email
            EmailThread(
                subject=mail_subject,
                message=plain_message,
                from_email='recgetup.music@gmail.com',
                recipient_list=[to_email],
                fail_silently=True,
                html_message=html_message
            ).start()
        except Exception as e:
            print(f"Error sending welcome email: {e}")

        messages.success(request, "✅ Email verified successfully! You can now login.")
        return redirect('login')
    else:
        messages.error(request, "❌ Activation link is invalid or has expired!")
        return redirect('register')


# 🧠 Utility: Check if user can access a quiz
def user_has_access(user, quiz):
    """Allow all practice quizzes, and only coupon-approved hackathon quizzes."""
    if quiz.quiz_type.lower() == 'practice':
        return True
    return QuizAccessGrant.objects.filter(user=user, quiz=quiz).exists()


# 📂 Category Selection Page
@login_required
def category_list(request):
    categories = Category.objects.all()
    return render(request, 'core/category_list.html', {'categories': categories})


# 📜 Quiz List Page (Filtered by Category & Type)
@login_required
def quiz_list(request, category_id=None):
    # 🔒 Enforce Category Selection
    # If no category is specified, redirect to the Category List page.
    # The user explicitly wants to prevent accessing "All Quizzes" directly.
    if category_id is None:
        return redirect('category_list')

    from django.db.models import Q
    # 1. Base Query: 
    # - User's Own Quizzes
    # - Admin/Staff Quizzes
    # - Public Legacy Quizzes (Exclude 'AI Generated' ones which should be private)
    quizzes = Quiz.objects.filter(is_active=True).filter(
        Q(created_by=request.user) | 
        Q(created_by__is_staff=True) | 
        (Q(created_by__isnull=True) & ~Q(category__name="AI Generated"))
    ).order_by('-id')

    # 2. Category Filter
    category = get_object_or_404(Category.objects.prefetch_related('quizzes'), id=category_id)
    quizzes = quizzes.filter(category=category)

    # 3. Type Filter (All / Practice / Hackathon)
    print(f"DEBUG GET: {request.GET}") # Debugging
    filter_type = request.GET.get('filter', 'all').strip().lower()
    
    if filter_type == 'practice':
        quizzes = quizzes.filter(quiz_type=Quiz.PRACTICE)
    elif filter_type == 'hackathon':
        quizzes = quizzes.filter(quiz_type=Quiz.HACKATHON)

    # 4. Pagination
    paginator = Paginator(quizzes, 9) # 9 quizzes per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    unlocked_quiz_ids = QuizAccessGrant.objects.filter(user=request.user).values_list('quiz_id', flat=True)
    
    return render(request, 'core/quiz_list.html', {
        'page_obj': page_obj,
        'unlocked_quiz_ids': unlocked_quiz_ids,
        'current_category': category,
        'filter_type': filter_type,
    })


# 📄 Quiz Detail Page
@login_required
def quiz_detail(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    # ✅ PRACTICE QUIZ: Directly accessible
    if quiz.quiz_type.lower() == 'practice':
        return render(request, 'core/quiz_detail.html', {'quiz': quiz})

    # ✅ HACKATHON QUIZ: Check Time & Access
    if quiz.quiz_type == Quiz.HACKATHON:
        now = timezone.now() # Since USE_TZ=False, this is naive local time (IST)

        # 0. Check for existing attempt (even if active)
        existing_attempt = Attempt.objects.filter(user=request.user, quiz=quiz, finished_at__isnull=False).first()
        if existing_attempt:
             # If strictly one attempt, maybe show 'over' page or just detail with 'View Result'
             # Let's pass it to detail template to handle "You've already done this"
             pass 

        # 1. 🛑 CHECK START TIME (Countdown)
        if quiz.start_time and now < quiz.start_time:
            return render(request, 'core/hackathon_countdown.html', {
                'quiz': quiz,
                'start_time_iso': quiz.start_time.isoformat(), # For JS
                'start_time_ts': quiz.start_time.timestamp()
            })

        # 2. 🛑 CHECK END TIME (Expired)
        if quiz.end_time and now > quiz.end_time:
             return render(request, 'core/hackathon_over.html', {'quiz': quiz})

    if user_has_access(request.user, quiz):
        # Check for any attempt (active or finished) to resume/view
        existing_attempt = Attempt.objects.filter(user=request.user, quiz=quiz).first()
        return render(request, 'core/quiz_detail.html', {'quiz': quiz, 'existing_attempt': existing_attempt})

    # 🚫 No access yet — show coupon input form
    warning = None
    if request.method == 'POST':
        entered = (request.POST.get('coupon_code') or '').strip().lower()
        correct = (quiz.coupon_code or '').strip().lower()

        if entered and correct and entered == correct:
            # Grant access permanently
            QuizAccessGrant.objects.get_or_create(user=request.user, quiz=quiz)
            messages.success(request, "✅ Coupon verified successfully! Quiz unlocked.")
            return redirect('quiz_detail', pk=quiz.id)
        else:
            warning = "⚠️ Invalid coupon code. Please try again."

    return render(request, 'core/access_denied.html', {'quiz': quiz, 'warning': warning})


# ▶️ Start Quiz
@login_required
def start_quiz(request, pk):
    quiz = get_object_or_404(Quiz, pk=pk)

    # 🚫 If access revoked (coupon changed), redirect back to quiz list
    if not user_has_access(request.user, quiz):
        messages.warning(request, "⚠️ Access revoked or invalid. Please re-enter the coupon.")
        return redirect('quiz_list')

    # 🛑 STRICT TIMING CHECK (Double check for URL hacking)
    if quiz.quiz_type == Quiz.HACKATHON:
        now = timezone.now()
        if (quiz.start_time and now < quiz.start_time) or (quiz.end_time and now > quiz.end_time):
             messages.error(request, "🚫 This Hackathon is currently not active.")
             return redirect('quiz_detail', pk=quiz.pk)

        # 🛑 ONE ATTEMPT ONLY
        existing_attempt = Attempt.objects.filter(user=request.user, quiz=quiz).first()
        if existing_attempt:
            if existing_attempt.finished_at:
                messages.warning(request, "You have already completed this Hackathon! 🏆")
                return redirect('result', attempt_id=existing_attempt.id)
            else:
                 # Resume incomplete attempt instead of creating new one
                 # Find the first unanswered question or last answered one
                 last_answer = existing_attempt.answers.order_by('-question__id').first()
                 resume_q_id = quiz.questions.first().id
                 
                 if last_answer:
                     next_q = quiz.questions.filter(id__gt=last_answer.question.id).order_by('id').first()
                     if next_q:
                         resume_q_id = next_q.id
                 
                 return redirect('take_quiz', attempt_id=existing_attempt.id, question_id=resume_q_id)

    # ✅ Create a new attempt
    attempt = Attempt.objects.create(user=request.user, quiz=quiz)
    question = quiz.questions.first()

    if not question:
        messages.warning(request, "⚠️ No questions are available in this quiz yet.")
        return redirect('quiz_list')

    return redirect('take_quiz', attempt_id=attempt.id, question_id=question.id)


# 🧩 Take Quiz (Question by Question)
@login_required
def take_quiz(request, attempt_id, question_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    quiz = attempt.quiz

    if attempt.finished_at:
        return redirect('result', attempt_id=attempt.id)

    question = get_object_or_404(Question, id=question_id, quiz=attempt.quiz)
    choices = question.choices.all()

    # ✅ Robust Navigation using Filter (avoids list index issues)
    next_q = attempt.quiz.questions.filter(id__gt=question.id).order_by('id').first()
    prev_q = attempt.quiz.questions.filter(id__lt=question.id).order_by('-id').first()
    
    # Calculate total for progress
    total_questions = attempt.quiz.questions.count()
    # Calculate current position (1-based)
    current_position = attempt.quiz.questions.filter(id__lt=question.id).count() + 1

    # Calculate remaining time
    elapsed_time = (timezone.now() - attempt.created_at).total_seconds()
    total_duration_seconds = attempt.quiz.duration_minutes * 60
    remaining_time = max(0, total_duration_seconds - elapsed_time)

    # 🚨 Backend Time Enforcement
    if remaining_time <= 0:
        if not attempt.finished_at:
            total_questions = attempt.quiz.questions.count()
            attempt.score = attempt.answers.filter(is_correct=True).count()
            attempt.finished_at = timezone.now()
            attempt.passed = (attempt.score / total_questions) * 100 >= attempt.quiz.passing_percentage
            attempt.auto_submit_reason = "Time Expired"
            attempt.save()
            send_hackathon_result_email(request, attempt)
        return redirect('result', attempt_id=attempt.id)

    # Get previously selected answer for this question
    selected_answer = Answer.objects.filter(attempt=attempt, question=question).first()
    selected_choice_id = selected_answer.selected_choice.id if selected_answer else None

    if request.method == 'POST':
        # 🚨 Force submit when user violates tab warnings or time expires
        if 'force_submit' in request.POST:
            total_questions = attempt.quiz.questions.count()
            attempt.score = attempt.answers.filter(is_correct=True).count()
            attempt.finished_at = timezone.now()
            attempt.passed = (attempt.score / total_questions) * 100 >= attempt.quiz.passing_percentage
            
            # Get specific reason or default
            reason = request.POST.get('violation_reason', "You exceeded the warning limit.")
            attempt.auto_submit_reason = reason
            attempt.auto_submit_reason = reason
            attempt.save()
            send_hackathon_result_email(request, attempt)
            
            return redirect('result', attempt_id=attempt.id)

        # ✅ Normal submission
        selected_choice_id = request.POST.get('choice')
        if selected_choice_id:
            choice = get_object_or_404(Choice, id=selected_choice_id)
            Answer.objects.update_or_create(
                attempt=attempt,
                question=question,
                defaults={'selected_choice': choice, 'is_correct': choice.is_correct}
            )

        # ✅ Navigation buttons
        action = request.POST.get('action')
        
        if action == 'next':
            if next_q:
                return redirect('take_quiz', attempt_id=attempt.id, question_id=next_q.id)
            else:
                pass
                
        elif action == 'prev' and prev_q:
            return redirect('take_quiz', attempt_id=attempt.id, question_id=prev_q.id)
            
        elif action == 'submit':
            total_questions = attempt.quiz.questions.count()
            attempt.score = attempt.answers.filter(is_correct=True).count()
            attempt.finished_at = timezone.now()
            attempt.passed = (attempt.score / total_questions) * 100 >= attempt.quiz.passing_percentage
            attempt.passed = (attempt.score / total_questions) * 100 >= attempt.quiz.passing_percentage
            attempt.save()
            send_hackathon_result_email(request, attempt)
            return redirect('result', attempt_id=attempt.id)

    response = render(request, 'core/take_quiz.html', {
        'question': question,
        'choices': choices,
        'attempt': attempt,
        'current_index': current_position,
        'total_questions': total_questions,
        'prev_q': prev_q,
        'next_q': next_q,
        'selected_choice_id': selected_choice_id,
        'remaining_time': int(remaining_time),
    })
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    return response


# 🧠 RESULT VIEW (Final Version)
@login_required
def result(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)

    # ✅ Get total quiz questions (not just answered)
    total_questions = attempt.quiz.questions.count()
    correct_answers = attempt.answers.filter(is_correct=True).count()

    # ✅ Ensure attempt info is accurate
    attempt.score = correct_answers
    attempt.finished_at = attempt.finished_at or timezone.now()
    attempt.passed = (correct_answers / total_questions) * 100 >= attempt.quiz.passing_percentage
    attempt.save()

    # ✅ Calculate percentage safely
    percentage = round((correct_answers / total_questions) * 100, 2) if total_questions > 0 else 0

    # ✅ Get all answers for detailed review
    answers = attempt.answers.select_related('question', 'selected_choice').all()

    return render(request, 'core/result.html', {
        'attempt': attempt,
        'correct': correct_answers,
        'total': total_questions,
        'answers': answers,
        'percentage': percentage,
    })


# -------------------------------------------------------------------
#  PASSWORD RESET VIEWS
# -------------------------------------------------------------------
class CustomPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    form_class = CustomSetPasswordForm
    template_name = 'core/password_reset_confirm.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, "✅ Password reset successfully! You can now login with your new password.")
        return super().form_valid(form)


# -------------------------------------------------------------------
#  CUSTOM LOGIN VIEW (Remember Me)
# -------------------------------------------------------------------
class CustomPasswordResetView(auth_views.PasswordResetView):
    template_name = 'core/login.html'
    email_template_name = 'core/password_reset_email.html'
    form_class = EmailValidationPasswordResetForm
    success_url = reverse_lazy('password_reset_done')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_type'] = 'forgot'
        context['login_form'] = UserLoginForm()
        context['register_form'] = UserRegistrationForm()
        context['password_reset_form'] = context['form'] # Alias for consistency
        return context


class CustomLoginView(auth_views.LoginView):
    template_name = 'core/login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'form' in context:
             context['login_form'] = context['form']
        context['register_form'] = UserRegistrationForm() # Pass register form for the flip card
        context['password_reset_form'] = EmailValidationPasswordResetForm()
        context['page_type'] = 'login'
        return context

    def form_valid(self, form):
        # Remember Me Logic
        remember_me = self.request.POST.get('remember_me')
        if remember_me:
            # Set session expiry to 30 days (2592000 seconds)
            self.request.session.set_expiry(2592000)
        else:
            # Default behavior: Don't expire on browser close. 
            # Set to standard 2 weeks (1209600 seconds) to prevent "cut tab = logout" frustration
            self.request.session.set_expiry(1209600)
            
        return super().form_valid(form)


@login_required
@xframe_options_sameorigin
def certificate_view(request, attempt_id):
    attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
    
    if attempt.quiz.quiz_type != 'hackathon':
        messages.error(request, "Certificates are only available for Hackathon quizzes.")
        return redirect('result', attempt_id=attempt.id)

    # 🛑 Check if certificates are enabled for this quiz
    if not attempt.quiz.generate_certificate:
        messages.error(request, "Certificates are disabled for this quiz.")
        return redirect('result', attempt_id=attempt.id)

    if not attempt.passed:
        messages.error(request, "You must pass the quiz to get a certificate.")
        return redirect('result', attempt_id=attempt.id)

    buffer = generate_certificate_pdf(attempt)
    
    # Check if download is requested
    if request.GET.get('download'):
        return FileResponse(buffer, as_attachment=True, filename=f"Certificate_{attempt.quiz.title}.pdf")
    
    # Otherwise, show inline (preview)
    return FileResponse(buffer, filename=f"Certificate_{attempt.quiz.title}.pdf")


# -------------------------------------------------------------------
#  PROFILE VIEW
# -------------------------------------------------------------------
@login_required
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            
            # 🛡️ Send Profile Security Alert Email
            try:
                current_site = get_current_site(request)
                mail_subject = 'Security Alert: Profile Updated 🛡️'
                html_message = render_to_string('core/profile_update_email.html', {
                    'user': request.user,
                    'domain': f"{'https' if request.is_secure() else 'http'}://{current_site.domain}",
                    'timestamp': timezone.now().strftime("%B %d, %Y at %I:%M %p"),
                })
                plain_message = f"Hello {request.user.first_name}, your profile was updated. If this wasn't you, please secure your account."
                
                send_mail(
                    subject=mail_subject,
                    message=plain_message,
                    from_email='recgetup.music@gmail.com',
                    recipient_list=[request.user.email],
                    fail_silently=True,
                    html_message=html_message
                )
            except Exception as e:
                print(f"Error sending profile alert email: {e}")

            messages.success(request, '✅ Your profile has been updated!')
            return redirect('profile')

    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'u_form': u_form,
        'p_form': p_form
    }

    return render(request, 'core/profile.html', context)


@login_required
def my_history(request):
    """
    Displays the user's quiz history/dashboard with filtering and pagination.
    """
    attempts = Attempt.objects.filter(user=request.user).select_related('quiz', 'quiz__category').order_by('-created_at')

    # 1. 🔍 Search Filter
    query = request.GET.get('q')
    if query:
        attempts = attempts.filter(
            models.Q(quiz__title__icontains=query) | 
            models.Q(quiz__category__name__icontains=query)
        )

    # 2. ⚡ Type Filter
    filter_type = request.GET.get('type', '').strip().lower()
    if filter_type == 'practice':
        attempts = attempts.filter(quiz__quiz_type='practice')
    elif filter_type == 'hackathon':
         attempts = attempts.filter(quiz__quiz_type='hackathon')

    # 3. 📄 Pagination (10 per page)
    paginator = Paginator(attempts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'attempts': page_obj,
        'query': query,
        'filter_type': filter_type,
    }

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'core/partials/dashboard_list.html', context)

    return render(request, 'core/user_dashboard.html', context)


@csrf_exempt
def ask_ai(request):
    """
    AJAX Endpoint to get AI explanation for a specific question using Gemini.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            question_id = data.get('question_id')
            user_answer_text = data.get('user_answer')
            
            question = Question.objects.get(id=question_id)
            correct_choices = question.choices.filter(is_correct=True)
            correct_text = ", ".join([c.text for c in correct_choices])
            
            # Configure OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""
            You are an expert tutor. A student answered a multiple-choice question incorrectly.
            
            Question: {question.text}
            Student's Answer: {user_answer_text}
            Correct Answer: {correct_text}
            
            Please provide a brief, encouraging, and clear explanation of:
            1. Why the student's answer is incorrect.
            2. Why the correct answer is right.
            Keep it strictly under 100 words. Be friendly and helpful.
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful AI tutor."},
                    {"role": "user", "content": prompt}
                ]
            )
            return JsonResponse({'explanation': response.choices[0].message.content})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    return JsonResponse({'error': 'Invalid request'}, status=400)


@csrf_exempt
def analyze_progress(request):
    """
    AJAX Endpoint to analyze user's quiz history and provide AI feedback.
    """
    if request.method == 'POST':
        try:
            # 1. Gather User Stats
            # Get last 15 attempts with full details
            attempts = Attempt.objects.filter(user=request.user).select_related('quiz', 'quiz__category').order_by('-created_at')[:15]
            
            if not attempts.exists():
                return JsonResponse({'analysis': "You haven't taken any quizzes yet! Take a few practice quizzes so I can analyze your strengths and weaknesses."})

            # Format detailed history for AI
            stats_text = "Student's Recent Quiz History:\n"
            for attempt in attempts:
                category = attempt.quiz.category.name if attempt.quiz.category else "General"
                topic = attempt.quiz.title
                score = attempt.score
                max_score = attempt.quiz.questions.count()
                
                # For AI Generated quizzes, the Topic IS the title. For others, it might be generic, but still useful.
                if category == "AI Generated":
                    label = f"AI Quiz on '{topic}'"
                else:
                    label = f"{category} Quiz: {topic}"
                    
                stats_text += f"- {label}: Scored {score}/{max_score}\n"

            # 2. Query OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)
            
            prompt = f"""
            You are an expert academic mentor. Analyze this student's recent quiz history:
            
            {stats_text}
            
            Provide a short, motivating analysis (max 3 sentences).
            1. Identify their strongest TOPIC (not just category).
            2. specific weak area based on the specific quiz titles where they scored low.
            3. End with an encouraging remark.
            Use emojis. Talk directly to the student ("You...").
            """
            
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful academic mentor."},
                    {"role": "user", "content": prompt}
                ]
            )
            return JsonResponse({'analysis': response.choices[0].message.content})
            
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


@login_required
def generate_quiz_page(request):
    return render(request, 'core/generate_quiz.html')


@csrf_exempt
@login_required
def generate_quiz_api(request):
    """
    API to generate a quiz using Gemini and save it to DB.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            topic = data.get('topic', '').strip()
            limit = int(data.get('limit', 5))
            difficulty = data.get('difficulty', 'Beginner') # Get difficulty
            
            if not topic:
                return JsonResponse({'error': 'Topic is required'}, status=400)

            # 🛑 0. Check Monthly Limit (3 Quizzes)
            from django.utils import timezone
            now = timezone.now()
            start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Count user's AI quizzes this month
            # Note: We rely on created_at or fuzzy matching if created_at is null for old ones
            # But since this is a new feature, we only care about new quizzes which will have created_at
            current_month_count = Quiz.objects.filter(
                created_by=request.user,
                quiz_type='practice', # Assuming AI quizzes are practice
                category__name="AI Generated",
                created_at__gte=start_of_month
            ).count()
            
            if current_month_count >= 3:
                return JsonResponse({
                    'error': 'Monthly limit exceeded', 
                    'limit_reached': True
                }, status=403)

            # 1. Configure OpenAI
            from openai import OpenAI
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # 2. Construct Prompt for JSON
            prompt = f"""
            Analyze the topic: "{topic}".
            Difficulty Level: {difficulty}.
            
            STRICT CONTENT GUIDELINES:
            This platform is for study and educational purposes only.
            1. REJECT topics involving: profanity, sexual content, violence, hate speech, illegal acts, or inappropriate adult themes.
            2. REJECT topics that are purely for inappropriate entertainment or "bad things".
            
            If the topic violates these rules, return ONLY this JSON:
            {{ "error": "This platform is designed mainly for study purposes. Please choose a polite and educational topic." }}

            If the topic is safe/educational, create a multiple-choice quiz about "{topic}".
            Number of questions: {limit}.
            Complexity: {difficulty} (Ensure questions are suitable for {difficulty} level).
            
            Return ONLY raw JSON. No markdown formatting. No code blocks.
            Success Structure:
            {{
                "title": "Short Topic Title (Max 5 words)",
                "questions": [
                    {{
                        "text": "Question text here?",
                        "choices": [
                            {{"text": "Choice 1", "is_correct": false}},
                            {{"text": "Choice 2", "is_correct": true}},
                            {{"text": "Choice 3", "is_correct": false}},
                            {{"text": "Choice 4", "is_correct": false}}
                        ]
                    }}
                ]
            }}
            """

            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a helpful and ethical AI tutor. You strictly enforce educational guidelines."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" }
            )
            
            clean_text = response.choices[0].message.content.strip()
            
            quiz_data = json.loads(clean_text)
            
            # Check if AI rejected the topic
            if 'error' in quiz_data:
                 return JsonResponse({'error': quiz_data['error']}, status=400)

            # 3. Save to Database
            # Get or Create "AI Generated" category
            category, _ = Category.objects.get_or_create(name="AI Generated")
            
            # ✅ Hybrid Title Logic
            # If user typed a short topic (e.g. "Python"), use it directly.
            # If user typed a long description, use the AI's summarized title.
            if len(topic.split()) <= 6:
                final_title = topic.title()
            else:
                final_title = quiz_data.get('title', topic[:50]).title()
            
            # Append difficulty to title if not beginner
            if difficulty != 'Beginner':
                final_title = f"{final_title} ({difficulty})"

            # ✅ Dynamic Time Calculation
            # 1.5 minutes per question, minimum 5 minutes
            calculated_duration = max(5, int(limit * 1.5))
            
            # Create Quiz Object
            quiz = Quiz.objects.create(
                title=final_title,
                description=f"An AI-generated quiz on {topic}. Challenge yourself!",
                category=category,
                quiz_type='practice', # Defaulting to practice for AI quizzes
                duration_minutes=calculated_duration, 
                passing_percentage=60, # Standard passing
                created_by=request.user
            )

            # 4. Save Questions to Database
            for q_data in quiz_data.get('questions', []):
                question = Question.objects.create(
                    quiz=quiz,
                    text=q_data['text']
                    # question_type removed as it doesn't exist in model
                )
                
                for choice_data in q_data.get('choices', []):
                    Choice.objects.create(
                        question=question,
                        text=choice_data['text'],
                        is_correct=choice_data['is_correct']
                    )

            # 🤖 Send AI Quiz Ready Email
            try:
                current_site = get_current_site(request)
                mail_subject = f"Your AI Quiz '{final_title}' is Ready! 🤖"
                quiz_url = f"{'https' if request.is_secure() else 'http'}://{current_site.domain}{reverse('quiz_detail', args=[quiz.id])}"
                
                html_message = render_to_string('core/ai_quiz_ready_email.html', {
                    'user': request.user,
                    'topic': topic.title(),
                    'quiz_url': quiz_url,
                    'question_count': limit,
                    'difficulty': difficulty,
                    'domain': f"{'https' if request.is_secure() else 'http'}://{current_site.domain}",
                })
                plain_message = f"Your AI quiz on {topic} is ready. Start here: {quiz_url}"
                
                send_mail(
                    subject=mail_subject,
                    message=plain_message,
                    from_email='recgetup.music@gmail.com',
                    recipient_list=[request.user.email],
                    fail_silently=True,
                    html_message=html_message
                )
            except Exception as e:
                print(f"Error sending AI quiz email: {e}")
            
            return JsonResponse({'success': True, 'quiz_id': quiz.id})

        except Exception as e:
            print(f"Generic Error: {e}")
            return JsonResponse({'error': "We are facilitating many quizzes right now! Please try again in 30 seconds. 🚀"}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)


# -------------------------------------------------------------------
#  LIFELINES API (Hackathon Only)
# -------------------------------------------------------------------
# -------------------------------------------------------------------
#  LIFELINES API (Hackathon Only)
# -------------------------------------------------------------------
@csrf_exempt
def use_lifeline_api(request):
    print("\n--- LIFELINE REQUEST RECEIVED ---")
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'User not logged in'}, status=401)

    if request.method == 'POST':
        try:
            print(f"BODY: {request.body.decode('utf-8')}")
            data = json.loads(request.body)
            attempt_id = data.get('attempt_id')
            question_id = data.get('question_id')
            lifeline_type = data.get('lifeline_type') # '5050', 'ask_ai', 'poll'
            print(f"Parsed: Attempt={attempt_id}, Question={question_id}, Type={lifeline_type}")

            # VALIDATE INPUTS
            if not all([attempt_id, question_id, lifeline_type]):
                return JsonResponse({'error': 'Missing required fields'}, status=400)

            attempt = get_object_or_404(Attempt, id=attempt_id, user=request.user)
            question = get_object_or_404(Question, id=question_id)
            
            # Init lifelines_used if empty (handle None case explicitly)
            if attempt.lifelines_used is None:
                attempt.lifelines_used = {}

            if attempt.lifelines_used.get(lifeline_type):
                return JsonResponse({'error': 'Lifeline already used'}, status=400)

            result = {}

            if lifeline_type == '5050':
                choices = list(question.choices.all())
                incorrect_choices = [c for c in choices if not c.is_correct]
                
                if len(incorrect_choices) >= 2:
                    import random
                    to_remove = random.sample(incorrect_choices, 2)
                    result['remove_ids'] = [c.id for c in to_remove]
                else:
                    result['remove_ids'] = [c.id for c in incorrect_choices]
            
            elif lifeline_type == 'ask_ai':
                from openai import OpenAI
                if not settings.OPENAI_API_KEY:
                     return JsonResponse({'error': 'OpenAI API Key not configured'}, status=500)

                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                
                options_text = "\n".join([f"- {c.text}" for c in question.choices.all()])
                
                prompt = f"""
                Question: {question.text}
                Options:
                {options_text}
                
                You are a "Phone a Friend" lifeline. 
                Provide a helpful HINT. Do NOT give the direct answer. 
                Guide the user towards the correct concept. 
                Keep it under 30 words.
                """
                
                try:
                    ai_resp = client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": prompt}],
                        max_tokens=60
                    )
                    result['hint'] = ai_resp.choices[0].message.content.strip()
                except Exception as e:
                     print(f"OpenAI Error: {e}")
                     return JsonResponse({'error': 'AI service unavailable'}, status=503)

            elif lifeline_type == 'poll':
                import random
                choices = list(question.choices.all())
                correct_choice = next((c for c in choices if c.is_correct), None)
                
                remaining_pct = 100
                poll_data = {}
                
                if correct_choice:
                    correct_pct = random.randint(55, 85)
                    poll_data[correct_choice.id] = correct_pct
                    remaining_pct -= correct_pct
                
                incorrects = [c for c in choices if not c.is_correct]
                for i, inc in enumerate(incorrects):
                    if i == len(incorrects) - 1:
                        score = remaining_pct
                    else:
                        score = random.randint(0, remaining_pct)
                        remaining_pct -= score
                    poll_data[inc.id] = score
                
                result['poll_data'] = poll_data

            # Mark as used
            attempt.lifelines_used[lifeline_type] = True
            attempt.save()
            
            return JsonResponse({'success': True, 'result': result})

        except json.JSONDecodeError:
             return JsonResponse({'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            print(f"Lifeline API Error: {str(e)}")
            return JsonResponse({'error': f"Server Error: {str(e)}"}, status=500)
    
    return JsonResponse({'error': 'Invalid request method'}, status=405)
# -------------------------------------------------------------------
#  ADMIN CHART API
# -------------------------------------------------------------------
# -------------------------------------------------------------------
#  ADMIN CHART API (REWRITTEN FRESH)
# -------------------------------------------------------------------
@login_required
def admin_dashboard_chart_api(request):
    """
    API for Admin Dashboard Charts.
    Returns JSON {labels: [], data: []} based on metric/period.
    Timezone: Asia/Kolkata (Implicit via USE_TZ=True and local conversion)
    """
    if not request.user.is_staff:
        return JsonResponse({'error': 'Unauthorized'}, status=403)

    metric = request.GET.get('metric', 'income') 
    period = request.GET.get('period', 'monthly') 
    year = request.GET.get('year')

    # Imports
    from django.db.models import Sum
    from core.models import Expense
    from training.models import Coupon
    import datetime
    from django.utils.dateparse import parse_datetime, parse_date

    # 1. Define QuerySet & Date Field
    # For Net Profit, we need special handling (two querysets)
    qs = None
    qs_expense = None
    
    if metric == 'students':
        qs = User.objects.exclude(is_staff=True).exclude(is_superuser=True).exclude(groups__name='Tutor')
        date_field = 'date_joined'
        is_datetime_field = True
    elif metric == 'income':
        qs = Coupon.objects.filter(payment_amount__gt=0)
        date_field = 'payment_date'
        is_datetime_field = False
    elif metric == 'net_profit':
        # Dual Data Source
        qs = Coupon.objects.filter(payment_amount__gt=0) # Income
        qs_expense = Expense.objects.all()               # Expense
        date_field = 'payment_date'   # Primary date field (Income)
        expense_date_field = 'date'   # Secondary date field (Expense)
        is_datetime_field = False     # Both are DateFields
    elif metric == 'course_popularity':
        # Pie Chart Logic: Group by Workshop Title
        from training.models import Enrollment
        # Active Enrollments only? Or all time? Let's generic to all for popularity histoy.
        data = Enrollment.objects.values('batch__workshop__title').annotate(count=Count('id')).order_by('-count')
        labels = [x['batch__workshop__title'] for x in data]
        values = [x['count'] for x in data]
        return JsonResponse({'labels': labels, 'data': values})
    elif metric == 'demographics':
        # Bar/Pie Logic: Group by City
        from core.models import Profile
        # Filter only students (exclude tutors/admin from count)
        student_ids = User.objects.exclude(is_staff=True).exclude(groups__name='Tutor').values_list('id', flat=True)
        data = Profile.objects.filter(user__id__in=student_ids).values('city').annotate(count=Count('id')).order_by('-count')[:8] # Top 8
        labels = [x['city'] or 'Unknown' for x in data]
        values = [x['count'] for x in data]
        return JsonResponse({'labels': labels, 'data': values})
    
    # ... (Rest of Time Series Logic for Income/Students) ...
    # We need to wrap the Time Series logic in "else" or specific check
    
    # 2. Determine Time Range & Grouping logic (Only for Time Series)
    today = timezone.localtime(timezone.now()).date()
    start_date = None
    end_date = None
    
    # helper for aggregation grouping
    group_by = 'day' # day | month | hour

    if period == 'today':
        start_date = today
        end_date = today # inclusive check logic handled later
        group_by = 'hour'
        
    elif period == 'weekly':
        start_date = today - datetime.timedelta(days=6) # Last 7 days including today
        end_date = today
        group_by = 'day'

    elif period == 'monthly':
        # "Monthly" = Current Month Daily Trend
        start_date = today.replace(day=1)
        end_date = today
        group_by = 'day'

    elif period == 'yearly':
        # "Yearly" = Current Year Monthly Trend
        start_date = today.replace(month=1, day=1)
        end_date = today.replace(month=12, day=31)
        group_by = 'month'
        
    elif period == 'specific_year' and year:
        try:
            y = int(year)
            start_date = datetime.date(y, 1, 1)
            end_date = datetime.date(y, 12, 31)
            group_by = 'month'
        except ValueError:
            pass # Fallback

    elif period == 'all_time':
         start_date = None # No start limit
         group_by = 'month' # Too dense for day?

    # 3. Apply DB Filter (Course Optimization)
    if start_date:
        if is_datetime_field:
             start_dt = timezone.make_aware(datetime.datetime.combine(start_date, datetime.time.min))
             qs = qs.filter(**{f"{date_field}__gte": start_dt})
        else:
             qs = qs.filter(**{f"{date_field}__gte": start_date})
             if qs_expense is not None:
                 qs_expense = qs_expense.filter(**{f"{expense_date_field}__gte": start_date})
             
    if period == 'specific_year' and year:
         if is_datetime_field:
             end_dt = timezone.make_aware(datetime.datetime.combine(end_date, datetime.time.max))
             qs = qs.filter(**{f"{date_field}__lte": end_dt})
         else:
             qs = qs.filter(**{f"{date_field}__lte": end_date})
             if qs_expense is not None:
                 qs_expense = qs_expense.filter(**{f"{expense_date_field}__lte": end_date})

    elif period == 'today':
         if is_datetime_field:
             start_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.min))
             end_dt = timezone.make_aware(datetime.datetime.combine(today, datetime.time.max))
             qs = qs.filter(**{f"{date_field}__range": (start_dt, end_dt)})
         else:
             qs = qs.filter(**{f"{date_field}": today})
             if qs_expense is not None:
                 qs_expense = qs_expense.filter(**{f"{expense_date_field}": today})
                 
    # 4. Fetch Raw Data
    if metric == 'students':
        data_rows = qs.values(date_field)
    elif metric == 'net_profit':
        # Fetch both
        data_rows = qs.values(date_field, 'payment_amount')
        expense_rows = qs_expense.values(expense_date_field, 'amount')
    else:
        # Income / Standard
        data_rows = qs.values(date_field, 'payment_amount')

    # 5. Python Aggregation (Robust)
    aggregated = {} 
    
    current_tz = timezone.get_current_timezone()
    
    # Helper to process a row list
    def process_rows(rows, date_key, val_key, multiplier=1):
        for row in rows:
            raw_dt = row[date_key]
            val = row.get(val_key, 0)
            
            if not raw_dt: continue

            # Normalize 
            dt_obj = None
            if isinstance(raw_dt, datetime.datetime):
                 if timezone.is_naive(raw_dt):
                     raw_dt = timezone.make_aware(raw_dt, current_tz)
                 dt_obj = timezone.localtime(raw_dt)
            elif isinstance(raw_dt, datetime.date):
                 naive_dt = datetime.datetime.combine(raw_dt, datetime.time.min)
                 dt_obj = timezone.make_aware(naive_dt, current_tz)
            elif isinstance(raw_dt, str):
                 parsed = parse_datetime(raw_dt)
                 if not parsed:
                     parsed_d = parse_date(raw_dt)
                     if parsed_d:
                         parsed = datetime.datetime.combine(parsed_d, datetime.time.min)
                 if parsed:
                     if timezone.is_naive(parsed):
                         parsed = timezone.make_aware(parsed, current_tz)
                     dt_obj = timezone.localtime(parsed)
            
            if not dt_obj: continue

            # Grouping
            key = None
            if group_by == 'hour':
                key = dt_obj.replace(minute=0, second=0, microsecond=0)
            elif group_by == 'day':
                key = dt_obj.replace(hour=0, minute=0, second=0, microsecond=0)
            elif group_by == 'month':
                key = dt_obj.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            if metric == 'students':
                aggregated[key] = aggregated.get(key, 0) + 1
            else:
                aggregated[key] = aggregated.get(key, 0) + (val * multiplier)

    # Process Primary Data (Income / Student)
    if metric == 'students':
        process_rows(data_rows, date_field, None)
    else:
        # For Net Profit, Income is positive
        process_rows(data_rows, date_field, 'payment_amount', 1)

    # Process Secondary Data (Expense for Net Profit)
    if metric == 'net_profit':
        # Expense is negative
        process_rows(expense_rows, expense_date_field, 'amount', -1)

    # 6. Formatting for Chart.js
    sorted_keys = sorted(aggregated.keys())
    labels = []
    values = []

    for k in sorted_keys:
        # Label
        if group_by == 'hour':
            lbl = k.strftime('%I %p') # 10 AM
        elif group_by == 'day':
            lbl = k.strftime('%d %b') # 26 Jan
        elif group_by == 'month':
            lbl = k.strftime('%b %Y') # Jan 2026
            
        labels.append(lbl)
        values.append(aggregated[k])

    return JsonResponse({'labels': labels, 'data': values})

