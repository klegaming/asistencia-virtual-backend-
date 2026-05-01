from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core import signing
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.http import JsonResponse
from .models import Usuario, Estudiante, Materia, Horario, Asistencia


# ─── Home ─────────────────────────────────────────────────────────────────────
def home_view(request):
    return render(request, 'web_ujap/home.html')


# ─── Login ────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('usuario')
        password = request.POST.get('password')
        
        print(f"Intentando login: {username} / {password}")  # ← agrega esto
        
        user = authenticate(request, username=username, password=password)
        
        print(f"Usuario autenticado: {user}")  # ← y esto
        
        if user is not None:
            login(request, user)
            return redirect('pagina')
        else:
            return render(request, 'web_ujap/login.html', {
                'error': 'Usuario o contraseña incorrectos'
            })
    return render(request, 'web_ujap/login.html')


# ─── Crear usuario ─────────────────────────────────────────────────────────────
def usuario_view(request):
    if request.method == 'POST':
        cedula    = request.POST.get('cedula', '').strip()
        username  = request.POST.get('username', '').strip()
        facultad  = request.POST.get('facultad', '').strip()
        email     = request.POST.get('email', '').strip()
        password  = request.POST.get('password', '').strip()
        password2 = request.POST.get('password2', '').strip()

        if not all([cedula, facultad, email, password]):
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Todos los campos son obligatorios.'
            })

        if password != password2:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Las contraseñas no coinciden.'
            })

        if Usuario.objects.filter(email=email).exists():
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Ya existe una cuenta con ese correo.'
            })

        if Usuario.objects.filter(username=cedula).exists():
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Ya existe un usuario con esa cédula.'
            })
        if Usuario.objects.filter(username=username).exists():
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Ya existe un usuario con ese nombre de usuario.'
            })

        user = Usuario.objects.create_user(
            username=username,
            email=email,
            password=password,
            cedula=cedula,
            facultad=facultad,
        )
        login(request, user)
        return redirect('pagina')

    return render(request, 'web_ujap/crear_usuario.html')


# ─── Logout ───────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('login')


# ─── Página principal (después del login) ─────────────────────────────────────
@login_required(login_url='login')
def pagina_view(request):
    horarios = Horario.objects.select_related('materia').all().order_by('dia_semana', 'hora_inicio')
    
    # Organizar por sección y día
    horarios_json = []
    for h in horarios:
        horarios_json.append({
            'materia': h.materia.nombre,
            'codigo': h.materia.codigo,
            'dia': h.dia_semana,
            'inicio': h.hora_inicio.strftime('%H:%M'),
            'fin': h.hora_fin.strftime('%H:%M'),
            'aula': h.aula,
        })
    
    import json
    return render(request, 'web_ujap/pagina.html', {
        'horarios_json': json.dumps(horarios_json)
    })


# ─── Contacto ─────────────────────────────────────────────────────────────────
def contacto_view(request):
    return render(request, 'web_ujap/contacto.html')


# ─── Recuperar contraseña – Paso 1: pedir email ───────────────────────────────
def recuperar_view(request):
    if request.method == 'POST':
        correo = request.POST.get('email', '').strip().lower()
        usuario = Usuario.objects.filter(email__iexact=correo).first()

        if usuario:
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
                recipient_list=[usuario.email],
                html_message=email_html,
                fail_silently=False,
            )

        messages.success(request,
            'Si ese correo está registrado, recibirás las instrucciones en breve.')
        return redirect('recuperar_enviado')

    return render(request, 'web_ujap/recuperar.html')


# ─── Recuperar – Paso 2: aviso "revisá tu correo" ─────────────────────────────
def recuperar_enviado_view(request):
    return render(request, 'web_ujap/recuperar_enviado.html')


# ─── Recuperar – Paso 3: nueva contraseña ─────────────────────────────────────
def recuperar_confirmar_view(request, token):
    try:
        data = signing.loads(token, salt='recuperar-password', max_age=3600)
        usuario = Usuario.objects.get(id=data['id'])
    except (signing.SignatureExpired, signing.BadSignature, Usuario.DoesNotExist):
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
            usuario.set_password(pass1)  # ← encripta correctamente
            usuario.save()
            messages.success(request, '¡Contraseña actualizada correctamente!')
            return redirect('login')

    return render(request, 'web_ujap/recuperar_confirmar.html', {'token': token})


# ─── Dashboard ────────────────────────────────────────────────────────────────
def dashboard_index(request):
    hoy = timezone.now().date()
    inicio_mes = hoy.replace(day=1)

    total_estudiantes = Estudiante.objects.filter(activo=True).count()
    total_materias = Materia.objects.filter(activa=True).count()

    asistencias_hoy = Asistencia.objects.filter(fecha=hoy)
    total_asistencias_hoy = asistencias_hoy.count()
    presentes_hoy = asistencias_hoy.filter(estado='presente').count()
    ausentes_hoy = asistencias_hoy.filter(estado='ausente').count()
    tardes_hoy = asistencias_hoy.filter(estado='tarde').count()

    porcentaje_asistencia_hoy = 0
    if total_asistencias_hoy > 0:
        porcentaje_asistencia_hoy = round((presentes_hoy / total_asistencias_hoy) * 100, 2)

    asistencias_mes = Asistencia.objects.filter(fecha__gte=inicio_mes, fecha__lte=hoy)
    ausencias_mes = asistencias_mes.filter(estado='ausente').count()

    estudiantes_faltas = Estudiante.objects.filter(activo=True).annotate(
        total_faltas=Count('asistencias', filter=Q(asistencias__estado='ausente'))
    ).order_by('-total_faltas')[:5]

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

    materias_ausencias = Materia.objects.filter(activa=True).annotate(
        total_ausencias=Count('asistencias', filter=Q(asistencias__estado='ausente'))
    ).order_by('-total_ausencias')[:5]

    dias_español = {
        'monday': 'lunes', 'tuesday': 'martes', 'wednesday': 'miercoles',
        'thursday': 'jueves', 'friday': 'viernes', 'saturday': 'sabado', 'sunday': 'domingo'
    }
    dia_hoy_español = dias_español.get(hoy.strftime('%A').lower(), 'lunes')
    horarios_hoy = Horario.objects.filter(dia_semana=dia_hoy_español).order_by('hora_inicio')

    context = {
        'total_estudiantes': total_estudiantes,
        'total_materias': total_materias,
        'presentes_hoy': presentes_hoy,
        'ausentes_hoy': ausentes_hoy,
        'tardes_hoy': tardes_hoy,
        'porcentaje_asistencia_hoy': porcentaje_asistencia_hoy,
        'ausencias_mes': ausencias_mes,
        'estudiantes_faltas': estudiantes_faltas,
        'estudiantes_mejor_asistencia': estudiantes_mejor_asistencia,
        'materias_ausencias': materias_ausencias,
        'horarios_hoy': horarios_hoy,
        'hoy': hoy,
        'dia_hoy': dia_hoy_español,
    }
    return render(request, 'dashboard/index.html', context)


# ─── API Estadísticas ─────────────────────────────────────────────────────────
def estadisticas_json(request):
    tipo = request.GET.get('tipo', 'asistencias_semana')

    if tipo == 'asistencias_semana':
        hoy = timezone.now().date()
        labels = []
        datos = {'presentes': [], 'ausentes': [], 'tardes': []}

        for i in range(6, -1, -1):
            fecha = hoy - timedelta(days=i)
            asistencias = Asistencia.objects.filter(fecha=fecha)
            labels.append(fecha.strftime('%d/%m'))
            datos['presentes'].append(asistencias.filter(estado='presente').count())
            datos['ausentes'].append(asistencias.filter(estado='ausente').count())
            datos['tardes'].append(asistencias.filter(estado='tarde').count())

        return JsonResponse({
            'labels': labels,
            'datasets': [
                {'label': 'Presentes', 'data': datos['presentes'],
                 'backgroundColor': 'rgba(75, 192, 192, 0.6)', 'borderColor': 'rgba(75, 192, 192, 1)', 'borderWidth': 2},
                {'label': 'Ausentes', 'data': datos['ausentes'],
                 'backgroundColor': 'rgba(255, 99, 132, 0.6)', 'borderColor': 'rgba(255, 99, 132, 1)', 'borderWidth': 2},
                {'label': 'Tardanzas', 'data': datos['tardes'],
                 'backgroundColor': 'rgba(255, 206, 86, 0.6)', 'borderColor': 'rgba(255, 206, 86, 1)', 'borderWidth': 2},
            ]
        })

    elif tipo == 'estados_hoy':
        hoy = timezone.now().date()
        asistencias = Asistencia.objects.filter(fecha=hoy)
        return JsonResponse({
            'labels': ['Presentes', 'Ausentes', 'Tardanzas', 'Justificados'],
            'datasets': [{
                'data': [
                    asistencias.filter(estado='presente').count(),
                    asistencias.filter(estado='ausente').count(),
                    asistencias.filter(estado='tarde').count(),
                    asistencias.filter(estado='justificado').count(),
                ],
                'backgroundColor': [
                    'rgba(75, 192, 192, 0.8)', 'rgba(255, 99, 132, 0.8)',
                    'rgba(255, 206, 86, 0.8)', 'rgba(54, 162, 235, 0.8)'
                ],
                'borderWidth': 2
            }]
        })

    elif tipo == 'asistencias_por_materia':
        materias = Materia.objects.filter(activa=True).annotate(
            total_asistencias=Count('asistencias')
        ).order_by('-total_asistencias')[:5]
        return JsonResponse({
            'labels': [m.nombre for m in materias],
            'datasets': [{
                'label': 'Total Asistencias',
                'data': [m.total_asistencias for m in materias],
                'backgroundColor': 'rgba(153, 102, 255, 0.6)',
                'borderColor': 'rgba(153, 102, 255, 1)',
                'borderWidth': 2
            }]
        })

    return JsonResponse({'error': 'Tipo no válido'}, status=400)


# ─── Reporte estudiante ───────────────────────────────────────────────────────
def reporte_estudiante(request, estudiante_id):
    estudiante = Estudiante.objects.get(id=estudiante_id)
    asistencias = estudiante.asistencias.all().order_by('-fecha')

    context = {
        'estudiante': estudiante,
        'asistencias': asistencias[:20],
        'total_asistencias': asistencias.count(),
        'presentes': asistencias.filter(estado='presente').count(),
        'ausentes': asistencias.filter(estado='ausente').count(),
        'tardes': asistencias.filter(estado='tarde').count(),
        'justificados': asistencias.filter(estado='justificado').count(),
        'porcentaje': estudiante.calcular_porcentaje_asistencia()
    }
    return render(request, 'dashboard/reporte_estudiante.html', context)