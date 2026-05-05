from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    WorkshopRegistration, HeroSection, MarqueeSection, MasterySection,
    CurriculumSection, MentorSection, PricingSection, TimerSection, VocalWorkshopQuery,
    GallerySection, FAQSection, SiteSettings
)
import json
import logging

logger = logging.getLogger(__name__)

def workshop_landing(request):
    """Renders the minimal, premium classical singing workshop landing page."""
    context = {
        'hero': HeroSection.objects.filter(is_active=True).first(),
        'marquee': MarqueeSection.objects.filter(is_active=True).first(),
        'mastery': MasterySection.objects.filter(is_active=True).first(),
        'curriculum': CurriculumSection.objects.filter(is_active=True).first(),
        'mentor': MentorSection.objects.filter(is_active=True).first(),
        'pricing': PricingSection.objects.filter(is_active=True).first(),
        'timer': TimerSection.objects.filter(is_active=True).first(),
        'gallery': GallerySection.objects.filter(is_active=True).first(),
        'faq': FAQSection.objects.filter(is_active=True).first(),
        'settings': SiteSettings.objects.filter(is_active=True).first(),
    }
    return render(request, 'landingpage/index.html', context)

def submit_query(request):
    """Handles the query form submission via AJAX."""
    if request.method == 'POST':
        try:
            # Handle both standard POST and JSON POST
            if request.content_type == 'application/json':
                data = json.loads(request.body)
                name = data.get('name')
                phone = data.get('phone')
                email = data.get('email')
                message = data.get('message')
            else:
                name = request.POST.get('name')
                phone = request.POST.get('phone')
                email = request.POST.get('email')
                message = request.POST.get('message')
            
            if name and phone and message:
                VocalWorkshopQuery.objects.create(
                    name=name,
                    phone=phone,
                    email=email,
                    message=message
                )
                
                # Send Email Synchronously (Exactly like Core App for Instant Delivery)
                if email:
                    try:
                        subject = 'Query Received | RecgetUp Music'
                        html_content = render_to_string('landingpage/email_welcome.html', {
                            'name': name,
                            'is_query': True
                        })
                        # Explicitly set display name to hide "tgays"
                        display_from = f"RecgetUp Music <{settings.EMAIL_HOST_USER}>"
                        send_mail(
                            subject=subject,
                            message=f"Hi {name}, thank you for your query.",
                            from_email=display_from,
                            recipient_list=[email],
                            html_message=html_content,
                            fail_silently=True
                        )
                    except Exception as e:
                        logger.error(f"Email error: {e}")
                    
                return JsonResponse({'status': 'success', 'message': "Your question has been sent!"})
            else:
                return JsonResponse({'status': 'error', 'message': "Please fill in all required fields."}, status=400)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

def register_workshop(request):
    """Handles the workshop registration."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            full_name = data.get('full_name', '').strip()
            email = data.get('email', '').strip()
            whatsapp_number = data.get('whatsapp_number', '').strip()
            age = data.get('age')
            state = data.get('state', '').strip()
            experience = data.get('experience', '0-1')
            instrument = data.get('instrument', 'Harmonium')
            swar_identification = data.get('swar_identification', 'No')
            
            if full_name and email and whatsapp_number:
                # 1. Save to Database
                WorkshopRegistration.objects.create(
                    full_name=full_name,
                    email=email,
                    whatsapp_number=whatsapp_number,
                    age=age if age else None,
                    state=state,
                    experience=experience,
                    instrument=instrument,
                    swar_identification=swar_identification
                )
                
                # 2. Send Email Synchronously (Exactly like Core App for Instant Delivery)
                if email:
                    try:
                        subject = 'Registration Confirmed | RecgetUp Music'
                        html_content = render_to_string('landingpage/email_registration.html', {
                            'name': full_name,
                            'instrument': instrument
                        })
                        # Explicitly set display name to hide "tgays"
                        display_from = f"RecgetUp Music <{settings.EMAIL_HOST_USER}>"
                        send_mail(
                            subject=subject,
                            message=f"Hi {full_name}, your registration is confirmed.",
                            from_email=display_from,
                            recipient_list=[email],
                            html_message=html_content,
                            fail_silently=True
                        )
                    except Exception as e:
                        logger.error(f"Email error: {e}")
                
                return JsonResponse({'status': 'success', 'message': 'Registration successful.'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Please fill all required fields.'}, status=400)
            
        except Exception as e:
            print(f"REGISTRATION ERROR: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)
