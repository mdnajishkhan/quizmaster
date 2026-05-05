from django.db import models

class HeroSection(models.Model):
    is_active = models.BooleanField(default=False, help_text="Only one Hero section can be active at a time.")
    title_tag = models.CharField(max_length=255, default="RecgetUp Music | Vocal Excellence", help_text="Browser tab title")
    
    # English
    badge_en = models.CharField(max_length=100, default="PREMIUM CLASSICAL ACADEMY")
    title_en = models.CharField(max_length=255, default="Master the Soul of Hindustani Classical Vocal")
    desc_en = models.TextField(default="A scientifically designed journey from basic swars to advanced Raga mastery. Join our exclusive workshop to transform your vocal technique.")
    btn_join_en = models.CharField(max_length=100, default="Join Free Workshop")
    btn_register_en = models.CharField(max_length=100, default="Register Now")
    
    # Hindi
    badge_hi = models.CharField(max_length=100, default="प्रीमियम शास्त्रीय अकादमी")
    title_hi = models.CharField(max_length=255, default="हिंदुस्तानी शास्त्रीय गायन की आत्मा में महारत हासिल करें")
    desc_hi = models.TextField(default="बुनियादी स्वरों से लेकर उन्नत राग महारत तक की एक वैज्ञानिक रूप से तैयार की गई यात्रा। अपनी गायन तकनीक को बदलने के लिए हमारी विशेष वर्कशॉप में शामिल हों।")
    btn_join_hi = models.CharField(max_length=100, default="फ्री वर्कशॉप ज्वाइन करें")
    btn_register_hi = models.CharField(max_length=100, default="अभी रजिस्टर करें")
    
    image = models.ImageField(upload_to='landing/hero/', blank=True, null=True, help_text="Main Hero Image (Foreground)")
    background_image = models.ImageField(upload_to='landing/hero/bg/', blank=True, null=True, help_text="Background Image for Hero")

    def save(self, *args, **kwargs):
        if self.is_active:
            HeroSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Hero Section {self.id} ({'Active' if self.is_active else 'Inactive'})"

class MarqueeSection(models.Model):
    is_active = models.BooleanField(default=False)
    text_en = models.CharField(max_length=500, default="Free Workshop Starting Soon • Limited Free Seats Available • Reserve Your Spot Now")
    text_hi = models.CharField(max_length=500, default="फ्री वर्कशॉप जल्द शुरू हो रही है • सीमित सीटें उपलब्ध • अपनी सीट अभी सुरक्षित करें")

    def save(self, *args, **kwargs):
        if self.is_active:
            MarqueeSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class MasterySection(models.Model):
    is_active = models.BooleanField(default=False)
    subtitle_en = models.CharField(max_length=200, default="Your Transformation")
    subtitle_hi = models.CharField(max_length=200, default="आपका परिवर्तन")
    title_en = models.CharField(max_length=255, default="What You Will Master")
    title_hi = models.CharField(max_length=255, default="आप क्या सीखेंगे")
    desc_en = models.TextField(default="Three pillars of your scientific musical journey.")
    desc_hi = models.TextField(default="आपकी संगीतमय यात्रा के तीन मुख्य स्तंभ।")
    background_image = models.ImageField(upload_to='landing/mastery/bg/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            MasterySection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class MasteryCard(models.Model):
    section = models.ForeignKey(MasterySection, related_name='cards', on_delete=models.CASCADE)
    title_en = models.CharField(max_length=200)
    title_hi = models.CharField(max_length=200)
    desc_en = models.TextField()
    desc_hi = models.TextField()
    image = models.ImageField(upload_to='landing/mastery/')
    icon_class = models.CharField(max_length=50, default="lucide-mic-2")
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class CurriculumSection(models.Model):
    is_active = models.BooleanField(default=False)
    subtitle_en = models.CharField(max_length=200, default="The Learning Path")
    subtitle_hi = models.CharField(max_length=200, default="सीखने की राह")
    title_en = models.CharField(max_length=255, default="Workshop Schedule")
    title_hi = models.CharField(max_length=255, default="वर्कशॉप शेड्यूल")
    desc_en = models.TextField(default="A scientifically structured journey into the depths of Hindustani Classical Vocal.")
    desc_hi = models.TextField(default="हिंदुस्तानी शास्त्रीय गायन की गहराइयों में एक वैज्ञानिक रूप से संरचित यात्रा।")
    background_image = models.ImageField(upload_to='landing/curriculum/bg/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            CurriculumSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class CurriculumStep(models.Model):
    section = models.ForeignKey(CurriculumSection, related_name='steps', on_delete=models.CASCADE)
    title_en = models.CharField(max_length=200)
    title_hi = models.CharField(max_length=200)
    desc_en = models.TextField()
    desc_hi = models.TextField()
    image = models.ImageField(upload_to='landing/curriculum/', blank=True, null=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class MentorSection(models.Model):
    is_active = models.BooleanField(default=False)
    subtitle_en = models.CharField(max_length=200, default="Your Guide & Mentor")
    subtitle_hi = models.CharField(max_length=200, default="आपके मार्गदर्शक और मेंटर")
    name_en = models.CharField(max_length=255, default="Md Shahbaz Khan")
    name_hi = models.CharField(max_length=255, default="MD SHAHBAZ KHAN")
    tagline_en = models.CharField(max_length=255, default="Classical Vocal Mentor")
    tagline_hi = models.CharField(max_length=255, default="शास्त्रीय गायन शिक्षक")
    quote_en = models.TextField(default="“True classical training is about discipline, patience, and discovering the depth of your own voice.”")
    quote_hi = models.TextField(default="“सच्चा शास्त्रीय प्रशिक्षण अनुशासन, धैर्य और अपनी आवाज़ की गहराई को खोजने के बारे में है।”")
    bio_en = models.TextField(default="With years of dedicated training in Hindustani Classical music, Md Shahbaz Khan has mentored students across all levels.")
    bio_hi = models.TextField(default="हिंदुस्तानी शास्त्रीय संगीत में वर्षों के समर्पित प्रशिक्षण के साथ, एमडी शाहबाज़ खान ने सभी स्तरों के छात्रों को प्रशिक्षित किया है।")
    image = models.ImageField(upload_to='landing/mentor/', blank=True, null=True)
    background_image = models.ImageField(upload_to='landing/mentor/bg/', blank=True, null=True)
    
    # Stats
    exp_num = models.CharField(max_length=50, default="15+")
    exp_label_en = models.CharField(max_length=100, default="Years Experience")
    exp_label_hi = models.CharField(max_length=100, default="वर्षों का अनुभव")
    students_num = models.CharField(max_length=50, default="500+")
    students_label_en = models.CharField(max_length=100, default="Vocalists Trained")
    students_label_hi = models.CharField(max_length=100, default="छात्र प्रशिक्षित")

    def save(self, *args, **kwargs):
        if self.is_active:
            MentorSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class PricingSection(models.Model):
    is_active = models.BooleanField(default=False)
    label_en = models.CharField(max_length=100, default="Workshop Value")
    label_hi = models.CharField(max_length=100, default="वर्कशॉप की वैल्यू")
    old_price = models.IntegerField(default=499)
    new_price = models.IntegerField(default=0)
    tag_free_en = models.CharField(max_length=50, default="FREE")
    tag_free_hi = models.CharField(max_length=50, default="मुफ्त")

    def save(self, *args, **kwargs):
        if self.is_active:
            PricingSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class TimerSection(models.Model):
    is_active = models.BooleanField(default=False)
    title_en = models.CharField(max_length=255, default="Seats Filling Fast for Free Session")
    title_hi = models.CharField(max_length=255, default="फ्री सेशन के लिए सीटें तेज़ी से भर रही हैं")
    desc_en = models.TextField(default="Limited free seats available for the upcoming session. Secure your spot before enrollment closes.")
    desc_hi = models.TextField(default="आने वाले सेशन के लिए सीमित मुफ़्त सीटें। नामांकन बंद होने से पहले अपना स्थान सुरक्षित करें।")
    btn_text_en = models.CharField(max_length=100, default="Reserve My Seat")
    btn_text_hi = models.CharField(max_length=100, default="अपनी सीट सुरक्षित करें")
    target_date = models.DateTimeField(null=True, blank=True, help_text="The date and time the countdown ends.")
    background_image = models.ImageField(upload_to='landing/timer/bg/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            TimerSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class GallerySection(models.Model):
    is_active = models.BooleanField(default=False)
    title_en = models.CharField(max_length=200, default="Inside the Academy")
    title_hi = models.CharField(max_length=200, default="अकादमी के अंदर")
    desc_en = models.TextField(default="A glimpse into our soulful musical environment.")
    desc_hi = models.TextField(default="हमारे संगीतमय वातावरण की एक झलक।")
    background_image = models.ImageField(upload_to='landing/gallery/bg/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            GallerySection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class GalleryImage(models.Model):
    section = models.ForeignKey(GallerySection, related_name='images', on_delete=models.CASCADE)
    media_file = models.FileField(upload_to='landing/gallery/', help_text="Upload an Image or Video file.")
    alt_text = models.CharField(max_length=200, blank=True)
    is_main = models.BooleanField(default=False, help_text="Show this as the large feature image.")
    order = models.PositiveIntegerField(default=0)

    @property
    def is_video(self):
        if not self.media_file: return False
        return self.media_file.name.lower().endswith(('.mp4', '.webm', '.ogg', '.mov'))

    def __str__(self):
        return f"Media {self.id} - {self.media_file.name}"

    class Meta:
        ordering = ['order']

class FAQSection(models.Model):
    is_active = models.BooleanField(default=False)
    title_en = models.CharField(max_length=200, default="Frequently Asked Questions")
    title_hi = models.CharField(max_length=200, default="अक्सर पूछे जाने वाले प्रश्न")

    def save(self, *args, **kwargs):
        if self.is_active:
            FAQSection.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

class FAQItem(models.Model):
    section = models.ForeignKey(FAQSection, related_name='items', on_delete=models.CASCADE)
    question_en = models.CharField(max_length=500)
    question_hi = models.CharField(max_length=500)
    answer_en = models.TextField()
    answer_hi = models.TextField()
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

class WorkshopRegistration(models.Model):
    EXP_CHOICES = [
        ('0-1', '0–1 Years'),
        ('1-2', '1–2 Years'),
        ('2-3', '2–3 Years'),
        ('Above 3', 'Above 3 Years'),
    ]
    INSTRUMENT_CHOICES = [
        ('Harmonium', 'Harmonium'),
        ('Tanpura', 'Tanpura'),
    ]
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    whatsapp_number = models.CharField(max_length=15)
    age = models.IntegerField(null=True, blank=True)
    state = models.CharField(max_length=100)
    experience = models.CharField(max_length=50, choices=EXP_CHOICES)
    instrument = models.CharField(max_length=50, choices=INSTRUMENT_CHOICES)
    swar_identification = models.CharField(max_length=10, default="No") # Yes/No
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.whatsapp_number})"

class VocalWorkshopQuery(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
class SiteSettings(models.Model):
    is_active = models.BooleanField(default=False)
    whatsapp_link = models.URLField(default="https://chat.whatsapp.com/JqEzO72JNggAi6fErSWrxX")
    contact_email = models.EmailField(default="info@recgetup.com")
    contact_phone = models.CharField(max_length=20, default="+91 00000 00000")
    instagram_link = models.URLField(blank=True, null=True)
    youtube_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)
    copyright_text = models.CharField(max_length=255, default="© 2026 RECGETUP MUSIC. CRAFTED FOR MUSICAL EXCELLENCE.")
    body_background = models.ImageField(upload_to='landing/site/bg/', blank=True, null=True)
    footer_background = models.ImageField(upload_to='landing/site/footer/', blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.is_active:
            SiteSettings.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Site Settings {self.id} ({'Active' if self.is_active else 'Inactive'})"
