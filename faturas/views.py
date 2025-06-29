from django.shortcuts import render
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from fpdf import FPDF
from calendar import month_name

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
from django.core.cache import cache
from django.utils import timezone
from rest_framework.permissions import AllowAny
from pytz import timezone as pytz_timezone
import requests

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

        #chamada para atualizar o cache do n8n

        n8n_url = 'https://novoprojeto-n8n.aidvjr.easypanel.host/webhook/reset-cache'
        
        try:        
            response = requests.get(n8n_url)
            if response.status_code != 200:
                erros.append({'erro': 'Falha ao atualizar o cache no n8n'})
        except requests.RequestException as e:
            erros.append({'erro': f'Erro ao conectar com o n8n: {str(e)}'})

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
   

    
    permission_classes = [AllowAny]  # <-- adiciona isso

    def get(self, request, *args, **kwargs):
        data_inicio = request.query_params.get("data_inicio")
        data_fim = request.query_params.get("data_fim")
        print(request)
        return
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

        faturas = Fatura.objects.filter()

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

        contagem_produtos = defaultdict(int)
        for fatura in faturas:
            for item in fatura.itens.all():
                contagem_produtos[item.nome] += item.quantidade

        # Transformar em lista de dicionários
        produtos = sorted(
    [{"produto": nome, "quantidade": qtd} for nome, qtd in contagem_produtos.items()],
    key=lambda x: x["quantidade"],
    reverse=True
)


        
            # Agrupar vendas por dia
        vendas_por_dia = defaultdict(float)
        for fatura in faturas:
            vendas_por_dia[str(fatura.data)] += float(fatura.total)

        # Transformar em lista de dicionários e ordenar por data
        vendas = sorted(
            [{"data": data, "total": total} for data, total in vendas_por_dia.items()],
            key=lambda x: x["data"]
)
        

         # Agrupar vendas por hora (baseado em campo 'hora')
        vendas_por_hora = defaultdict(float)
        for fatura in faturas:
            hora_formatada = fatura.hora.strftime("%H:00")  # ex: '14:00'
            vendas_por_hora[hora_formatada] += float(fatura.total)

        vendas_horarias = sorted(
            [{"hora": hora, "total": total} for hora, total in vendas_por_hora.items()],
            key=lambda x: x["hora"]
        )


        return Response({
            "total_vendas": round(total_vendas, 2),
            "total_itens": total_itens,
            "vendas_por_dia": vendas,
            "vendas_por_hora": vendas_horarias,
            "vendas_por_produto": produtos,
            "quantidade_faturas": faturas.count(),
            "filtro_data_inicio": data_inicio,
            "filtro_data_fim": data_fim,
        })

       
class StatsHojeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        hoje = date.today()

        #cache_key = f"stats_hoje_{hoje}"
        #cache_ttl = 120  # 2 minutos

        # Verifica se tem cache
        #dados_cache = cache.get(cache_key)
        #if dados_cache:
            #return Response(dados_cache)

        # Recalcula
        faturas = Fatura.objects.filter(data=hoje)

        total_vendas = sum(f.total for f in faturas)
        total_itens = sum(
            item.quantidade
            for f in faturas
            for item in f.itens.all()
        )

        contagem_produtos = defaultdict(int)
        for f in faturas:
            for item in f.itens.all():
                contagem_produtos[item.nome] += item.quantidade

        produtos = sorted(
            [{"produto": nome, "quantidade": qtd} for nome, qtd in contagem_produtos.items()],
            key=lambda x: x["quantidade"],
            reverse=True
        )

        vendas_por_hora_real = defaultdict(float)
        for f in faturas:
            hora_formatada = f.hora.strftime("%H:00")
            vendas_por_hora_real[hora_formatada] += float(f.total)

        horas_resultado = {"08:00", "12:00", "18:00"} | set(vendas_por_hora_real.keys())
        vendas_horarias = [
            {"hora": hora, "total": round(vendas_por_hora_real.get(hora, 0.0), 2)}
            for hora in sorted(horas_resultado)
        ]


        # Atualiza a última atualização 
        # para o momento atual com timezone lisboa 

        agora = timezone.now().astimezone(pytz_timezone("Europe/Lisbon"))        
        print(f"Atualizando estatísticas para hoje: {hoje} às {agora.strftime('%H:%M')}")
        faturas.update(ultima_atualizacao=agora)

         # Faturas dos últimos 7 dias até ontem
        ontem = hoje - timedelta(days=1)
        sete_dias_atras = hoje - timedelta(days=7)
        faturas_7_dias = Fatura.objects.filter(data__range=(sete_dias_atras, ontem))

        vendas_ultimos_7_dias = defaultdict(float)
        for f in faturas_7_dias:
            vendas_ultimos_7_dias[f.data.strftime("%Y-%m-%d")] += float(f.total)

        vendas_por_dia_ultimos_7 = [
            {"data": data, "total": round(total, 2)}
            for data, total in sorted(vendas_ultimos_7_dias.items())
        ]
        total_ultimos_7_dias = round(sum(f.total for f in faturas_7_dias), 2)
       
        resultado = {
            "dados": {
                "total_vendas": round(total_vendas, 2),
                "total_itens": total_itens,
                "vendas_por_dia": [{"data": str(hoje), "total": round(total_vendas, 2)}],
                "vendas_por_hora": vendas_horarias,
                "vendas_por_produto": produtos,
                "quantidade_faturas": faturas.count(),
                "filtro_data": str(hoje),
                "ultima_atualizacao": agora.strftime("%H:%M"),
                "ultimos_7_dias": vendas_por_dia_ultimos_7,
                "total_ultimos_7_dias": total_ultimos_7_dias,
            }
        }


        # Armazena no cache por 2 minutos
        #cache.set(cache_key, resultado, timeout=cache_ttl)

        return Response(resultado)
@login_required
def index(request):
    return render(request, 'faturas/index.html')

@login_required
def faturas(request):

    
    return render(request, "faturas/faturas.html")



from django.db.models import Sum, Count, F, ExpressionWrapper, DecimalField, Value as V
from django.db.models.functions import TruncHour, Coalesce
from django.utils import timezone
from datetime import timedelta, time
from django.http import JsonResponse
from .models import Fatura, ItemFatura



from django.db.models import Count

def faturas_agrupadas_view(request):
    hoje = timezone.localdate()
    agora = timezone.now().astimezone(timezone.get_current_timezone())
    sete_dias_atras = hoje - timedelta(days=7)

    # Faturas de hoje e últimos 7 dias (excluindo hoje)
    faturas_hoje = Fatura.objects.filter(data=hoje)
    faturas_7_dias = Fatura.objects.filter(data__range=[sete_dias_atras, hoje - timedelta(days=1)])

    # Contagens gerais
    quantidade_faturas = faturas_hoje.count()
    quantidade_faturas_7_dias = faturas_7_dias.count()

    total_vendas = faturas_hoje.aggregate(
        total=Coalesce(Sum('total'), V(0, output_field=DecimalField()))
    )['total']

    # Agrupamento por hora - Hoje
    faturas_hoje_por_hora = (
        faturas_hoje
        .annotate(hora_truncada=TruncHour('hora'))
        .values('hora_truncada')
        .annotate(
            total=Coalesce(Sum('total'), V(0, output_field=DecimalField())),
            quantidade=Count('id')
        )
    )
    totais_hoje = {
        fh['hora_truncada'].strftime("%H:%M"): {
            "volume": float(fh['total']),
            "quantidade": fh['quantidade']
        } for fh in faturas_hoje_por_hora
    }

    # Agrupamento por hora - Últimos 7 dias
    faturas_7dias_por_hora = (
        faturas_7_dias
        .annotate(hora_truncada=TruncHour('hora'))
        .values('hora_truncada')
        .annotate(
            total=Coalesce(Sum('total'), V(0, output_field=DecimalField())),
            quantidade=Count('id')
        )
    )
    totais_7_dias = {
        fh['hora_truncada'].strftime("%H:%M"): {
            "volume": float(fh['total']),
            "quantidade": fh['quantidade']
        } for fh in faturas_7dias_por_hora
    }

    # Lista fixa de horas (08:00 às 18:00)
    # Conjunto de horas únicas com dados de hoje e dos últimos 7 dias
    horas_com_dados = set(totais_hoje.keys()) | set(totais_7_dias.keys())

    # Construção final apenas com horas que têm dados
    vendas_por_hora_formatado = []
    for hora in sorted(horas_com_dados):
        vendas_por_hora_formatado.append({
            "hora": hora,
            "faturas_hoje": totais_hoje.get(hora, {}).get("quantidade", 0),
            "volume_hoje": round(totais_hoje.get(hora, {}).get("volume", 0), 2),
            "faturas_7_dias": totais_7_dias.get(hora, {}).get("quantidade", 0),
            "volume_7_dias": round(totais_7_dias.get(hora, {}).get("volume", 0), 2)
        })


    # Vendas por dia (hoje)
    vendas_por_dia = [{
        "data": hoje.strftime("%Y-%m-%d"),
        "total": round(float(total_vendas), 2)
    }]

    # Vendas últimos 7 dias
    vendas_7_dias = (
        faturas_7_dias
        .values('data')
        .annotate(total=Coalesce(Sum('total'), V(0, output_field=DecimalField())))
        .order_by('data')
    )
    ultimos_7_dias = [{
        "data": v["data"].strftime("%Y-%m-%d"),
        "total": round(float(v["total"]), 2)
    } for v in vendas_7_dias]

    total_ultimos_7_dias = round(sum(v["total"] for v in ultimos_7_dias), 2)

    # Hora da última atualização
    ultima_atualizacao = agora.strftime("%H:%M")

    response = [{
        "dados": {
            "total_vendas": round(float(total_vendas), 2),
            "quantidade_faturas": quantidade_faturas,
            "vendas_por_dia": vendas_por_dia,
            "vendas_por_hora": vendas_por_hora_formatado,
            "filtro_data": hoje.strftime("%Y-%m-%d"),
            "ultima_atualizacao": ultima_atualizacao,
            "ultimos_7_dias": ultimos_7_dias,
            "total_ultimos_7_dias": total_ultimos_7_dias,
            "quantidade_faturas_7_dias": quantidade_faturas_7_dias,
        }
    }]

    return JsonResponse(response, safe=False)




from django.db.models.functions import TruncMonth
from datetime import datetime
from collections import defaultdict
import locale


MESES_PT = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

def faturas_por_mes_view(request):
    hoje = timezone.localdate()
    agora = timezone.now().astimezone(timezone.get_current_timezone())
    ano_atual = hoje.year
    ano_passado = ano_atual - 1

    faturas_dois_anos = Fatura.objects.filter(data__year__in=[ano_atual, ano_passado])

    faturas_por_mes = (
        faturas_dois_anos
        .annotate(mes=TruncMonth('data'))
        .values('mes')
        .annotate(
            total=Coalesce(Sum('total'), V(0, output_field=DecimalField())),
            quantidade=Count('id')
        )
    )

    totais_por_ano = defaultdict(lambda: defaultdict(float))
    faturas_por_mes_ano_atual = defaultdict(int)

    for item in faturas_por_mes:
        data_mes = item['mes']
        mes_num = data_mes.month
        mes_nome = MESES_PT[mes_num]
        ano = data_mes.year
        total = float(item['total'])

        totais_por_ano[ano][mes_nome] += total
        if ano == ano_atual:
            faturas_por_mes_ano_atual[mes_nome] += item['quantidade']

    vendas_por_mes_formatado = []
    for mes_num in range(1, 13):
        mes_nome = MESES_PT[mes_num]
        vendas_por_mes_formatado.append({
            "mes":mes_nome,
            f"total_ano_atual": round(totais_por_ano[ano_atual].get(mes_nome, 0), 2),
            f"total_ano_passado": round(totais_por_ano[ano_passado].get(mes_nome, 0), 2),
            f"faturas_ano_atual": faturas_por_mes_ano_atual.get(mes_nome, 0)
        })

    response = [{
        "dados": {
            "vendas_por_mes": vendas_por_mes_formatado,
            "filtro_ano": ano_atual,
            "ultima_atualizacao": agora.strftime("%H:%M"),
        }
    }]

    return JsonResponse(response, safe=False)