from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *



urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('faturas.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/minha_conta/', minha_conta, name='minha-conta'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='profile/password_change_form.html',
        success_url='/accounts/password_change/done/'
    ), name='password_change'),

    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='profile/password_change_done.html'
    ), name='password_change_done'),
    #path('accounts/perfil/', edit_profile, name='edit_profile'),
]

