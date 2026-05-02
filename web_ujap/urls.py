from django.urls import path
from . import views

app_name = 'dashboard'

app_name = 'dashboard'

urlpatterns = [
    # Dashboard
    path('', views.dashboard_index, name='index'),
    path('api/estadisticas/', views.estadisticas_json, name='estadisticas_json'),
    path('estudiante/<int:estudiante_id>/', views.reporte_estudiante, name='reporte_estudiante'),

    # QR - Profesor
    path('sesion/iniciar/', views.iniciar_sesion_view, name='iniciar_sesion'),
    path('sesion/<uuid:token>/', views.panel_sesion_view, name='panel_sesion'),
    path('sesion/<uuid:token>/marcar/', views.marcar_manual_view, name='marcar_manual'),
    path('sesion/<uuid:token>/cerrar/', views.cerrar_sesion_view, name='cerrar_sesion'),
    path('sesion/<uuid:token>/estado/', views.estado_sesion_json, name='estado_sesion'),
    path('sesion/<uuid:token>/buscar/', views.buscar_estudiante_json, name='buscar_estudiante'),
]