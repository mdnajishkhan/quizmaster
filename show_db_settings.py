import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'quizsite.settings')
django.setup()

def show_settings():
    db = settings.DATABASES['default']
    print(f"DB Engine: {db['ENGINE']}")
    print(f"DB Name:   {db['NAME']}")
    print(f"DB Host:   {db['HOST']}")
    print(f"DB Port:   {db['PORT']}")

if __name__ == "__main__":
    show_settings()
