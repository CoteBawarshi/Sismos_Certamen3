from django.urls import path
from . import views

urlpatterns = [
    # Página de inicio
    path('', views.vista_inicio, name='inicio'),

    # Ruta obligatoria para guardar descripciones editadas desde la web
    path('guardar-descripcion/', views.guardar_descripcion_view, name='guardar_descripcion'),

    # Rutas de los Reportes (los 3 listados del Certamen 2 + el reporte nuevo)
    path('datos-principales/', views.vista_datos_principales, name='datos_principales'),
    path('datos-secundarios/', views.vista_datos_secundarios, name='datos_secundarios'),
    path('datos-especificos/', views.vista_datos_especificos, name='datos_especificos'),
    path('reporte-dinamico/', views.vista_reporte_dinamico, name='reporte_dinamico'),

    # Descargas de cada reporte: <nombre> = principales | secundarios | especificos | dinamico
    path('reportes/<str:nombre>/pdf/', views.descargar_pdf, name='descargar_pdf'),
    path('reportes/<str:nombre>/excel/', views.descargar_excel, name='descargar_excel'),

    # Rutas para los Gráficos
    path('grafico-1/', views.vista_grafico_1, name='grafico_1'),
    path('grafico-2/', views.vista_grafico_2, name='grafico_2'),
    path('grafico-3/', views.vista_grafico_3, name='grafico_3'),
    path('grafico-4/', views.vista_grafico_4, name='grafico_4'),
    path('mapa-terremotos/', views.mapa_terremotos_view, name='mapa_terremotos'),
    path('grafico-dinamico/', views.vista_grafico_dinamico, name='grafico_dinamico'),
]
