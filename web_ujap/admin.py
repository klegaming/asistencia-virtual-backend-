from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
import csv
from django.http import HttpResponse
from .models import UsuarioUJAP, Usuario, Estudiante, Materia, Horario, Asistencia, Seccion, SesionClase


# ─── Usuario UJAP (legacy) ────────────────────────────────────────────────────
@admin.register(UsuarioUJAP)
class UsuarioUJAPAdmin(admin.ModelAdmin):
    list_display  = ['cedula', 'correo', 'facultad']
    search_fields = ['cedula', 'correo']


# ─── Usuario (custom) ─────────────────────────────────────────────────────────
@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display  = ['username', 'first_name', 'last_name', 'rol', 'cedula', 'is_staff']
    list_filter   = ['rol', 'is_staff']
    search_fields = ['username', 'first_name', 'last_name', 'cedula']
    fieldsets     = UserAdmin.fieldsets + (
        ('Datos UJAP', {'fields': ('rol', 'cedula', 'facultad')}),
    )


# ─── Sección ──────────────────────────────────────────────────────────────────
@admin.register(Seccion)
class SeccionAdmin(admin.ModelAdmin):
    list_display  = ['codigo', 'periodo', 'carrera', 'activa']
    list_filter   = ['activa', 'periodo', 'carrera']
    search_fields = ['codigo', 'carrera']


# ─── Estudiante ───────────────────────────────────────────────────────────────
@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display  = ['cedula', 'nombre_completo_display', 'correo', 'seccion', 'activo',
                     'porcentaje_asistencia_display', 'total_faltas']
    list_filter   = ['activo', 'seccion', 'fecha_ingreso']
    search_fields = ['nombre', 'apellido', 'cedula', 'correo']
    list_per_page = 25

    def nombre_completo_display(self, obj):
        return obj.nombre_completo
    nombre_completo_display.short_description = 'Nombre Completo'

    def porcentaje_asistencia_display(self, obj):
        porcentaje = obj.calcular_porcentaje_asistencia()
        color = 'green' if porcentaje >= 80 else 'orange' if porcentaje >= 60 else 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>', color, porcentaje
        )
    porcentaje_asistencia_display.short_description = '% Asistencia'

    def total_faltas(self, obj):
        faltas = obj.asistencias.filter(estado='ausente').count()
        if faltas > 5:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', faltas)
        return faltas
    total_faltas.short_description = 'Faltas'


# ─── Materia ──────────────────────────────────────────────────────────────────
@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display  = ['codigo', 'nombre', 'creditos', 'activa']
    list_filter   = ['activa', 'creditos']
    search_fields = ['nombre', 'codigo']


# ─── Horario ──────────────────────────────────────────────────────────────────
@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display  = ['materia', 'seccion', 'dia_semana', 'hora_inicio', 'hora_fin', 'aula', 'profesor']
    list_filter   = ['seccion', 'dia_semana', 'materia']
    search_fields = ['materia__nombre', 'aula']
    ordering      = ['dia_semana', 'hora_inicio']


# ─── Sesión de Clase ──────────────────────────────────────────────────────────
@admin.register(SesionClase)
class SesionClaseAdmin(admin.ModelAdmin):
    list_display  = ['horario', 'fecha', 'activa', 'creada_por', 'duracion_minutos', 'creada_en']
    list_filter   = ['activa', 'fecha']
    search_fields = ['horario__materia__nombre', 'creada_por__username']
    readonly_fields = ['token', 'creada_en']


# ─── Asistencia ───────────────────────────────────────────────────────────────
@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display  = ['estudiante', 'materia', 'fecha', 'hora', 'estado_display', 'metodo']
    list_filter   = ['estado', 'metodo', 'fecha', 'materia']
    search_fields = ['estudiante__nombre', 'estudiante__apellido', 'estudiante__cedula', 'materia__nombre']
    date_hierarchy = 'fecha'
    list_per_page = 50

    def estado_display(self, obj):
        colors = {
            'presente':    'green',
            'ausente':     'red',
            'tarde':       'orange',
            'justificado': 'blue'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            colors.get(obj.estado, 'black'),
            obj.get_estado_display()
        )
    estado_display.short_description = 'Estado'

    actions = ['marcar_como_presente', 'marcar_como_ausente', 'exportar_reporte']

    def marcar_como_presente(self, request, queryset):
        updated = queryset.update(estado='presente')
        self.message_user(request, f'{updated} asistencias marcadas como Presente.')
    marcar_como_presente.short_description = 'Marcar como Presente'

    def marcar_como_ausente(self, request, queryset):
        updated = queryset.update(estado='ausente')
        self.message_user(request, f'{updated} asistencias marcadas como Ausente.')
    marcar_como_ausente.short_description = 'Marcar como Ausente'

    def exportar_reporte(self, request, queryset):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="reporte_asistencias.csv"'
        writer = csv.writer(response)
        writer.writerow(['Estudiante', 'Cédula', 'Materia', 'Fecha', 'Hora', 'Estado', 'Método', 'Observaciones'])
        for a in queryset:
            writer.writerow([
                a.estudiante.nombre_completo,
                a.estudiante.cedula,
                a.materia.nombre,
                a.fecha,
                a.hora,
                a.get_estado_display(),
                a.get_metodo_display(),
                a.observaciones,
            ])
        return response
    exportar_reporte.short_description = 'Exportar reporte a CSV'


# ─── Personalización del sitio admin ─────────────────────────────────────────
admin.site.site_header  = 'Sistema de Asistencia UJAP'
admin.site.site_title   = 'Panel de Administración'
admin.site.index_title  = 'Gestión de Asistencias'