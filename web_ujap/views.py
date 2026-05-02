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
from .models import Usuario, Estudiante, Materia, Horario, Asistencia, Seccion, SesionClase
 
 
# ─── Home ─────────────────────────────────────────────────────────────────────
def home_view(request):
    return render(request, 'web_ujap/home.html')
 
 
# ─── Login ────────────────────────────────────────────────────────────────────
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('usuario')
        password = request.POST.get('password')
 
        user = authenticate(request, username=username, password=password)
 
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
    secciones = Seccion.objects.filter(activa=True).order_by('codigo')
 
    if request.method == 'POST':
        username   = request.POST.get('username', '').strip()
        cedula     = request.POST.get('cedula', '').strip()
        password   = request.POST.get('password', '').strip()
        password2  = request.POST.get('password2', '').strip()
        seccion_id = request.POST.get('seccion', '').strip()
 
        # ── Validaciones ──────────────────────────────────────────────────
        if not all([username, cedula, password, password2, seccion_id]):
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Todos los campos son obligatorios.',
                'secciones': secciones,
            })
 
        if password != password2:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Las contraseñas no coinciden.',
                'secciones': secciones,
            })
 
        if len(password) < 8:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'La contraseña debe tener al menos 8 caracteres.',
                'secciones': secciones,
            })
 
        if Usuario.objects.filter(username=username).exists():
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Ese nombre de usuario ya está en uso, elegí otro.',
                'secciones': secciones,
            })
 
        # ── Verificar cédula ──────────────────────────────────────────────
        try:
            estudiante = Estudiante.objects.get(cedula=cedula, activo=True)
        except Estudiante.DoesNotExist:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Esa cédula no está registrada. Consultá a tu profesor.',
                'secciones': secciones,
            })
 
        # ── Verificar que no tenga cuenta ya ─────────────────────────────
        if estudiante.usuario is not None:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'Ya existe una cuenta vinculada a esa cédula.',
                'secciones': secciones,
            })
 
        # ── Verificar sección ─────────────────────────────────────────────
        try:
            seccion = Seccion.objects.get(id=seccion_id, activa=True)
        except Seccion.DoesNotExist:
            return render(request, 'web_ujap/crear_usuario.html', {
                'error': 'La sección seleccionada no es válida.',
                'secciones': secciones,
            })
 
        # ── Crear Usuario, vincular Estudiante y asignar Sección ──────────
        usuario = Usuario.objects.create_user(
            username=username,
            email=estudiante.correo,
            password=password,
            first_name=estudiante.nombre,
            last_name=estudiante.apellido,
            cedula=cedula,
            rol=Usuario.ROL_ESTUDIANTE,
        )
 
        estudiante.usuario = usuario
        estudiante.seccion = seccion
        estudiante.save()
 
        login(request, usuario)
        return redirect('pagina')
 
    return render(request, 'web_ujap/crear_usuario.html', {
        'secciones': secciones,
    })
 
 
# ─── Logout ───────────────────────────────────────────────────────────────────
def logout_view(request):
    logout(request)
    return redirect('login')
 
 
# ─── Página principal (después del login) ─────────────────────────────────────
@login_required(login_url='login')
def pagina_view(request):
    horarios = Horario.objects.select_related('materia').all().order_by('dia_semana', 'hora_inicio')
 
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
 
 
# ─── Recuperar contraseña – Paso 1 ────────────────────────────────────────────
def recuperar_view(request):
    if request.method == 'POST':
        correo = request.POST.get('email', '').strip().lower()
        usuario = Usuario.objects.filter(email__iexact=correo).first()
 
        if usuario:
            token = signing.dumps({'id': usuario.id}, salt='recuperar-password')
            reset_url = request.build_absolute_uri(f'/recuperar/confirmar/{token}/')
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
 
        messages.success(request, 'Si ese correo está registrado, recibirás las instrucciones en breve.')
        return redirect('recuperar_enviado')
 
    return render(request, 'web_ujap/recuperar.html')
 
 
# ─── Recuperar – Paso 2 ───────────────────────────────────────────────────────
def recuperar_enviado_view(request):
    return render(request, 'web_ujap/recuperar_enviado.html')
 
 
# ─── Recuperar – Paso 3 ───────────────────────────────────────────────────────
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
            usuario.set_password(pass1)
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
    return render(request, 'web_ujap/index.html', context)
 
 
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
 
 
# ─── Vistas QR ────────────────────────────────────────────────────────────────
import qrcode
import io
import base64
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django.http import HttpResponseForbidden
from functools import wraps
 
 
def solo_profesor(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.es_profesor:
            return HttpResponseForbidden("Solo los profesores pueden acceder aquí.")
        return view_func(request, *args, **kwargs)
    return wrapper
 
 
def solo_estudiante(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.es_estudiante:
            return HttpResponseForbidden("Solo los estudiantes pueden registrar asistencia por QR.")
        return view_func(request, *args, **kwargs)
    return wrapper
 
 
def _generar_qr_b64(url: str) -> str:
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return base64.b64encode(buffer.getvalue()).decode('utf-8')
 
 
@login_required(login_url='login')
@solo_profesor
def iniciar_sesion_view(request):
    horarios = Horario.objects.filter(
        profesor=request.user
    ).select_related('materia', 'seccion').order_by('dia_semana', 'hora_inicio')
 
    if request.method == 'POST':
        horario_id       = request.POST.get('horario')
        duracion_minutos = int(request.POST.get('duracion', 15))
 
        horario = get_object_or_404(Horario, id=horario_id, profesor=request.user)
 
        SesionClase.objects.filter(
            horario=horario,
            fecha=timezone.now().date(),
            activa=True
        ).update(activa=False)
 
        sesion = SesionClase.objects.create(
            horario=horario,
            fecha=timezone.now().date(),
            duracion_minutos=duracion_minutos,
            creada_por=request.user,
        )
        return redirect('dashboard:panel_sesion', token=sesion.token)
 
    return render(request, 'web_ujap/qr/iniciar_sesion.html', {'horarios': horarios})
 
 
@login_required(login_url='login')
@solo_profesor
def panel_sesion_view(request, token):
    sesion = get_object_or_404(SesionClase, token=token, creada_por=request.user)
 
    url_escaneo = request.build_absolute_uri(f'/asistencia/escanear/{token}/')
    qr_imagen_b64 = _generar_qr_b64(url_escaneo)
 
    todos_estudiantes = Estudiante.objects.filter(
        activo=True,
        seccion=sesion.horario.seccion
    ).order_by('apellido')
 
    asistencias_registradas = {
        a.estudiante_id: a
        for a in Asistencia.objects.filter(sesion=sesion).select_related('estudiante')
    }
 
    lista = []
    for est in todos_estudiantes:
        asistencia = asistencias_registradas.get(est.id)
        lista.append({
            'estudiante': est,
            'asistencia': asistencia,
            'estado': asistencia.estado if asistencia else 'sin_registro',
        })
 
    return render(request, 'web_ujap/qr/panel_sesion.html', {
        'sesion':       sesion,
        'qr_b64':       qr_imagen_b64,
        'url_escaneo':  url_escaneo,
        'lista':        lista,
        'total':        len(lista),
        'presentes':    sum(1 for x in lista if x['estado'] == 'presente'),
        'ausentes':     sum(1 for x in lista if x['estado'] == 'ausente'),
        'sin_registro': sum(1 for x in lista if x['estado'] == 'sin_registro'),
    })
 
 
@login_required(login_url='login')
@solo_profesor
@require_POST
def marcar_manual_view(request, token):
    sesion        = get_object_or_404(SesionClase, token=token, creada_por=request.user)
    estudiante_id = request.POST.get('estudiante_id')
    nuevo_estado  = request.POST.get('estado')
 
    if nuevo_estado not in ['presente', 'ausente', 'tarde', 'justificado']:
        return JsonResponse({'ok': False, 'error': 'Estado inválido.'}, status=400)
 
    estudiante = get_object_or_404(Estudiante, id=estudiante_id)
 
    Asistencia.objects.update_or_create(
        estudiante=estudiante,
        materia=sesion.horario.materia,
        fecha=sesion.fecha,
        defaults={'estado': nuevo_estado, 'metodo': 'manual', 'sesion': sesion}
    )
 
    return JsonResponse({'ok': True, 'estado': nuevo_estado,
                         'mensaje': f"{estudiante.nombre_completo} marcado como {nuevo_estado}."})
 
 
@login_required(login_url='login')
@solo_profesor
@require_POST
def cerrar_sesion_view(request, token):
    sesion = get_object_or_404(SesionClase, token=token, creada_por=request.user)
    sesion.activa = False
    sesion.save()
    return redirect('dashboard:index')
 
 
@login_required(login_url='login')
@solo_profesor
def estado_sesion_json(request, token):
    sesion = get_object_or_404(SesionClase, token=token, creada_por=request.user)
    asistencias = Asistencia.objects.filter(sesion=sesion).select_related('estudiante')
 
    return JsonResponse({
        'vigente':           sesion.esta_vigente,
        'minutos_restantes': sesion.minutos_restantes,
        'asistencias': [
            {
                'estudiante_id':   a.estudiante.id,
                'nombre_completo': a.estudiante.nombre_completo,
                'estado':          a.estado,
                'metodo':          a.metodo,
                'hora':            a.hora.strftime('%H:%M'),
            }
            for a in asistencias
        ]
    })
 
 
@login_required(login_url='login')
@solo_estudiante
def escanear_qr_view(request, token):
    sesion = SesionClase.objects.filter(token=token).select_related(
        'horario__materia'
    ).first()
 
    if not sesion:
        return render(request, 'web_ujap/qr/resultado_escaneo.html', {
            'exito': False, 'mensaje': 'El código QR no es válido.',
        })
 
    if not sesion.esta_vigente:
        return render(request, 'web_ujap/qr/resultado_escaneo.html', {
            'exito': False,
            'mensaje': 'Este código QR ya expiró o la sesión fue cerrada por el profesor.',
            'sesion': sesion,
        })
 
    try:
        estudiante = request.user.perfil_estudiante
    except Estudiante.DoesNotExist:
        return render(request, 'web_ujap/qr/resultado_escaneo.html', {
            'exito': False,
            'mensaje': 'Tu cuenta no está vinculada a ningún perfil de estudiante.',
        })
 
    ya_registro = Asistencia.objects.filter(
        estudiante=estudiante,
        materia=sesion.horario.materia,
        fecha=sesion.fecha,
    ).first()
 
    if ya_registro:
        return render(request, 'web_ujap/qr/resultado_escaneo.html', {
            'exito': False,
            'mensaje': f'Ya registraste tu asistencia para {sesion.horario.materia.nombre} hoy ({ya_registro.get_estado_display()}).',
            'sesion': sesion,
        })
 
    Asistencia.objects.create(
        estudiante=estudiante,
        materia=sesion.horario.materia,
        sesion=sesion,
        fecha=sesion.fecha,
        estado='presente',
        metodo='qr',
    )
 
    return render(request, 'web_ujap/qr/resultado_escaneo.html', {
        'exito':      True,
        'mensaje':    f'¡Asistencia registrada para {sesion.horario.materia.nombre}!',
        'sesion':     sesion,
        'estudiante': estudiante,
    })

@login_required(login_url='login')
@solo_profesor
def buscar_estudiante_json(request, token):
    from django.db import models as m
    sesion = get_object_or_404(SesionClase, token=token, creada_por=request.user)
    query  = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'resultados': []})
    estudiantes = Estudiante.objects.filter(
        activo=True, seccion=sesion.horario.seccion
    ).filter(
        m.Q(nombre__icontains=query) |
        m.Q(apellido__icontains=query) |
        m.Q(cedula__icontains=query)
    )[:10]
    ya_registrados = set(Asistencia.objects.filter(
        sesion=sesion).values_list('estudiante_id', flat=True))
    return JsonResponse({'resultados': [
        {'id': e.id, 'nombre': e.nombre_completo,
         'cedula': e.cedula, 'ya_registrado': e.id in ya_registrados}
        for e in estudiantes
    ]})

pass
    
 