from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from .views import *
from faturas.views import edit_profile


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('faturas.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', logout_view, name='logout'),
    path('accounts/minha_conta/', minha_conta, name='minha-conta'),
    path('accounts/perfil/', edit_profile, name='edit_profile'),
]

