from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from django.template.loader import render_to_string
from .models import UsuarioUJAP


# ─── Login ────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        user_data = request.POST.get('usuario', '').strip()
        pass_data = request.POST.get('password', '').strip()

        try:
            usuario = UsuarioUJAP.objects.get(cedula=user_data, password=pass_data)
            request.session['usuario_id'] = usuario.id
            request.session['usuario_cedula'] = usuario.cedula
            return redirect('dashboard')   # cambia 'dashboard' por tu vista principal
        except UsuarioUJAP.DoesNotExist:
            messages.error(request, 'Cédula o contraseña incorrectos.')

    return render(request, 'web_ujap/login.html')


# ─── Crear usuario ─────────────────────────────────────────────────────────────
def usuario_view(request):
    if request.method == 'POST':
        cedula  = request.POST.get('cedula', '').strip()
        correo  = request.POST.get('email', '').strip()
        facu    = request.POST.get('facultad', '').strip()
        pass1   = request.POST.get('password', '').strip()
        pass2   = request.POST.get('confirm_password', '').strip()

        if not all([cedula, correo, facu, pass1]):
            messages.error(request, 'Todos los campos son obligatorios.')
            return render(request, 'web_ujap/crear_usuario.html',
                          {'cedula_viva': cedula, 'correo_vivo': correo})

        if pass1 != pass2:
            messages.error(request, 'Las contraseñas no coinciden.')
            return render(request, 'web_ujap/crear_usuario.html',
                          {'cedula_viva': cedula, 'correo_vivo': correo})

        if UsuarioUJAP.objects.filter(cedula=cedula).exists():
            messages.error(request, 'Ya existe un usuario con esa cédula.')
            return render(request, 'web_ujap/crear_usuario.html',
                          {'cedula_viva': cedula, 'correo_vivo': correo})

        UsuarioUJAP.objects.create(
            cedula=cedula,
            correo=correo,
            facultad=facu,
            password=pass1,
        )
        messages.success(request, '¡Cuenta creada con éxito!')
        return redirect('login')

    return render(request, 'web_ujap/crear_usuario.html')


# ─── Recuperar contraseña – Paso 1: pedir email ───────────────────────────────
def recuperar_view(request):
    if request.method == 'POST':
        correo = request.POST.get('email', '').strip().lower()
        usuario = UsuarioUJAP.objects.filter(correo__iexact=correo).first()

        if usuario:
            # Generamos un token firmado que expira en 1 hora
            token = signing.dumps({'id': usuario.id}, salt='recuperar-password')
            reset_url = request.build_absolute_uri(
                f'/recuperar/confirmar/{token}/'
            )
            email_html = render_to_string('web_ujap/emails/recuperar_email.html', {
                'usuario': usuario,
                'reset_url': reset_url,
                'site_name': 'UJAP.online',
            })
            send_mail(
                subject='Recuperación de contraseña - UJAP.online',
                message=f'Enlace: {reset_url}',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.correo],
                html_message=email_html,
                fail_silently=False,
            )

        # Mismo mensaje siempre (seguridad: no revelar si el correo existe)
        messages.success(request,
            'Si ese correo está registrado, recibirás las instrucciones en breve.')
        return redirect('recuperar_enviado')

    return render(request, 'web_ujap/recuperar.html')


# ─── Recuperar – Paso 2: aviso "revisá tu correo" ─────────────────────────────
def recuperar_enviado_view(request):
    return render(request, 'web_ujap/recuperar_enviado.html')


# ─── Recuperar – Paso 3: nueva contraseña (desde link del email) ──────────────
def recuperar_confirmar_view(request, token):
    try:
        # El token expira en 3600 segundos (1 hora)
        data = signing.loads(token, salt='recuperar-password', max_age=3600)
        usuario = UsuarioUJAP.objects.get(id=data['id'])
    except (signing.SignatureExpired, signing.BadSignature, UsuarioUJAP.DoesNotExist):
        return render(request, 'web_ujap/recuperar_invalido.html')

    if request.method == 'POST':
        pass1 = request.POST.get('password', '').strip()
        pass2 = request.POST.get('confirm_password', '').strip()

        if not pass1:
            messages.error(request, 'La contraseña no puede estar vacía.')
        elif len(pass1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        elif pass1 != pass2:
            messages.error(request, 'Las contraseñas no coinciden.')
        else:
            usuario.password = pass1
            usuario.save()
            messages.success(request, '¡Contraseña actualizada correctamente!')
            return redirect('login')

    return render(request, 'web_ujap/recuperar_confirmar.html', {'token': token})


# ─── Otras vistas ─────────────────────────────────────────────────────────────
def contacto_view(request):
    return render(request, 'web_ujap/contacto.html')

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import JsonResponse
from .models import Estudiante, Materia, Horario, Asistencia


#@login_required
def dashboard_index(request):
    """Vista principal del dashboard con estadísticas generales"""
    
    # Fecha actual y rangos
    hoy = timezone.now().date()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    fin_semana = inicio_semana + timedelta(days=6)
    inicio_mes = hoy.replace(day=1)
    
    # KPIs Principales
    total_estudiantes = Estudiante.objects.filter(activo=True).count()
    total_materias = Materia.objects.filter(activa=True).count()
    
    # Asistencias de hoy
    asistencias_hoy = Asistencia.objects.filter(fecha=hoy)
    total_asistencias_hoy = asistencias_hoy.count()
    presentes_hoy = asistencias_hoy.filter(estado='presente').count()
    ausentes_hoy = asistencias_hoy.filter(estado='ausente').count()
    tardes_hoy = asistencias_hoy.filter(estado='tarde').count()
    
    # Porcentaje de asistencia hoy
    porcentaje_asistencia_hoy = 0
    if total_asistencias_hoy > 0:
        porcentaje_asistencia_hoy = round((presentes_hoy / total_asistencias_hoy) * 100, 2)
    
    # Asistencias del mes
    asistencias_mes = Asistencia.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy)
    total_asistencias_mes = asistencias_mes.count()
    ausencias_mes = asistencias_mes.filter(estado='ausente').count()
    
    # Estudiantes con más faltas (top 5)
    estudiantes_faltas = Estudiante.objects.filter(activo=True).annotate(
        total_faltas=Count('asistencias', filter=Q(asistencias__estado='ausente'))
    ).order_by('-total_faltas')[:5]
    
    # Estudiantes con mejor asistencia (top 5)
    estudiantes_mejor_asistencia = []
    for estudiante in Estudiante.objects.filter(activo=True):
        porcentaje = estudiante.calcular_porcentaje_asistencia()
        if porcentaje > 0:
            estudiantes_mejor_asistencia.append({
                'estudiante': estudiante,
                'porcentaje': porcentaje
            })
    estudiantes_mejor_asistencia = sorted(
        estudiantes_mejor_asistencia, 
        key=lambda x: x['porcentaje'], 
        reverse=True
    )[:5]
    
    # Materias con más ausencias
    materias_ausencias = Materia.objects.filter(activa=True).annotate(
        total_ausencias=Count('asistencias', filter=Q(asistencias__estado='ausente'))
    ).order_by('-total_ausencias')[:5]
    
    # Horarios de hoy
    dia_hoy = hoy.strftime('%A').lower()
    dias_español = {
        'monday': 'lunes',
        'tuesday': 'martes',
        'wednesday': 'miercoles',
        'thursday': 'jueves',
        'friday': 'viernes',
        'saturday': 'sabado',
        'sunday': 'domingo'
    }
    dia_hoy_español = dias_español.get(dia_hoy, 'lunes')
    horarios_hoy = Horario.objects.filter(dia_semana=dia_hoy_español).order_by('hora_inicio')
    
    context = {
        # KPIs
        'total_estudiantes': total_estudiantes,
        'total_materias': total_materias,
        'presentes_hoy': presentes_hoy,
        'ausentes_hoy': ausentes_hoy,
        'tardes_hoy': tardes_hoy,
        'porcentaje_asistencia_hoy': porcentaje_asistencia_hoy,
        'ausencias_mes': ausencias_mes,
        
        # Listas
        'estudiantes_faltas': estudiantes_faltas,
        'estudiantes_mejor_asistencia': estudiantes_mejor_asistencia,
        'materias_ausencias': materias_ausencias,
        'horarios_hoy': horarios_hoy,
        
        # Fechas
        'hoy': hoy,
        'dia_hoy': dia_hoy_español,
    }
    
    return render(request, 'dashboard/index.html', context)


#@login_required
def estadisticas_json(request):
    """API endpoint para datos de gráficos en JSON"""
    
    tipo = request.GET.get('tipo', 'asistencias_semana')
    
    if tipo == 'asistencias_semana':
        # Asistencias de los últimos 7 días
        hoy = timezone.now().date()
        datos = []
        labels = []
        
        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            asistencias = Asistencia.objects.filter(fecha=fecha)
            
            presentes = asistencias.filter(estado='presente').count()
            ausentes = asistencias.filter(estado='ausente').count()
            tardes = asistencias.filter(estado='tarde').count()
            
            labels.append(fecha.strftime('%d/%m'))
            
            if i == 6:
                datos = {
                    'presentes': [presentes],
                    'ausentes': [ausentes],
                    'tardes': [tardes]
                }
            else:
                datos['presentes'].append(presentes)
                datos['ausentes'].append(ausentes)
                datos['tardes'].append(tardes)
        
        return JsonResponse({
            'labels': labels,
            'datasets': [
                {
                    'label': 'Presentes',
                    'data': datos['presentes'],
                    'backgroundColor': 'rgba(75, 192, 192, 0.6)',
                    'borderColor': 'rgba(75, 192, 192, 1)',
                    'borderWidth': 2
                },
                {
                    'label': 'Ausentes',
                    'data': datos['ausentes'],
                    'backgroundColor': 'rgba(255, 99, 132, 0.6)',
                    'borderColor': 'rgba(255, 99, 132, 1)',
                    'borderWidth': 2
                },
                {
                    'label': 'Tardanzas',
                    'data': datos['tardes'],
                    'backgroundColor': 'rgba(255, 206, 86, 0.6)',
                    'borderColor': 'rgba(255, 206, 86, 1)',
                    'borderWidth': 2
                }
            ]
        })
    
    elif tipo == 'estados_hoy':
        # Distribución de estados hoy
        hoy = timezone.now().date()
        asistencias = Asistencia.objects.filter(fecha=hoy)
        
        presentes = asistencias.filter(estado='presente').count()
        ausentes = asistencias.filter(estado='ausente').count()
        tardes = asistencias.filter(estado='tarde').count()
        justificados = asistencias.filter(estado='justificado').count()
        
        return JsonResponse({
            'labels': ['Presentes', 'Ausentes', 'Tardanzas', 'Justificados'],
            'datasets': [{
                'data': [presentes, ausentes, tardes, justificados],
                'backgroundColor': [
                    'rgba(75, 192, 192, 0.8)',
                    'rgba(255, 99, 132, 0.8)',
                    'rgba(255, 206, 86, 0.8)',
                    'rgba(54, 162, 235, 0.8)'
                ],
                'borderWidth': 2
            }]
        })
    
    elif tipo == 'asistencias_por_materia':
        # Top 5 materias por asistencias
        materias = Materia.objects.filter(activa=True).annotate(
            total_asistencias=Count('asistencias')
        ).order_by('-total_asistencias')[:5]
        
        labels = [m.nombre for m in materias]
        datos = [m.total_asistencias for m in materias]
        
        return JsonResponse({
            'labels': labels,
            'datasets': [{
                'label': 'Total Asistencias',
                'data': datos,
                'backgroundColor': 'rgba(153, 102, 255, 0.6)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 2
            }]
        })
    
    return JsonResponse({'error': 'Tipo no válido'}, status=400)


#@login_required
def reporte_estudiante(request, estudiante_id):
    """Vista de reporte individual de estudiante"""
    
    estudiante = Estudiante.objects.get(id=estudiante_id)
    asistencias = estudiante.asistencias.all().order_by('-fecha')
    
    # Estadísticas del estudiante
    total_asistencias = asistencias.count()
    presentes = asistencias.filter(estado='presente').count()
    ausentes = asistencias.filter(estado='ausente').count()
    tardes = asistencias.filter(estado='tarde').count()
    justificados = asistencias.filter(estado='justificado').count()
    
    porcentaje = estudiante.calcular_porcentaje_asistencia()
    
    context = {
        'estudiante': estudiante,
        'asistencias': asistencias[:20],  # Últimas 20
        'total_asistencias': total_asistencias,
        'presentes': presentes,
        'ausentes': ausentes,
        'tardes': tardes,
        'justificados': justificados,
        'porcentaje': porcentaje
    }
    
    return render(request, 'dashboard/reporte_estudiante.html', context)