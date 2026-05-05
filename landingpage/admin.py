from django.contrib import admin
from .models import (
    WorkshopRegistration, VocalWorkshopQuery, 
    HeroSection, MarqueeSection, MasterySection, MasteryCard,
    CurriculumSection, CurriculumStep, MentorSection, PricingSection, TimerSection,
    GallerySection, GalleryImage, FAQSection, FAQItem, SiteSettings
)
from django.contrib.auth.models import User, Group
from django.contrib.auth.admin import UserAdmin, GroupAdmin

# Customize Default User Admin
admin.site.unregister(User)
@admin.register(User)
class CustomUserAdmin(UserAdmin):
    def serial_number(self, obj):
        return list(User.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number',) + UserAdmin.list_display
    ordering = ['-id']

# Customize Default Group Admin
admin.site.unregister(Group)
@admin.register(Group)
class CustomGroupAdmin(GroupAdmin):
    def serial_number(self, obj):
        return list(Group.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name')
    ordering = ['-id']

# Custom Admin Ordering (Matches Website Flow)
def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    if not app_dict: return []
    
    # Precise ordering to match the website's scroll sequence
    model_order = {
        'HeroSection': 1,
        'MarqueeSection': 2,
        'MasterySection': 3,
        'CurriculumSection': 4,
        'MentorSection': 5,
        'GallerySection': 6,
        'TimerSection': 7,
        'PricingSection': 8,
        'FAQSection': 9,
        'SiteSettings': 10,
        'VocalWorkshopQuery': 11,
        'WorkshopRegistration': 12,
    }

    app_list = list(app_dict.values())
    for app in app_list:
        if app['app_label'] == 'landingpage':
            app['models'].sort(key=lambda x: model_order.get(x['object_name'], 100))
    return app_list

admin.AdminSite.get_app_list = get_app_list

# Inlines for better management
class MasteryCardInline(admin.StackedInline):
    model = MasteryCard
    extra = 1
    fieldsets = (
        ('English Content', {'fields': ('title_en', 'desc_en', 'image')}),
        ('Hindi Content (हिन्दी)', {'fields': ('title_hi', 'desc_hi')}),
    )

class CurriculumStepInline(admin.StackedInline):
    model = CurriculumStep
    extra = 1
    fieldsets = (
        ('English Content', {'fields': ('title_en', 'desc_en', 'image')}),
        ('Hindi Content (हिन्दी)', {'fields': ('title_hi', 'desc_hi')}),
    )

class GalleryImageInline(admin.TabularInline):
    model = GalleryImage
    extra = 3
    fields = ('media_file', 'alt_text', 'is_main', 'order')

class FAQItemInline(admin.StackedInline):
    model = FAQItem
    extra = 3
    fieldsets = (
        ('English Content', {'fields': ('question_en', 'answer_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('question_hi', 'answer_hi')}),
    )

# Model Admins
@admin.register(HeroSection)
class HeroSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(HeroSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title_en', 'is_active')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'image', 'background_image', 'title_tag')}),
        ('English Content', {'fields': ('badge_en', 'title_en', 'desc_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('badge_hi', 'title_hi', 'desc_hi')}),
    )

@admin.register(MarqueeSection)
class MarqueeSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(MarqueeSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'text_en', 'is_active')
    list_display_links = ('serial_number', 'text_en')
    ordering = ['-id']
    save_on_top = True
    fieldsets = (
        ('Settings', {'fields': ('is_active',)}),
        ('English Content', {'fields': ('text_en',)}),
        ('Hindi Content (हिन्दी)', {'fields': ('text_hi',)}),
    )

@admin.register(MasterySection)
class MasterySectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(MasterySection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title_en', 'is_active')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    inlines = [MasteryCardInline]
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'background_image')}),
        ('English Content', {'fields': ('subtitle_en', 'title_en', 'desc_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('subtitle_hi', 'title_hi', 'desc_hi')}),
    )

@admin.register(CurriculumSection)
class CurriculumSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(CurriculumSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title_en', 'is_active')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    inlines = [CurriculumStepInline]
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'background_image')}),
        ('English Content', {'fields': ('subtitle_en', 'title_en', 'desc_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('subtitle_hi', 'title_hi', 'desc_hi')}),
    )

@admin.register(MentorSection)
class MentorSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(MentorSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name_en', 'is_active')
    list_display_links = ('serial_number', 'name_en')
    ordering = ['-id']
    save_on_top = True
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'image', 'background_image')}),
        ('English Content', {
            'fields': ('subtitle_en', 'name_en', 'tagline_en', 'quote_en', 'bio_en', 'exp_label_en', 'students_label_en')
        }),
        ('Hindi Content (हिन्दी)', {
            'fields': ('subtitle_hi', 'name_hi', 'tagline_hi', 'quote_hi', 'bio_hi', 'exp_label_hi', 'students_label_hi')
        }),
    )

@admin.register(PricingSection)
class PricingSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(PricingSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'label_en', 'is_active')
    list_display_links = ('serial_number', 'label_en')
    ordering = ['-id']
    save_on_top = True
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'old_price', 'new_price')}),
        ('English Content', {'fields': ('label_en', 'tag_free_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('label_hi', 'tag_free_hi')}),
    )

@admin.register(TimerSection)
class TimerSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(TimerSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title_en', 'is_active')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'target_date', 'background_image')}),
        ('English Content', {'fields': ('title_en', 'desc_en', 'btn_text_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('title_hi', 'desc_hi', 'btn_text_hi')}),
    )

@admin.register(GallerySection)
class GallerySectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(GallerySection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'is_active', 'title_en')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    inlines = [GalleryImageInline]
    fieldsets = (
        ('Settings', {'fields': ('is_active', 'background_image')}),
        ('English Content', {'fields': ('title_en', 'desc_en')}),
        ('Hindi Content (हिन्दी)', {'fields': ('title_hi', 'desc_hi')}),
    )

@admin.register(FAQSection)
class FAQSectionAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(FAQSection.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'title_en', 'is_active')
    list_display_links = ('serial_number', 'title_en')
    ordering = ['-id']
    save_on_top = True
    inlines = [FAQItemInline]
    fieldsets = (
        ('Settings', {'fields': ('is_active',)}),
        ('English Content', {'fields': ('title_en',)}),
        ('Hindi Content (हिन्दी)', {'fields': ('title_hi',)}),
    )

@admin.register(WorkshopRegistration)
class WorkshopRegistrationAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(WorkshopRegistration.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'full_name', 'whatsapp_number', 'experience', 'instrument', 'created_at')
    list_display_links = ('serial_number', 'full_name')
    ordering = ['-id']
    list_filter = ('experience', 'instrument', 'created_at')
    search_fields = ('full_name', 'whatsapp_number', 'email')
    readonly_fields = ('created_at',)

@admin.register(VocalWorkshopQuery)
class VocalWorkshopQueryAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(VocalWorkshopQuery.objects.all().order_by('-id').values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'
    list_display = ('serial_number', 'name', 'phone', 'email', 'created_at')
    list_display_links = ('serial_number', 'name')
    ordering = ['-id']
    list_filter = ('created_at',)
    search_fields = ('name', 'phone', 'email')
    readonly_fields = ('created_at',)

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    def serial_number(self, obj):
        return list(SiteSettings.objects.all().values_list('id', flat=True)).index(obj.id) + 1
    serial_number.short_description = 'Sr. No.'

    list_display = ('serial_number', 'is_active', 'whatsapp_link', 'contact_email')
    list_editable = ('is_active',)
    list_display_links = ('serial_number', 'whatsapp_link')
    ordering = ['id']
    save_on_top = True
    fieldsets = (
        ('Global Links', {'fields': ('is_active', 'whatsapp_link', 'contact_email', 'contact_phone', 'instagram_link', 'youtube_link', 'facebook_link')}),
        ('Global Aesthetics', {'fields': ('body_background', 'footer_background', 'copyright_text')}),
    )
