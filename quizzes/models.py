from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
import hashlib

class College(models.Model):
    name = models.CharField(max_length=190, unique=True)

    def __str__(self):
        return self.name


class Profile(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    college = models.ForeignKey(College, on_delete=models.SET_NULL, null=True, blank=True)
    bio = models.TextField(blank=True, null=True)
    profile_pic = models.ImageField(upload_to='profiles/', blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


@receiver(models.signals.post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

@receiver(models.signals.post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    @property
    def color_class(self):
        colors = [
            "bg-red-900/50 text-red-200 border border-red-500/30",
            "bg-orange-900/50 text-orange-200 border border-orange-500/30",
            "bg-amber-900/50 text-amber-200 border border-amber-500/30",
            "bg-yellow-900/50 text-yellow-200 border border-yellow-500/30",
            "bg-lime-900/50 text-lime-200 border border-lime-500/30",
            "bg-green-900/50 text-green-200 border border-green-500/30",
            "bg-emerald-900/50 text-emerald-200 border border-emerald-500/30",
            "bg-teal-900/50 text-teal-200 border border-teal-500/30",
            "bg-cyan-900/50 text-cyan-200 border border-cyan-500/30",
            "bg-sky-900/50 text-sky-200 border border-sky-500/30",
            "bg-blue-900/50 text-blue-200 border border-blue-500/30",
            "bg-indigo-900/50 text-indigo-200 border border-indigo-500/30",
            "bg-violet-900/50 text-violet-200 border border-violet-500/30",
            "bg-purple-900/50 text-purple-200 border border-purple-500/30",
            "bg-fuchsia-900/50 text-fuchsia-200 border border-fuchsia-500/30",
            "bg-pink-900/50 text-pink-200 border border-pink-500/30",
            "bg-rose-900/50 text-rose-200 border border-rose-500/30",
        ]
        if not self.name:
            return colors[0]
            
        hash_object = hashlib.md5(self.name.encode())
        hash_int = int(hash_object.hexdigest(), 16)
        index = hash_int % len(colors)
        return colors[index]


class Quiz(models.Model):
    PRACTICE = 'practice'
    HACKATHON = 'hackathon'

    QUIZ_TYPES = [
        (PRACTICE, 'Practice'),
        (HACKATHON, 'Hackathon'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='quizzes')
    quiz_type = models.CharField(max_length=20, choices=QUIZ_TYPES, default=PRACTICE)
    duration_minutes = models.PositiveIntegerField(default=10)
    passing_percentage = models.PositiveIntegerField(default=50)
    is_active = models.BooleanField(default=True)
    
    DIFFICULTY_CHOICES = [
        ('Beginner', 'Beginner'),
        ('Intermediate', 'Intermediate'),
        ('Advanced', 'Advanced'),
    ]
    difficulty = models.CharField(max_length=20, choices=DIFFICULTY_CHOICES, default='Beginner')
    
    coupon_code = models.CharField(
        max_length=50, blank=True, null=True,
        help_text="Set coupon only for hackathon quizzes. Leave blank for practice."
    )
    
    # ⏰ Hackathon Timing
    start_time = models.DateTimeField(null=True, blank=True, help_text="Quiz becomes accessible at this time.")
    end_time = models.DateTimeField(null=True, blank=True, help_text="Quiz closes at this time.")
    
    # 🏅 Certificate Control
    generate_certificate = models.BooleanField(default=True, help_text="If checked, students can download a certificate after passing.")
    
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_quizzes')
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return self.title


class HackathonResult(Quiz):
    class Meta:
        proxy = True
        verbose_name = 'Hackathon Result'
        verbose_name_plural = 'Hackathon Results'


class Question(models.Model):
    quiz = models.ForeignKey(Quiz, related_name='questions', on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text[:70]


class Choice(models.Model):
    question = models.ForeignKey(Question, related_name='choices', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:60]


class Attempt(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    score = models.IntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)
    passed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    auto_submit_reason = models.CharField(max_length=255, blank=True, null=True)
    lifelines_used = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.quiz.title}"


class Answer(models.Model):
    attempt = models.ForeignKey(Attempt, related_name='answers', on_delete=models.CASCADE)
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_choice = models.ForeignKey(Choice, on_delete=models.CASCADE)
    is_correct = models.BooleanField(default=False)


class QuizAccessGrant(models.Model):
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    granted_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('quiz', 'user')

    def __str__(self):
        return f"{self.user.username} → {self.quiz.title}"




@receiver(pre_save, sender=Quiz)
def reset_access_when_coupon_changes(sender, instance, **kwargs):
    """
    Automatically revoke access for all users if the coupon_code changes.
    """
    if not instance.pk:
        # If quiz is new, do nothing
        return

    try:
        old_quiz = Quiz.objects.get(pk=instance.pk)
    except Quiz.DoesNotExist:
        return

    old_code = (old_quiz.coupon_code or '').strip().lower()
    new_code = (instance.coupon_code or '').strip().lower()

    if old_code != new_code:
        # Coupon has changed! Revoke all user access for this quiz
        QuizAccessGrant.objects.filter(quiz=instance).delete()
        print(f"🔐 Coupon changed for '{instance.title}', all previous access revoked.")
