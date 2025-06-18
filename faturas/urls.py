from django.urls import path
from .views import (
    FaturaListCreateView,
    UploadFaturaView,
    FaturaPDFView,
    StatsView,
    index,
    faturas,
    StatsHojeView,
    faturas_agrupadas_view,
    faturas_por_mes_view
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('api/faturas/', FaturaListCreateView.as_view(), name='faturas-list'),
    path('api/upload/', UploadFaturaView.as_view(), name='upload-fatura'),
    path('api/faturas/<slug:numero>/pdf/', FaturaPDFView.as_view(), name='fatura-pdf'),
    path('api/stats/', StatsView.as_view(), name='stats'),
    path("faturas",faturas,name="faturas" ),
    path('api/stats/today', StatsHojeView.as_view(), name='stats-hoje'),
    path('api/stats/report', faturas_agrupadas_view, name='stats-report'),
    path('api/stats/month', faturas_por_mes_view, name='stats-month'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
