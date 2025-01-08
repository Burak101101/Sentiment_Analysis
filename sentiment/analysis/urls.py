from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Ana sayfa (ama sentiment/urlsde var maksat /analysis boş olmasın)
    path('filter/', views.filter_page, name='filter'),  # Filtreleme sayfası
    path('results/', views.results_page, name='results'),  # Sonuçlar sayfası
    path('ai-analysis/', views.ai_analysis, name='ai_analysis'),
    path('reports/', views.user_reports, name='user_reports'),
    path('reports/download/<int:report_id>/', views.download_report_pdf, name='download_report_pdf'),
    path('analyze-text/', views.analyze_text, name='analyze_text'),

]