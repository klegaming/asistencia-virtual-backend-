from django.shortcuts import render, redirect
from django.contrib import messages  
from .models import UsuarioUJAP

def login_view(request):
    if request.method == 'POST':
        user_data = request.POST.get('usuario')
        pass_data = request.POST.get('password')
        print(f"Intento de login - Usuario: {user_data}, Clave: {pass_data}")
    return render(request, 'web_ujap/login.html')

def contacto_view(request):
    return render(request, 'web_ujap/contacto.html')

def recuperar_view(request):
    return render(request, 'web_ujap/recuperar.html')

# ESTA ES LA ÚNICA QUE DEBE QUEDAR
def usuario_view(request):
    if request.method == 'POST':
        # 1. Atrapamos los datos del HTML
        cedula = request.POST.get('cedula')
        correo = request.POST.get('email')
        facu = request.POST.get('facultad')
        pass1 = request.POST.get('password', '').strip()
        pass2 = request.POST.get('confirm_password', '').strip()

        print(f"--- Intentando guardar: {cedula} ---")

        # 2. Verificamos contraseñas
        if pass1 == pass2 and pass1 != "":
            # 3.Guardamos en PostgreSQL
            UsuarioUJAP.objects.create(
                facultad=facu,
                password=pass1
            )
            print(f"✅ ¡Usuario {cedula} guardado exitosamente!")
            messages.success(request, "¡Cuenta creada con éxito!")
            return redirect('login')
        else:
            print("❌ Error: Las claves no coinciden o están vacías.")
            messages.error(request, "Las contraseñas no coinciden.")
            return render(request, 'web_ujap/crear_usuario.html', {
                'cedula_viva': cedula,
                'correo_vivo': correo,
            })

    return render(request, 'web_ujap/crear_usuario.html')