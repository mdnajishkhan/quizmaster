from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
import requests
from training.models import HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ
from django.conf import settings
import os

class Command(BaseCommand):
    help = 'Populates the landing page with sample music academy data'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting population...")

        # Clear existing data to avoid duplicates (optional, strictly for test population)
        # HeroSection.objects.all().delete()
        # AboutSection.objects.all().delete()
        # ClassType.objects.all().delete()
        # Testimonial.objects.all().delete()
        # GalleryImage.objects.all().delete()
        # FAQ.objects.all().delete()

        # Helper to download and save image
        def save_image_from_url(model_instance, field_name, url, filename):
            image_saved = False
            try:
                response = requests.get(url, timeout=10)
                if response.status_code == 200:
                    getattr(model_instance, field_name).save(filename, ContentFile(response.content), save=True)
                    self.stdout.write(f"Saved image for {model_instance}")
                    image_saved = True
                else:
                    self.stdout.write(self.style.WARNING(f"Failed to download {url} (Status {response.status_code})"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving image: {e}"))
            
            # If image failed, save the instance anyway (so text content exists)
            if not image_saved and not model_instance.pk:
                model_instance.save()
                self.stdout.write(self.style.SUCCESS(f"Saved {model_instance} (without image)"))

        # 1. Hero Content
        if not HeroSection.objects.exists():
            hero = HeroSection(
                title="Master The Music",
                subtitle="Join the premier online music learning platform. Master your instrument with personalized guidance from world-class tutors.",
                cta_text="Start Learning Today",
                cta_link="#classes",
                is_active=True
            )
            # Music Concert Background
            save_image_from_url(hero, 'background_image', 'https://images.unsplash.com/photo-1514320291840-2e0a9bf2a9ae?q=80&w=2670&auto=format&fit=crop', 'hero_bg.jpg')
            self.stdout.write("Created Hero Section")

        # 2. About
        about = AboutSection.objects.filter(is_active=True).first()
        if not about:
            about = AboutSection(
                instructor_name="Maestro David",
                bio="With over 15 years of experience performing in international orchestras and teaching hundreds of students globally, David believes every student has a unique voice waiting to be discovered. His teaching style blends classical rigour with modern flexibility.",
                experience_years="15+",
                students_trained="1200+",
                is_active=True
            )
            # Instructor Image - Using a reliable URL (Concert/Musician)
            save_image_from_url(about, 'image', 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?q=80&w=2670', 'instructor.jpg')
            self.stdout.write("Created About Section")
        elif not about.image:
             # Try to fix missing image on existing object
             self.stdout.write("Fixing missing image for About Section...")
             save_image_from_url(about, 'image', 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?q=80&w=2670', 'instructor.jpg')

        # 3. Classes
        if not ClassType.objects.exists():
            classes_data = [
                {
                    'title': '1-on-1 Guitar Mastery',
                    'description': 'Personalized lessons tailored to your pace. Learn chords, scales, and your favorite songs.',
                    'price': '₹2000/mo',
                    'icon': '🎸',
                    'order': 1
                },
                {
                    'title': 'Piano Foundations',
                    'description': 'From reading sheets to playing concertos. Perfect for beginners to intermediate players.',
                    'price': '₹2500/mo',
                    'icon': '🎹',
                    'order': 2
                },
                {
                    'title': 'Vocal Training',
                    'description': 'Find your voice. Breath control, pitch correction, and performance techniques.',
                    'price': '₹1800/mo',
                    'icon': '🎤',
                    'order': 3
                }
            ]
            for data in classes_data:
                ClassType.objects.create(**data)
            self.stdout.write("Created Classes")

        # 4. Testimonials (Need 10 for carousel)
        if Testimonial.objects.count() < 10:
            existing_count = Testimonial.objects.count()
            data = [
                {'quote': 'I never thought I could play guitar this well in just 3 months. The 1-on-1 sessions are a game changer!', 'name': 'Sarah Jenkins', 'role': 'Guitar Student', 'img': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?q=80&w=1000'},
                {'quote': 'The instructor is incredibly patient and knowledgeable. Highly recommended for anyone serious about music.', 'name': 'Rahul Sharma', 'role': 'Piano Student', 'img': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?q=80&w=1000'},
                {'quote': 'Online classes felt just like real ones. The audio quality and teaching method were superb.', 'name': 'Emily Clark', 'role': 'Vocal Student', 'img': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?q=80&w=1000'},
                {'quote': 'Best decision I made deeply in love with the piano course. The structure is fantastic.', 'name': 'Michael Chen', 'role': 'Piano Student', 'img': 'https://images.unsplash.com/photo-1506794778202-cad84cf45f1d?q=80&w=1000'},
                {'quote': 'Finally found a mentor who understands my pace. My vocal range has improved significantly.', 'name': 'Jessica Lee', 'role': 'Vocal Student', 'img': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=1000'},
                {'quote': 'From zero to playing my favorite songs in weeks. The lessons are so engaging!', 'name': 'David Miller', 'role': 'Guitar Student', 'img': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?q=80&w=1000'},
                {'quote': 'Highly professional and fun. The recording workshops are a huge bonus.', 'name': 'Sophie Turner', 'role': 'Production Student', 'img': 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?q=80&w=1000'},
                {'quote': 'I joined for hobby, effectively stayed for the career guidance. Amazing community.', 'name': 'James Wilson', 'role': 'Violin Student', 'img': 'https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?q=80&w=1000'},
                {'quote': 'The flexibility of online classes matches my busy schedule perfectly. 10/10.', 'name': 'Anita Roy', 'role': 'Flute Student', 'img': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?q=80&w=1000'},
                {'quote': 'My son loves the drum lessons. He practices every day without me asking!', 'name': 'Robert Brown', 'role': 'Parent', 'img': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?q=80&w=1000'},
            ]
            
            # Add only new ones
            for i, t in enumerate(data):
                if not Testimonial.objects.filter(student_name=t['name']).exists():
                    obj = Testimonial(student_name=t['name'], role=t['role'], quote=t['quote'], is_active=True)
                    save_image_from_url(obj, 'student_image', t['img'], f"student_{t['name'].split()[0].lower()}.jpg")
            self.stdout.write("Created/Updated Testimonials to 10 entries")

        # 5. Gallery
        if not GalleryImage.objects.exists():
            gallery_data = [
                {'caption': 'Live Concert 2024', 'url': 'https://images.unsplash.com/photo-1511379938547-c1f69419868d?q=80&w=2670'},
                {'caption': 'Student Workshop', 'url': 'https://images.unsplash.com/photo-1465847899078-b413929f7120?q=80&w=2670'},
                {'caption': 'Recording Session', 'url': 'https://images.unsplash.com/photo-1598488035139-bdbb2231ce04?q=80&w=2670'},
                {'caption': 'Annual Meetup', 'url': 'https://images.unsplash.com/photo-1520523839897-bd0b52f945a0?q=80&w=2670'},
            ]
            for i, item in enumerate(gallery_data):
                obj = GalleryImage(caption=item['caption'], order=i, is_active=True)
                save_image_from_url(obj, 'image', item['url'], f"gallery_{i}.jpg")
            self.stdout.write("Created Gallery")

        # 6. FAQ
        if not FAQ.objects.exists():
            faqs = [
                {'question': 'Do I need my own instrument?', 'answer': 'Yes, for the best learning experience, you should have access to your instrument for daily practice.'},
                {'question': 'Can I reschedule a class?', 'answer': 'Absolutely. We offer flexible scheduling. Just give us a 24-hour notice.'},
                {'question': 'Is this suitable for absolute beginners?', 'answer': 'Yes! We specialized in taking students from zero to hero.'},
                {'question': 'How are classes conducted?', 'answer': 'Classes are held live via Zoom/Google Meet with high-quality audio setups.'},
            ]
            for f in faqs:
                FAQ.objects.create(question=f['question'], answer=f['answer'], is_active=True, order=0)
            self.stdout.write("Created FAQs")

        self.stdout.write(self.style.SUCCESS("Successfully populated landing page data!"))
