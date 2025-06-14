from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from fpdf import FPDF
from django.utils.dateparse import parse_date
from io import BytesIO
from django.http import FileResponse
from .models import Fatura
from .serializers import FaturaSerializer, UploadFaturaSerializer
from .utils.parse_faturas import parse_faturas
from collections import defaultdict
from datetime import date, timedelta
from django.views.decorators.csrf import csrf_exempt
import qrcode
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import ProfileForm
from io import BytesIO
from PIL import Image
import tempfile


class FaturaListCreateView(generics.ListCreateAPIView):
    serializer_class = FaturaSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Fatura.objects.filter(usuario=user).order_by('-data', '-hora')

        # Pega o NIF opcional da query string
        nif = self.request.query_params.get('nif')
        if nif:
            queryset = queryset.filter(cliente__nif=nif)  # ajusta o campo conforme seu modelo

        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(usuario=self.request.user)

class UploadFaturaView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = UploadFaturaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        file = request.FILES['file']
        try:
            text = file.read().decode('utf-8')
        except UnicodeDecodeError:
            return Response({'erro': 'Arquivo com codificação inválida. Use UTF-8'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            lista_faturas = parse_faturas(text)
        except Exception as e:
            return Response({'erro': f'Erro ao processar as faturas: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        faturas_criadas = []
        erros = []
        
        for dados in lista_faturas:
            campos_obrigatorios = ['numero_fatura', 'data', 'hora', 'itens', 'total', 'qrcode', 'texto_completo']
            # Verifica se todos os campos obrigatórios estão presentes
            
            faltando = [campo for campo in campos_obrigatorios if campo not in dados or dados[campo] in [None, '', []]]
            if faltando:
                erros.append({
                    'numero_fatura': dados.get('numero_fatura', 'desconhecido'),
                    'erro': f'Campos faltando: {faltando}'
                })
                continue

            numero_fatura_limpo = dados['numero_fatura'].replace("/", "_").replace(" ", "")

            if Fatura.objects.filter(numero_fatura=numero_fatura_limpo).exists():
                erros.append({'numero_fatura': dados['numero_fatura'], 'erro': 'Fatura já existe'})
                continue

            fatura = Fatura.objects.create(
                usuario=request.user,
                numero_fatura=numero_fatura_limpo,
                data=dados['data'],
                hora=dados['hora'],
                total=dados['total'],
                texto_original=dados['texto_original'],
                texto_completo=dados['texto_completo'],
                qrcode=dados['qrcode']
            )

            for item in dados['itens']:
                fatura.itens.create(
                    nome=item['nome'],
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco_unitario'],
                    total=item['total']
                )

            faturas_criadas.append(fatura)

        serializer = FaturaSerializer(faturas_criadas, many=True)
        return Response({
            'mensagem': f'{len(faturas_criadas)} fatura(s) salva(s) com sucesso',
            'faturas': serializer.data,
            'erros': erros
        }, status=status.HTTP_201_CREATED if faturas_criadas else status.HTTP_400_BAD_REQUEST)



class FaturaPDFView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, numero, *args, **kwargs):
        try:
            fatura = Fatura.objects.get(numero_fatura=numero, usuario=request.user)
        except Fatura.DoesNotExist:
            return Response(
                {"erro": "Fatura não encontrada"},
                status=status.HTTP_404_NOT_FOUND
            )
        largura_papel = 80

        pdf = FPDF(unit='mm', format=(largura_papel, 297))  # altura padrão A4, ou ajuste conforme precisar
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=5)  # margens menores para papel pequeno
        pdf.set_font("Courier", size=10)


      
        for linha in fatura.texto_completo.splitlines():
            if '[[QR_CODE]]' in linha:
                pdf.ln(2)
                if fatura.qrcode:
                    qr = qrcode.make(fatura.qrcode)
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp_img:
                        qr.save(tmp_img.name)
                        tmp_img.flush()
                        # Centraliza o QR code no papel de 80mm
                        largura_qrcode = 40  # pode ajustar para maior ou menor
                        pos_x = (largura_papel - largura_qrcode) / 2
                        pdf.image(tmp_img.name, x=pos_x, w=largura_qrcode)
                pdf.ln(5)
            else:
                # Texto centralizado na largura do papel 80mm
                pdf.cell(0, 5, txt=linha.strip(), ln=True, align='C')


        pdf_output = pdf.output(dest='S')
        buffer = BytesIO(pdf_output)
        buffer.seek(0)

        return FileResponse(
            buffer,
            as_attachment=True,
            filename=f"{fatura.numero_fatura}.pdf",
            content_type="application/pdf"
        )

       

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            return redirect('edit_profile')
    else:
        form = ProfileForm(instance=request.user.profile)

    return render(request, 'profile/edit_profile.html', {'form': form})

class StatsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        data_inicio = request.query_params.get("data_inicio")
        data_fim = request.query_params.get("data_fim")

        # Se não vier filtro, usa o mês atual
        if not data_inicio or not data_fim:
            hoje = date.today()
            primeiro_dia = hoje.replace(day=1)
            # Próximo mês menos um dia = último dia do mês atual
            if hoje.month == 12:
                proximo_mes = hoje.replace(year=hoje.year + 1, month=1, day=1)
            else:
                proximo_mes = hoje.replace(month=hoje.month + 1, day=1)
            ultimo_dia = proximo_mes - timedelta(days=1)
            if not data_inicio:
                data_inicio = primeiro_dia.isoformat()
            if not data_fim:
                data_fim = ultimo_dia.isoformat()

        faturas = Fatura.objects.filter(usuario=request.user)

        if isinstance(data_inicio, str) and data_inicio:
            data_inicio_parsed = parse_date(data_inicio)
            if data_inicio_parsed:
                faturas = faturas.filter(data__gte=data_inicio_parsed)

        if isinstance(data_fim, str) and data_fim:
            data_fim_parsed = parse_date(data_fim)
            if data_fim_parsed:
                faturas = faturas.filter(data__lte=data_fim_parsed)
        
        total_vendas = sum(fatura.total for fatura in faturas)
        total_itens = sum(
            item.quantidade 
            for fatura in faturas 
            for item in fatura.itens.all()
        )

        produtos = {}
        for fatura in faturas:
            for item in fatura.itens.all():
                produtos[item.nome] = produtos.get(item.nome, 0) + item.quantidade
        
        # Agrupar vendas por dia
        vendas_por_dia = defaultdict(float)
        for fatura in faturas:
            vendas_por_dia[str(fatura.data)] += float(fatura.total)

        # Ordenar por data
        vendas_por_dia = dict(sorted(vendas_por_dia.items()))

        return Response({
            "total_vendas": round(total_vendas, 2),
            "total_itens": total_itens,
            "vendas_por_dia": vendas_por_dia,
            "vendas_por_produto": produtos,
            "quantidade_faturas": faturas.count(),
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        })

         # Só tenta fazer o parse se for string válida
        if isinstance(data_inicio, str) and data_inicio:
            data_inicio_parsed = parse_date(data_inicio)
            if data_inicio_parsed:
                faturas = faturas.filter(data__gte=data_inicio_parsed)

        if isinstance(data_fim, str) and data_fim:
            data_fim_parsed = parse_date(data_fim)
            if data_fim_parsed:
                faturas = faturas.filter(data__lte=data_fim_parsed)

        total_vendas = sum(fatura.total for fatura in faturas)
        total_itens = sum(
            item.quantidade 
            for fatura in faturas 
            for item in fatura.itens.all()
        )

        produtos = {}
        for fatura in faturas:
            for item in fatura.itens.all():
                produtos[item.nome] = produtos.get(item.nome, 0) + item.quantidade
        
        # Agrupar vendas por dia
        vendas_por_dia = defaultdict(float)
        for fatura in faturas:
            vendas_por_dia[str(fatura.data)] += float(fatura.total)

        # Ordenar por data
        vendas_por_dia = dict(sorted(vendas_por_dia.items()))

        return Response({
            "total_vendas": round(total_vendas, 2),
            "total_itens": total_itens,
            "vendas_por_dia": vendas_por_dia,
            "vendas_por_produto": produtos,
            "quantidade_faturas": faturas.count(),
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        })

@login_required
def index(request):
    return render(request, 'faturas/index.html')

@login_required
def faturas(request):

    
    return render(request, "faturas/faturas.html")

