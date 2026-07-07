from io import BytesIO
from pathlib import Path

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.contrib.staticfiles import finders
from django.conf import settings
from certificates.models import Certificate


@login_required
def certificate_list(request):
    """Display the user's certificates."""
    certificates = request.user.certificate_set.all()
    return render(request, 'certificates/list.html', {'certificates': certificates})


@login_required
def certificate_detail(request, pk):
    """Display a specific certificate."""
    certificate = get_object_or_404(Certificate, pk=pk, enrollment__user=request.user)
    return render(request, 'certificates/detail.html', {'certificate': certificate})


@login_required
def certificate_download(request, pk):
    """Download a certificate as a PDF file."""
    certificate = get_object_or_404(Certificate, pk=pk, enrollment__user=request.user)

    # Get certificate data
    user_name = certificate.enrollment.user.get_full_name() or certificate.enrollment.user.username
    course_title = certificate.enrollment.course.title
    issued_date = certificate.issued_at.strftime('%B %d, %Y')

    # Create a BytesIO buffer for the PDF
    buffer = BytesIO()

    # Create the PDF
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER

    # Set up the document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()

    # Custom styles
    title_accent = colors.HexColor('#0071e3')
    text_primary = colors.HexColor('#1d1d1f')
    text_secondary = colors.HexColor('#6e6e73')

    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=26,
        leading=30,
        textColor=text_primary,
        alignment=TA_CENTER,
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=15,
        textColor=text_secondary,
        alignment=TA_CENTER,
        spaceAfter=8,
    )

    name_style = ParagraphStyle(
        'StudentName',
        parent=styles['Heading2'],
        fontSize=24,
        leading=28,
        textColor=title_accent,
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=8,
        fontName='Helvetica-Bold'
    )

    course_style = ParagraphStyle(
        'CourseTitle',
        parent=styles['Heading2'],
        fontSize=18,
        leading=22,
        textColor=text_primary,
        alignment=TA_CENTER,
        spaceAfter=10,
        spaceBefore=4,
        fontName='Helvetica-Bold'
    )

    details_style = ParagraphStyle(
        'Details',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=text_secondary,
        alignment=TA_CENTER,
        spaceAfter=0,
    )

    meta_style = ParagraphStyle(
        'Meta',
        parent=styles['Normal'],
        fontSize=10,
        leading=12,
        textColor=text_secondary,
        alignment=TA_CENTER,
    )

    # Add content
    elements.append(Spacer(1, 0.15 * inch))

    # Logo at top center
    logo_path = finders.find('img/bh-elearning-logo.png')
    if not logo_path:
        logo_path = Path(settings.BASE_DIR) / 'static' / 'img' / 'bh-elearning-logo.png'

    if logo_path and Path(logo_path).exists():
        try:
            logo = Image(str(logo_path), width=1.0 * inch, height=1.0 * inch)
            logo.hAlign = 'CENTER'
            elements.append(logo)
        except Exception:
            # If the logo cannot be rendered, continue without it.
            pass

    elements.append(Spacer(1, 0.16 * inch))
    elements.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    elements.append(Spacer(1, 0.1 * inch))
    elements.append(Paragraph("This certifies that", subtitle_style))
    elements.append(Paragraph(user_name, name_style))
    elements.append(Paragraph("has successfully completed", subtitle_style))
    elements.append(Paragraph(course_title, course_style))
    elements.append(Spacer(1, 0.08 * inch))

    meta_table = Table(
        [
            [Paragraph(f"Certificate Code: <b>{certificate.certificate_code}</b>", meta_style)],
            [Paragraph(f"Issued: <b>{issued_date}</b>", meta_style)],
        ],
        colWidths=[6.6 * inch],
    )
    meta_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f5f5f7')),
        ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor('#d2d2d7')),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e8e8ed')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(meta_table)

    def draw_certificate_frame(canvas, _doc):
        canvas.saveState()
        width, height = landscape(letter)
        canvas.setStrokeColor(title_accent)
        canvas.setLineWidth(1.5)
        margin = 0.35 * inch
        canvas.roundRect(
            margin,
            margin,
            width - (2 * margin),
            height - (2 * margin),
            radius=12,
            stroke=1,
            fill=0,
        )
        canvas.setStrokeColor(colors.HexColor('#e8e8ed'))
        canvas.setLineWidth(0.6)
        canvas.line(margin + 0.12 * inch, height - 1.0 * inch, width - margin - 0.12 * inch, height - 1.0 * inch)
        canvas.restoreState()

    # Build the PDF
    doc.build(elements, onFirstPage=draw_certificate_frame, onLaterPages=draw_certificate_frame)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_code}.pdf"'
    response.write(pdf)
    
    return response
