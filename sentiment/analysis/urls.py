from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.filtered_analysis, name='analyze_subreddit_page'),
    path("compare/", views.compare_subreddits_page, name="compare_subreddits"),  # Yeni sayfa
    path('filter/', views.filtered_analysis, name='filter'),  # Yeni eklenen URL pattern
    path('ai-analysis/', views.ai_analysis, name='ai_analysis'),
    path('reports/', views.user_reports, name='user_reports'),
    path('reports/download/<int:report_id>/', views.download_report_pdf, name='download_report_pdf'),

]
