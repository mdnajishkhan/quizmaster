from django.db import models
from .models import *  # Import existing models if needed, though usually cleaner to keep separate

class ContactQuery(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_resolved = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Contact Query"
        verbose_name_plural = "Contact Queries"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"
