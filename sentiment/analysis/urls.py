from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('analyze/', views.analyze_subreddit_page, name='analyze_subreddit_page'),
    path("compare/", views.compare_subreddits_page, name="compare_subreddits"),  # Yeni sayfa
]
