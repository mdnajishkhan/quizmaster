from .models import (
    Coupon, Enrollment, ContactQuery, WorkshopPackage,
    HeroSection, AboutSection, ClassType, Testimonial, GalleryImage, FAQ
)

# --- SALES & ENROLLMENTS ---
class SalesCoupon(Coupon):
    class Meta:
        proxy = True
        app_label = 'training_sales'
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'

class SalesEnrollment(Enrollment):
    class Meta:
        proxy = True
        app_label = 'training_sales'
        verbose_name = 'Active Enrollment'
        verbose_name_plural = 'Active Enrollments'

class SalesInquiry(ContactQuery):
    class Meta:
        proxy = True
        app_label = 'training_sales'
        verbose_name = 'Website Inquiry'
        verbose_name_plural = 'Website Inquiries'

class SalesPackage(WorkshopPackage):
    class Meta:
        proxy = True
        app_label = 'training_sales'
        verbose_name = 'Pricing Package'
        verbose_name_plural = 'Pricing Packages'


# --- WEBSITE CONTENT ---
class ContentHero(HeroSection):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'Hero Section'
        verbose_name_plural = 'Hero Sections'

class ContentAbout(AboutSection):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'About Section'
        verbose_name_plural = 'About Sections'

class ContentClassType(ClassType):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'Class Type'
        verbose_name_plural = 'Class Types'

class ContentTestimonial(Testimonial):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'Testimonial'
        verbose_name_plural = 'Testimonials'

class ContentGallery(GalleryImage):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'Gallery Image'
        verbose_name_plural = 'Gallery Images'

class ContentFAQ(FAQ):
    class Meta:
        proxy = True
        app_label = 'training_content'
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
