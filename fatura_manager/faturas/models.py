from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator

class Fatura(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    numero_fatura = models.CharField(max_length=50, unique=True)
    data = models.DateField()
    hora = models.TimeField()
    total = models.DecimalField(max_digits=10, decimal_places=2)
    texto_original = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-hora']

    def __str__(self):
        return f"{self.numero_fatura} - {self.data}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)  # liga ao usuário
    photo = models.ImageField(upload_to='profile_photos/', default='default.jpg')  # campo da foto

    def __str__(self):
        return self.user.username

class ItemFatura(models.Model):
    
    fatura = models.ForeignKey(Fatura, related_name='itens', on_delete=models.CASCADE)
    nome = models.CharField(max_length=200)
    quantidade = models.PositiveIntegerField(validators=[MaxValueValidator(999)])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nome} - {self.quantidade}x"