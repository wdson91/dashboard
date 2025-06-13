from rest_framework import serializers
from .models import Fatura, ItemFatura

class ItemFaturaSerializer(serializers.ModelSerializer):
    class Meta:
        model = ItemFatura
        fields = ['nome', 'quantidade', 'preco_unitario', 'total']

class FaturaSerializer(serializers.ModelSerializer):
    itens = ItemFaturaSerializer(many=True)
    
    class Meta:
        model = Fatura
        fields = ['id', 'numero_fatura', 'data', 'hora', 'total', 'itens', 'criado_em']

class UploadFaturaSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if not value.name.endswith('.txt'):
            raise serializers.ValidationError("Apenas arquivos .txt são aceitos")
        if value.size > 2 * 1024 * 1024:  # 2MB
            raise serializers.ValidationError("Arquivo muito grande. Máximo permitido: 2MB")
        return value