from django.contrib.auth import logout
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from .forms import UserUpdateForm
from django.urls import reverse
from django.contrib.auth.models import User
from faturas.forms import ProfileForm
from faturas.utils.supabase import upload_image_to_supabase

def logout_view(request):
    logout(request)
    return redirect('/')

@login_required
def minha_conta(request):
    user = request.user
    profile = user.profile

    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        #Verifica se o email já está em uso por outro usuário
        if user_form.is_valid() and profile_form.is_valid():
            if User.objects.filter(email=user_form.cleaned_data['email']).exclude(id=user.id).exists():
                user_form.add_error('email', 'Este email já está em uso por outro usuário.')
                return render(request, 'profile/minha_conta.html', {
                    'user_form': user_form,
                    'profile_form': profile_form
                })  
        # Verifica se o formulário de usuário e o de perfil são válidos

       
            user_form.save()

            # Upload da imagem para Supabase, se houver
            photo = request.FILES.get('photo')
            if photo:
                photo_url = upload_image_to_supabase(photo)
                profile.photo_url = photo_url

            profile.save()
            #profile_form.save()
            return redirect(reverse('minha-conta'))
    else:
        user_form = UserUpdateForm(instance=user)
        profile_form = ProfileForm(instance=profile)

    return render(request, 'profile/minha_conta.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })