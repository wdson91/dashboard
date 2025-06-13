from django.contrib import admin
from .models import Fatura, ItemFatura

class ItemFaturaInline(admin.TabularInline):
    model = ItemFatura
    extra = 0

@admin.register(Fatura)
class FaturaAdmin(admin.ModelAdmin):
    list_display = ('numero_fatura', 'usuario', 'data', 'total')
    list_filter = ('usuario', 'data')
    search_fields = ('numero_fatura', 'texto_original')
    inlines = [ItemFaturaInline]

@admin.register(ItemFatura)
class ItemFaturaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'quantidade', 'preco_unitario', 'total', 'fatura')
    list_filter = ('fatura',)
    search_fields = ('nome',)