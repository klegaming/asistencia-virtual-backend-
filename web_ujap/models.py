from django.db import models
from django.utils import timezone

# ===== TU MODELO EXISTENTE (NO TOCAR) =====
class UsuarioUJAP(models.Model):
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    facultad = models.CharField(max_length=100)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.cedula


# ===== NUEVOS MODELOS PARA EL DASHBOARD =====

class Estudiante(models.Model):
    """Modelo para estudiantes"""
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    cedula = models.CharField(max_length=20, unique=True)
    correo = models.EmailField(unique=True)
    fecha_ingreso = models.DateField(default=timezone.now)
    activo = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Estudiante"
        verbose_name_plural = "Estudiantes"
        ordering = ['apellido', 'nombre']
    
    def __str__(self):
        return f"{self.apellido}, {self.nombre} ({self.cedula})"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    def calcular_porcentaje_asistencia(self):
        total = self.asistencias.count()
        if total == 0:
            return 0
        presentes = self.asistencias.filter(estado='presente').count()
        return round((presentes / total) * 100, 2)


class Materia(models.Model):
    """Modelo para materias/cursos"""
    nombre = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(blank=True)
    creditos = models.IntegerField(default=3)
    activa = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Materia"
        verbose_name_plural = "Materias"
        ordering = ['nombre']
    
    def __str__(self):
        return f"{self.codigo} - {self.nombre}"


class Horario(models.Model):
    """Modelo para horarios de clases"""
    DIAS_SEMANA = [
        ('lunes', 'Lunes'),
        ('martes', 'Martes'),
        ('miercoles', 'Miércoles'),
        ('jueves', 'Jueves'),
        ('viernes', 'Viernes'),
        ('sabado', 'Sábado'),
    ]
    
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='horarios')
    dia_semana = models.CharField(max_length=10, choices=DIAS_SEMANA)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()
    aula = models.CharField(max_length=50)
    profesor = models.CharField(max_length=100)
    
    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        ordering = ['dia_semana', 'hora_inicio']
    
    def __str__(self):
        return f"{self.materia.nombre} - {self.get_dia_semana_display()} {self.hora_inicio}-{self.hora_fin}"


class Asistencia(models.Model):
    """Modelo para registro de asistencias"""
    ESTADOS = [
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
        ('tarde', 'Tardanza'),
        ('justificado', 'Justificado'),
    ]
    
    estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, related_name='asistencias')
    materia = models.ForeignKey(Materia, on_delete=models.CASCADE, related_name='asistencias')
    fecha = models.DateField(default=timezone.now)
    hora = models.TimeField(auto_now_add=True)
    estado = models.CharField(max_length=15, choices=ESTADOS, default='presente')
    observaciones = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        ordering = ['-fecha', '-hora']
        unique_together = ['estudiante', 'materia', 'fecha']
    
    def __str__(self):
        return f"{self.estudiante.nombre_completo} - {self.materia.nombre} ({self.get_estado_display()}) - {self.fecha}"