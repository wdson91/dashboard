from django.urls import path
from .views import (
    FaturaListCreateView,
    UploadFaturaView,
    FaturaPDFView,
    StatsView,
    index,
    faturas
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', index, name='index'),
    path('api/faturas/', FaturaListCreateView.as_view(), name='faturas-list'),
    path('api/upload/', UploadFaturaView.as_view(), name='upload-fatura'),
    path('api/faturas/<slug:numero>/pdf/', FaturaPDFView.as_view(), name='fatura-pdf'),
    path('api/stats/', StatsView.as_view(), name='stats'),
    path("faturas",faturas,name="faturas" )
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
