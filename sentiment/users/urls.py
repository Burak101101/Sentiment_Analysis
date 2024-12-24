from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
app_name = 'users'

urlpatterns = [
    path("", views.index, name="index"),
    path('register/', views.register_view, name="register"),
    path('profile/', views.update_profile, name='profile'),
    path('password_change/', auth_views.PasswordChangeView.as_view(), name='password_change'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('login/', auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='home'), name='logout'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]
