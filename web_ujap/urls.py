from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_index, name='index'),
    
    # API endpoints para gráficos
    path('api/estadisticas/', views.estadisticas_json, name='estadisticas_json'),
    
    # Reportes
    path('estudiante/<int:estudiante_id>/', views.reporte_estudiante, name='reporte_estudiante'),
]