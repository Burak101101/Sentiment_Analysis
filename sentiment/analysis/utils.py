# utils.py

import pdfkit
from django.template.loader import render_to_string
from django.conf import settings
import os


def generate_pdf_report(report):
    """AI raporundan PDF oluşturur"""

    # PDF template'ini hazırla
    context = {
        'report': report,
        'title': str(report),
        'date': report.created_at.strftime('%Y-%m-%d %H:%M')
    }

    # HTML template'i render et
    html_string = render_to_string('analysis/pdf_report_template.html', context)

    # pdfkit yapılandırması
    options = {
        'page-size': 'A4',
        'margin-top': '0.75in',
        'margin-right': '0.75in',
        'margin-bottom': '0.75in',
        'margin-left': '0.75in',
        'encoding': "UTF-8",
        'no-outline': None,
        'enable-local-file-access': None
    }

    # Windows için wkhtmltopdf yolunu belirt
    config = None
    if os.name == 'nt':  # Windows işletim sistemi kontrolü
        config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
        pdf = pdfkit.from_string(html_string, False, options=options, configuration=config)
    else:
        pdf = pdfkit.from_string(html_string, False, options=options)

    return pdf