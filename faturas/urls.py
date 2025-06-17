from django.urls import path
from .views import (
    FaturaListCreateView,
    UploadFaturaView,
    FaturaPDFView,
    StatsView,
    index,
    faturas,
    StatsHojeView
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
    path('api/stats/today', StatsHojeView.as_view(), name='stats'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
