from io import BytesIO
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from django.utils import timezone

from django.conf import settings
import os

def generate_certificate_pdf(attempt):
    """
    Generates a PDF certificate for the given attempt.
    Returns a BytesIO buffer containing the PDF.
    Design: Precise User Specifications (Premium).
    """
    buffer = BytesIO()
    
    # Create the PDF object
    p = canvas.Canvas(buffer, pagesize=landscape(letter))
    width, height = landscape(letter)  # 792 x 612 approx
    center_x = width / 2
    
    # --- ASSETS (FIX: Use Absolute Paths) ---
    bg_path = os.path.join(settings.BASE_DIR, "media/certificates/certificate_bg.png")
    logo_path = os.path.join(settings.BASE_DIR, "media/certificates/logo.png")
    
    # --- COLORS ---
    COLOR_TEAL = HexColor("#0f766e")
    COLOR_DARK = HexColor("#111827")
    COLOR_GRAY = HexColor("#374151")
    
    # --- 1. BACKGROUND ---
    try:
        p.drawImage(bg_path, 0, 0, width=width, height=height, mask='auto')
    except Exception:
        # Fallback
        p.setFillColor(HexColor("#FFFFFF"))
        p.rect(0, 0, width, height, fill=1)
        p.setStrokeColor(COLOR_TEAL)
        p.setLineWidth(5)
        p.rect(20, 20, width - 40, height - 40)
    
    # --- 2. HEADER ---
    # TGAYS Logo - Top Left
    try:
        logo_w = 120
        # Position at Top Left: x=40, y=height-100
        p.drawImage(logo_path, 40, height - 90, width=logo_w, preserveAspectRatio=True, mask='auto')
    except Exception:
        pass

    # "CERTIFICATE"
    p.setFont("Times-Bold", 40)
    p.setFillColor(COLOR_TEAL)
    p.drawCentredString(center_x, height - 135, "CERTIFICATE")
    
    # "OF ACHIEVEMENT"
    p.setFont("Times-Roman", 12)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x, height - 155, "OF ACHIEVEMENT")

    # --- 3. PRESENTATION TEXT ---
    p.setFont("Times-Roman", 11)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x, height - 185, "This Certificate is Proudly Presented by")
    
    p.setFont("Times-Bold", 14)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x, height - 205, "TGAYS Technology Private Limited")
    
    p.setFont("Times-Italic", 11)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x, height - 230, "This is to certify that")

    # --- 4. RECIPIENT ---
    # STUDENT NAME (Prominent)
    user_name = attempt.user.get_full_name() or attempt.user.username
    p.setFont("Times-Bold", 30)
    p.setFillColor(COLOR_TEAL)
    p.drawCentredString(center_x, height - 265, user_name.title())

    # College Name
    if hasattr(attempt.user, 'profile') and attempt.user.profile.college:
        college_text = attempt.user.profile.college.name
        p.setFont("Times-Roman", 11)
        p.setFillColor(COLOR_DARK)
        p.drawCentredString(center_x, height - 285, f"from {college_text}")

    # --- 5. EVENT DETAILS ---
    # Quiz Title & Type
    quiz_title = attempt.quiz.title
    event_type = "Quiz"
    if attempt.quiz.quiz_type == 'hackathon':
        event_type = "Hackathon"
    elif "challenge" in quiz_title.lower():
        event_type = "Coding Challenge"
        
    p.setFont("Times-Roman", 11)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x, height - 315, f"has successfully participated in the {event_type} titled")
    
    # Event Title
    p.setFont("Times-Bold", 18)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x, height - 340, f"“{quiz_title}”")
    
    # Organizer line
    p.setFont("Times-Roman", 11)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x, height - 365, "organized by TGAYS Technology Private Limited.")

    # Description Paragraph
    # We need to wrap this text if it's too long, but for a certificate line, we can just split it manually or center it relative to width
    desc_line1 = "The participant demonstrated strong analytical thinking, problem-solving ability,"
    desc_line2 = "and technical competence while working on real-world challenges during the event."
    
    p.setFont("Times-Roman", 10)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x, height - 395, desc_line1)
    p.drawCentredString(center_x, height - 410, desc_line2)

    # --- 6. METRICS ---
    total_questions = attempt.quiz.questions.count()
    if total_questions > 0:
        percentage = int((attempt.score / total_questions) * 100)
    else:
        percentage = 0
    
    # FIX: Safety check for finished_at
    fin_date = attempt.finished_at if attempt.finished_at else timezone.now()
    date_str = fin_date.strftime("%B %d, %Y")

    # Layout: Score on Left, Date on Right? Or Centered block? 
    # User prompt showed them stacked: "Performance Score / {{Percentage}}% / Date: {{Date}}"
    
    y_metrics = height - 445
    p.setFont("Times-Bold", 11)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x, y_metrics, "Performance Score")
    
    p.setFont("Times-Bold", 16)
    p.setFillColor(COLOR_TEAL)
    p.drawCentredString(center_x, y_metrics - 20, f"{percentage}%")
    
    p.setFont("Times-Bold", 11)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x, y_metrics - 40, f"Date: {date_str}")

    # --- 7. SLOGAN ---
    y_slogan = 80 # Just above signatures
    p.setFont("Times-Italic", 9)
    p.setFillColor(COLOR_TEAL)
    p.drawCentredString(center_x, y_slogan + 10, "Empowering Innovation.")
    p.drawCentredString(center_x, y_slogan, "Building Future-Ready Technologists.")

    # --- 8. SIGNATURES ---
    sig_y = 40
    p.setLineWidth(0.8)
    p.setStrokeColor(COLOR_DARK)
    
    # Left: Jamal Ashraf
    p.line(center_x - 240, sig_y + 20, center_x - 100, sig_y + 20)
    
    p.setFont("Times-Bold", 10)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x - 170, sig_y + 8, "Jamal Ashraf")
    
    p.setFont("Times-Roman", 8)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x - 170, sig_y - 2, "Director")
    p.drawCentredString(center_x - 170, sig_y - 12, "TGAYS Technology Pvt. Ltd.")

    # Right: Md Najish Khan
    p.line(center_x + 100, sig_y + 20, center_x + 240, sig_y + 20)
    
    p.setFont("Times-Bold", 10)
    p.setFillColor(COLOR_DARK)
    p.drawCentredString(center_x + 170, sig_y + 8, "Md Najish Khan")
    
    p.setFont("Times-Roman", 8)
    p.setFillColor(COLOR_GRAY)
    p.drawCentredString(center_x + 170, sig_y - 2, "Software Engineer (Instructor)")
    p.drawCentredString(center_x + 170, sig_y - 12, "TGAYS Technology Pvt. Ltd.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer
