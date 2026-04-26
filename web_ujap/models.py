from django.db import models

class UsuarioUJAP(models.Model): # <--- Asegúrate de que el nombre esté bien
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    facultad = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.cedula