from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from rest_framework import generics
from django.contrib.auth.models import User
from .forms import RegisterForm, UserUpdateForm



def update_profile(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('home')
    else:
        user_form = UserUpdateForm(instance=request.user)
    return render(request, 'users/update_profile.html', {'user_form': user_form})
def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            login(request, user)
            return redirect('home')
    else:
        form = RegisterForm()
    return render(request, 'users/register.html', {'form': form})

@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()
        return redirect('home')
    return render(request, 'users/confirm_delete_account.html')


def index(request):
    return HttpResponse("Users home.")