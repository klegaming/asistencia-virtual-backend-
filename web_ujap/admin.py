from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count, Q
from datetime import timedelta
import csv
from django.http import HttpResponse
from .models import UsuarioUJAP, Estudiante, Materia, Horario, Asistencia


@admin.register(UsuarioUJAP)
class UsuarioUJAPAdmin(admin.ModelAdmin):
    list_display = ['cedula', 'correo', 'facultad']
    search_fields = ['cedula', 'correo']


@admin.register(Estudiante)
class EstudianteAdmin(admin.ModelAdmin):
    list_display = ['cedula', 'nombre_completo_display', 'correo', 'activo', 'porcentaje_asistencia_display', 'total_faltas']
    list_filter = ['activo', 'fecha_ingreso']
    search_fields = ['nombre', 'apellido', 'cedula', 'correo']
    list_per_page = 25
    
    def nombre_completo_display(self, obj):
        return obj.nombre_completo
    nombre_completo_display.short_description = 'Nombre Completo'
    
    def porcentaje_asistencia_display(self, obj):
        porcentaje = obj.calcular_porcentaje_asistencia()
        if porcentaje >= 80:
            color = 'green'
        elif porcentaje >= 60:
            color = 'orange'
        else:
            color = 'red'
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}%</span>',
            color,
            porcentaje
        )
    porcentaje_asistencia_display.short_description = '% Asistencia'
    
    def total_faltas(self, obj):
        faltas = obj.asistencias.filter(estado='ausente').count()
        if faltas > 5:
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', faltas)
        return faltas
    total_faltas.short_description = 'Faltas'


@admin.register(Materia)
class MateriaAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'creditos', 'activa']
    list_filter = ['activa', 'creditos']
    search_fields = ['nombre', 'codigo']


@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ['materia', 'dia_semana', 'hora_inicio', 'hora_fin', 'aula', 'profesor']
    list_filter = ['dia_semana', 'materia']
    search_fields = ['materia__nombre', 'profesor', 'aula']
    ordering = ['dia_semana', 'hora_inicio']


@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ['estudiante', 'materia', 'fecha', 'hora', 'estado_display']
    list_filter = ['estado', 'fecha', 'materia']
    search_fields = ['estudiante__nombre', 'estudiante__apellido', 'estudiante__cedula', 'materia__nombre']
    date_hierarchy = 'fecha'
    list_per_page = 50
    
    def estado_display(self, obj):
        colors = {
            'presente': 'green',
            'ausente': 'red',
            'tarde': 'orange',
            'justificado': 'blue'
        }
        color = colors.get(obj.estado, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
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
        writer.writerow(['Estudiante', 'Cédula', 'Materia', 'Fecha', 'Hora', 'Estado', 'Observaciones'])
        
        for asistencia in queryset:
            writer.writerow([
                asistencia.estudiante.nombre_completo,
                asistencia.estudiante.cedula,
                asistencia.materia.nombre,
                asistencia.fecha,
                asistencia.hora,
                asistencia.get_estado_display(),
                asistencia.observaciones
            ])
        
        return response
    exportar_reporte.short_description = 'Exportar reporte a CSV'


# Personalización del Admin Site
admin.site.site_header = 'Sistema de Asistencia UJAP'
admin.site.site_title = 'Panel de Administración'
admin.site.index_title = 'Gestión de Asistencias'