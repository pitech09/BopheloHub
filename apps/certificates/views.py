from io import BytesIO
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
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
    instructor_name = certificate.enrollment.course.instructor.get_full_name() or certificate.enrollment.course.instructor.username
    issued_date = certificate.issued_at.strftime('%B %d, %Y')
    
    # Create a BytesIO buffer for the PDF
    buffer = BytesIO()
    
    # Create the PDF
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.colors import Color
    from reportlab.graphics.shapes import Drawing, Rect, String, Group
    from reportlab.graphics import renderPDF
    
    # Set up the document
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), 
                           rightMargin=0.5*inch, leftMargin=0.5*inch, 
                           topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=36,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_CENTER,
        spaceAfter=30,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=16,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10
    )
    
    name_style = ParagraphStyle(
        'StudentName',
        parent=styles['Heading2'],
        fontSize=28,
        textColor=colors.HexColor('#16213e'),
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=20,
        fontName='Helvetica-Bold'
    )
    
    course_style = ParagraphStyle(
        'CourseTitle',
        parent=styles['Heading2'],
        fontSize=22,
        textColor=colors.HexColor('#0f3460'),
        alignment=TA_CENTER,
        spaceAfter=20,
        spaceBefore=10,
        fontName='Helvetica-Bold'
    )
    
    details_style = ParagraphStyle(
        'Details',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    
    # Add content
    elements.append(Spacer(1, 0.3*inch))
    
    # Logo at top center
    logo_path = 'static/images/logo.png'  # Update with your actual logo path
    try:
        logo = Image(logo_path, width=1.5*inch, height=1.5*inch)
        logo.hAlign = 'CENTER'
        elements.append(logo)
    except Exception as e:
        # If logo fails to load, just skip it
        pass
    elements.append(Spacer(1, 0.3*inch))
    
    # Decorative line
    from reportlab.platypus import Flowable
    class Line(Flowable):
        def __init__(self, width, color=colors.HexColor('#e94560')):
            Flowable.__init__(self)
            self.width = width
            self.color = color
        
        def draw(self):
            canvas = self.canv
            canvas.setStrokeColor(self.color)
            canvas.setFillColor(self.color)
            canvas.setLineWidth(2)
            canvas.line(0, 0, self.width, 0)
    
    elements.append(Line(6*inch, colors.HexColor('#e94560')))
    elements.append(Spacer(1, 0.2*inch))
    
    # Title
    elements.append(Paragraph("CERTIFICATE OF COMPLETION", title_style))
    elements.append(Spacer(1, 0.2*inch))
    
    # Subtitle
    elements.append(Paragraph("This is to certify that", subtitle_style))
    
    # Student name
    elements.append(Paragraph(user_name, name_style))
    
    # Completion text
    elements.append(Paragraph("has successfully completed the course", subtitle_style))
    
    # Course title
    elements.append(Paragraph(course_title, course_style))
    
    # Instructor
    elements.append(Paragraph(f"Instructor: {instructor_name}", details_style))
    
    # Certificate code and date
    elements.append(Paragraph(f"Certificate Code: {certificate.certificate_code}", details_style))
    elements.append(Paragraph(f"Issued: {issued_date}", details_style))
    
    elements.append(Spacer(1, 0.5*inch))
    
    # Signature section
    sig_style = ParagraphStyle(
        'Signature',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        alignment=TA_CENTER,
        spaceBefore=5
    )
    
    # Create signature line
    from reportlab.platypus import Table, TableStyle
    sig_data = [
        ['_________________________', '_________________________'],
        ['Platform Director', 'Date'],
        ['BopheloHub', issued_date],
    ]
    sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(sig_table)
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Footer with logo
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#1a1a2e'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    elements.append(Paragraph("BopheloHub", footer_style))
    elements.append(Paragraph("Empowering Lives Through Education", details_style))
    
    # Bottom decorative line
    elements.append(Spacer(1, 0.2*inch))
    elements.append(Line(6*inch, colors.HexColor('#e94560')))
    
    # Build the PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_code}.pdf"'
    response.write(pdf)
    
    return response
