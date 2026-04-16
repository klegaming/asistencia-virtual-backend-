from django.shortcuts import render,redirect
from django.contrib import messages  
from django.shortcuts import render

def login_view(request):
    # Verificamos si el usuario hizo clic en el botón (envió el formulario)
    if request.method == 'POST':
        # Sacamos los datos usando los 'name' que pusiste en el HTML
        user_data = request.POST.get('usuario')
        pass_data = request.POST.get('password')
        
        # Esto aparecerá en tu terminal negra de VS Code
        print(f"Intento de login - Usuario: {user_data}, Clave: {pass_data}")
        
    return render(request, 'web_ujap/login.html')

def contacto_view(request):
    return render(request, 'web_ujap/contacto.html')

def recuperar_view(request):
    return render(request, 'web_ujap/recuperar.html')

def usuario_view(request):
    return render(request, 'web_ujap/crear_usuario.html')

def usuario_view(request):
    # 1. Verificamos si la petición es POST (alguien pulsó el botón)
    if request.method == 'POST':
        # 2. "Atrapamos" los datos usando los nombres que pusiste en el HTML
        cedula_ingresada = request.POST.get('cedula')
        facultad_seleccionada = request.POST.get('facultad')
        
        # 3. Lo imprimimos en la terminal de VS Code para confirmar
        print("--- NUEVO REGISTRO RECIBIDO ---")
        print(f"Cédula: {cedula_ingresada}")
        print(f"Facultad: {facultad_seleccionada}")
        print("-------------------------------")
        
        # 4. Por ahora, lo devolvemos al login después de "registrarlo"
        return render(request, 'web_ujap/login.html')

    # Si solo está entrando a la página (GET), mostramos el formulario vacío
    return render(request, 'web_ujap/crear_usuario.html')

def usuario_view(request):
    if request.method == 'POST':
        # Capturamos los nuevos campos
        correo = request.POST.get('email')
        clave1 = request.POST.get('password')
        clave2 = request.POST.get('confirm_password')
        
        if clave1 == clave2:
            print(f"Registro exitoso: {correo}")
            return render(request, 'web_ujap/login.html')
        else:
            # Si no coinciden, podemos pasar una variable de error al HTML
            print("Error: Las contraseñas no coinciden")
            return render(request, 'web_ujap/crear_usuario.html', {'error': 'Las contraseñas no coinciden'})

    return render(request, 'web_ujap/crear_usuario.html')

    


def usuario_view(request):
    if request.method == 'POST':
        # Capturamos con los nombres exactos del HTML
        cedula = request.POST.get('cedula')
        correo = request.POST.get('email')
        facu = request.POST.get('facultad')
        pass1 = request.POST.get('password', '').strip() # .strip() quita espacios locos
        pass2 = request.POST.get('confirm_password', '').strip()

        if pass1 == pass2 and pass1 != "": # Verificamos que sean iguales y no estén vacías
            messages.success(request, "¡Cuenta creada con éxito!")
            return redirect('login')
        else:
            messages.error(request, "Las contraseñas no coinciden o están vacías.")
            # Mandamos los datos de vuelta para que no se borren
            return render(request, 'web_ujap/crear_usuario.html', {
                'cedula_viva': cedula,
                'correo_vivo': correo,
                'facu_viva': facu
            })

    return render(request, 'web_ujap/crear_usuario.html')