from django.shortcuts import redirect
from django.urls import reverse
from django.conf import settings
from .models import Attempt

class HackathonEnforcementMiddleware:
    """
    Middleware to restrict navigation for users with an active Hackathon attempt.
    Users are forced to stay on the quiz page until they submit.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Check if user is authenticated
        if request.user.is_authenticated:
            # 2. Check for ACTIVE Hackathon attempt (not finished)
            active_attempt = Attempt.objects.filter(
                user=request.user,
                quiz__quiz_type='hackathon',
                finished_at__isnull=True
            ).first()

            if active_attempt:
                # 3. Define allowed paths
                # - The quiz attempt URLs
                # - Static and Media files (so the page looks right)
                current_path = request.path
                quiz_path_prefix = f"/attempt/{active_attempt.id}/"
                
                is_allowed = (
                    current_path.startswith(quiz_path_prefix) or
                    current_path.startswith('/api/') or
                    current_path.startswith(settings.STATIC_URL) or
                    current_path.startswith(settings.MEDIA_URL)
                )

                if not is_allowed:
                    # 4. Redirect logic: Try to send them back to where they were
                    # Find the best question to redirect to (e.g., first unanswered or just the first one)
                    
                    # Simple fallback: Go to the first question
                    # Ideally, we could find the last answered question, but for safety/speed, 
                    # let's just grab the first question of the quiz.
                    # The user can navigate from there.
                    first_question = active_attempt.quiz.questions.order_by('id').first()
                    
                    if first_question:
                        return redirect('take_quiz', attempt_id=active_attempt.id, question_id=first_question.id)
                    else:
                        # Edge case: Quiz has no questions? 
                        # Let them go to result or list? 
                        # If no questions, they can't take it anyway.
                        pass

        response = self.get_response(request)
        return response
