"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path,include
from web_ujap.views import (
    home_view,
    login_view,
    contacto_view,
    recuperar_view,
    recuperar_enviado_view,
    recuperar_confirmar_view,
    usuario_view,
    pagina_view,
    logout_view,
    escanear_qr_view,   
) 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('login/', login_view, name='login'),
    path('contacto/', contacto_view, name='contacto'),
    path('recuperar/', recuperar_view, name='recuperar'),
    path('recuperar/enviado/', recuperar_enviado_view, name='recuperar_enviado'),
    path('recuperar/confirmar/<str:token>/', recuperar_confirmar_view, name='recuperar_confirmar'),
    path('usuario/', usuario_view, name='usuario'),
    path('dashboard/', include('web_ujap.urls')),  # Dashboard
    path('pagina/', pagina_view, name='pagina'),
    path('salir/', logout_view, name='logout'),
    path('asistencia/escanear/<uuid:token>/', escanear_qr_view, name='escanear_qr'),




]

