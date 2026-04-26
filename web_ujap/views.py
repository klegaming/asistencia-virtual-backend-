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