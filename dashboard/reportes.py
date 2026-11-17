"""Definición de los 4 reportes y sus descargas en PDF y Excel.

Cada reporte es una función que recibe el `request` y devuelve un diccionario con:
    titulo, descripcion, explicaciones, filtros, df (tabla), interpretacion

La MISMA función se usa para la página HTML, el PDF y el Excel, por eso los tres
siempre muestran exactamente los mismos datos (incluidos los filtros vigentes).
"""
import io
import datetime as dt

import pandas as pd
from django.http import HttpResponse

from .views import cargar_datos

AÑO_MIN, AÑO_MAX = 1926, 2026


# --------------------------------------------------------------------------
# Filtros del gráfico dinámico / reporte 4
# --------------------------------------------------------------------------
def _entero(valor, defecto, minimo, maximo):
    try:
        return max(minimo, min(maximo, int(valor)))
    except (TypeError, ValueError):
        return defecto


def _decimal(valor, defecto, minimo, maximo):
    try:
        return max(minimo, min(maximo, round(float(valor), 1)))
    except (TypeError, ValueError):
        return defecto


def leer_filtros(request):
    """Lee y valida los filtros desde la URL (?pais=Chile&desde=1960&hasta=2026&mag_min=6)."""
    desde = _entero(request.GET.get('desde'), 1960, AÑO_MIN, AÑO_MAX)
    hasta = _entero(request.GET.get('hasta'), AÑO_MAX, AÑO_MIN, AÑO_MAX)
    if desde > hasta:
        desde, hasta = hasta, desde
    return {
        'pais': request.GET.get('pais') or 'Todos',
        'desde': desde,
        'hasta': hasta,
        'mag_min': _decimal(request.GET.get('mag_min'), 5.0, 5.0, 9.5),
    }


def lista_paises(limite=40):
    """Países / regiones con más sismos, para el selector de filtros."""
    conteo = cargar_datos()['pais'].value_counts()
    return ['Todos'] + sorted(conteo.head(limite).index.tolist())


def datos_dinamicos(filtros):
    """Filtra los sismos y los agrupa por año. Lo usan el gráfico y el reporte."""
    df = cargar_datos()
    mask = (df['año'] >= filtros['desde']) & (df['año'] <= filtros['hasta']) & (df['mag'] >= filtros['mag_min'])
    if filtros['pais'] != 'Todos':
        mask &= df['pais'] == filtros['pais']
    sub = df[mask]

    tabla = (
        sub.groupby('año')
        .agg(cantidad=('mag', 'size'), mag_prom=('mag', 'mean'), mag_max=('mag', 'max'), prof_prom=('depth', 'mean'))
        .reset_index()
        .round(2)
    )
    tabla['año'] = tabla['año'].astype(int)
    tabla['cantidad'] = tabla['cantidad'].astype(int)
    tabla.columns = ['Año', 'Cantidad de sismos', 'Magnitud promedio', 'Magnitud máxima', 'Profundidad promedio (km)']
    return tabla


def texto_filtros(f):
    region = 'todas las regiones' if f['pais'] == 'Todos' else f['pais']
    return f"Región: {region} · Período: {f['desde']}–{f['hasta']} · Magnitud mínima: {f['mag_min']}"


def interpretar(tabla, f):
    if tabla.empty:
        return 'No hay sismos que cumplan los filtros seleccionados, por lo que no es posible interpretar la información.'
    total = int(tabla['Cantidad de sismos'].sum())
    fila_peak = tabla.loc[tabla['Cantidad de sismos'].idxmax()]
    fila_max = tabla.loc[tabla['Magnitud máxima'].idxmax()]
    años = len(tabla)
    region = 'el mundo' if f['pais'] == 'Todos' else f['pais']
    total_txt = f'{total:,}'.replace(',', '.')  # separador de miles chileno
    texto = (
        f"Entre {f['desde']} y {f['hasta']} se registraron {total_txt} sismos de magnitud ≥ {f['mag_min']} en {region}, "
        f"distribuidos en {años} años con actividad (promedio de {total / años:.1f} sismos por año). "
        f"El año con más eventos fue {int(fila_peak['Año'])} ({int(fila_peak['Cantidad de sismos'])} sismos) y "
        f"el sismo más fuerte del período alcanzó magnitud {fila_max['Magnitud máxima']:.1f} en {int(fila_max['Año'])}. "
    )
    if f['desde'] < 1970:
        texto += ('Hay que considerar que antes de 1970 la red sismológica mundial tenía menor cobertura, '
                  'por lo que el aumento de registros en décadas recientes se explica en parte por una mejor detección.')
    return texto


# --------------------------------------------------------------------------
# Definición de los 4 reportes
# --------------------------------------------------------------------------
def _muestra(cols):
    """Primeras 15 filas del dataset (las mismas que se muestran en pantalla)."""
    df = cargar_datos()
    tabla = df[[c for c in cols if c in df.columns]].head(15).copy()
    if 'time' in tabla.columns:
        tabla['time'] = tabla['time'].dt.tz_localize(None).dt.floor('s')
    return tabla


ORIGEN = ('Origen de los datos: catálogo sísmico del USGS (United States Geological Survey) con sismos de '
          'magnitud ≥ 5 entre 1926 y 2026, almacenado en la base de datos SQLite del servidor (tabla dashboard_sismo).')


def reporte_principales(request):
    return {
        'titulo': 'Reporte 1: Columnas Principales del Dataset',
        'descripcion': ORIGEN + ' Se muestran las 15 filas más recientes con las variables de ubicación, profundidad y magnitud.',
        'explicaciones': [
            ('time', 'Fecha y hora exacta en que ocurrió el evento sísmico (en formato UTC).'),
            ('latitude', 'Latitud geográfica del hipocentro en grados decimales.'),
            ('longitude', 'Longitud geográfica del hipocentro en grados decimales.'),
            ('depth', 'Profundidad del sismo medida en kilómetros bajo la superficie terrestre.'),
            ('mag', 'Magnitud del evento (medida principal en escala Richter o de momento).'),
            ('pais', 'País o región geográfica inferida a partir de la descripción de ubicación.'),
        ],
        'df': _muestra(['time', 'latitude', 'longitude', 'depth', 'mag', 'pais']),
    }


def reporte_secundarios(request):
    return {
        'titulo': 'Reporte 2: Columnas Relevantes / Secundarias',
        'descripcion': ORIGEN + ' Se muestran las 15 filas más recientes con las variables de calidad de la medición.',
        'explicaciones': [
            ('nst', 'Número total de estaciones/sensores sísmicos que registraron el evento.'),
            ('rms', 'Error cuadrático medio del tiempo de llegada de la onda sísmica (precisión del ajuste).'),
            ('gap', 'Brecha azimutal entre estaciones (en grados). Un menor valor indica mejor cobertura.'),
            ('dmin', 'Distancia horizontal desde el epicentro hasta la estación sísmica más cercana.'),
            ('magType', 'Algoritmo o método de cálculo de la magnitud (ej. Mw, Mb, Ms).'),
        ],
        'df': _muestra(['nst', 'rms', 'gap', 'dmin', 'magType']),
    }


def reporte_especificos(request):
    return {
        'titulo': 'Reporte 3: Información Específica y Metadatos',
        'descripcion': ORIGEN + ' Se muestran las 15 filas más recientes con los metadatos de cada registro.',
        'explicaciones': [
            ('id', 'Identificador alfa-numérico único asignado por el catálogo sísmico USGS.'),
            ('updated', 'Fecha y hora de la última modificación o recálculo del registro.'),
            ('type', 'Clasificación del evento telúrico (ej. earthquake, explosion, quarry blast).'),
            ('status', 'Estado de revisión del dato (ej. reviewed por un sismólogo o automatic).'),
            ('locationSource', 'Sigla de la red o centro sismológico que determinó las coordenadas.'),
            ('magSource', 'Sigla de la institución que calculó el valor de la magnitud.'),
        ],
        'df': _muestra(['id', 'updated', 'type', 'status', 'locationSource', 'magSource']),
    }


def reporte_dinamico(request):
    filtros = leer_filtros(request)
    tabla = datos_dinamicos(filtros)
    return {
        'titulo': 'Reporte 4: Sismicidad Anual por Región y Magnitud',
        'descripcion': (
            ORIGEN + ' Son los mismos datos del Gráfico Dinámico. Se filtran los sismos por región, rango de años '
            'y magnitud mínima; luego se agrupan por año y se calcula, para cada año, la cantidad de sismos, '
            'la magnitud promedio, la magnitud máxima y la profundidad promedio.'
        ),
        'explicaciones': [
            ('Año', 'Año calendario (UTC) en que ocurrieron los sismos.'),
            ('Cantidad de sismos', 'Número de sismos del año que cumplen los filtros (conteo).'),
            ('Magnitud promedio', 'Promedio de la magnitud de esos sismos (2 decimales).'),
            ('Magnitud máxima', 'Magnitud del sismo más fuerte del año.'),
            ('Profundidad promedio (km)', 'Promedio de la profundidad del hipocentro en kilómetros.'),
        ],
        'filtros': filtros,
        'filtros_texto': texto_filtros(filtros),
        'df': tabla,
        'interpretacion': interpretar(tabla, filtros),
    }


REPORTES = {
    'principales': reporte_principales,
    'secundarios': reporte_secundarios,
    'especificos': reporte_especificos,
    'dinamico': reporte_dinamico,
}


# --------------------------------------------------------------------------
# Exportación a Excel (.xlsx) con openpyxl
# --------------------------------------------------------------------------
def _nombre_archivo(rep, extension):
    base = rep['titulo'].split(':')[0].strip().lower().replace(' ', '_')
    return f"{base}_{dt.date.today():%Y%m%d}.{extension}"


def exportar_excel(rep):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    df = rep['df']
    wb = Workbook()
    ws = wb.active
    ws.title = 'Datos'

    ws['A1'] = rep['titulo']
    ws['A1'].font = Font(bold=True, size=14)
    fila = 2
    if rep.get('filtros_texto'):
        ws.cell(row=fila, column=1, value='Filtros: ' + rep['filtros_texto']).font = Font(italic=True)
        fila += 1
    fila += 1  # fila en blanco

    # Encabezados
    relleno = PatternFill('solid', fgColor='2C3E50')
    for j, col in enumerate(df.columns, start=1):
        celda = ws.cell(row=fila, column=j, value=str(col))
        celda.font = Font(bold=True, color='FFFFFF')
        celda.fill = relleno
        celda.alignment = Alignment(horizontal='center')
    fila_encabezado = fila

    # Datos: los números se escriben como números (no como texto)
    for registro in df.itertuples(index=False):
        fila += 1
        for j, valor in enumerate(registro, start=1):
            if pd.isna(valor):
                valor = None
            elif isinstance(valor, pd.Timestamp):
                valor = valor.to_pydatetime()
            elif hasattr(valor, 'item'):  # numpy int/float -> int/float de Python
                valor = valor.item()
            celda = ws.cell(row=fila, column=j, value=valor)
            if isinstance(valor, dt.datetime):
                celda.number_format = 'yyyy-mm-dd hh:mm:ss'

    # Ancho de columnas según el contenido
    for j, col in enumerate(df.columns, start=1):
        largo = max([len(str(col))] + [len(str(v)) for v in df.iloc[:, j - 1]])
        ws.column_dimensions[get_column_letter(j)].width = min(max(largo + 2, 10), 45)
    ws.freeze_panes = ws.cell(row=fila_encabezado + 1, column=1)

    # Segunda hoja con la explicación que aparece en pantalla
    ex = wb.create_sheet('Explicación')
    ex.column_dimensions['A'].width = 28
    ex.column_dimensions['B'].width = 100
    ex['A1'] = rep['titulo']
    ex['A1'].font = Font(bold=True, size=14)
    ex['A3'] = 'Descripción'
    ex['B3'] = rep['descripcion']
    n = 4
    if rep.get('filtros_texto'):
        ex.cell(row=n, column=1, value='Filtros')
        ex.cell(row=n, column=2, value=rep['filtros_texto'])
        n += 1
    n += 1
    ex.cell(row=n, column=1, value='Variable').font = Font(bold=True)
    ex.cell(row=n, column=2, value='Significado').font = Font(bold=True)
    for var, desc in rep['explicaciones']:
        n += 1
        ex.cell(row=n, column=1, value=var)
        ex.cell(row=n, column=2, value=desc)
    if rep.get('interpretacion'):
        n += 2
        ex.cell(row=n, column=1, value='Interpretación').font = Font(bold=True)
        ex.cell(row=n, column=2, value=rep['interpretacion'])
    for r in ex.iter_rows():
        for c in r:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    ex['A3'].font = Font(bold=True)

    buffer = io.BytesIO()
    wb.save(buffer)
    respuesta = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )
    respuesta['Content-Disposition'] = f'attachment; filename="{_nombre_archivo(rep, "xlsx")}"'
    return respuesta


# --------------------------------------------------------------------------
# Exportación a PDF con ReportLab
# --------------------------------------------------------------------------
def _formatear(valor):
    if pd.isna(valor):
        return '—'
    if isinstance(valor, pd.Timestamp):
        return valor.strftime('%Y-%m-%d %H:%M:%S')
    if isinstance(valor, float):
        return f'{valor:.2f}'.rstrip('0').rstrip('.') if valor != int(valor) else f'{valor:.1f}'
    return str(valor)


def exportar_pdf(rep):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), leftMargin=1.5 * cm, rightMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm, title=rep['titulo'],
    )
    estilos = getSampleStyleSheet()
    normal = ParagraphStyle('normal', parent=estilos['Normal'], fontSize=10, leading=14)
    celda = ParagraphStyle('celda', parent=normal, fontSize=8.5, leading=10.5)
    encabezado = ParagraphStyle('enc', parent=celda, textColor=colors.white, fontName='Helvetica-Bold')

    elementos = [
        Paragraph(rep['titulo'], estilos['Title']),
        Paragraph(rep['descripcion'], normal),
        Spacer(1, 6),
    ]
    if rep.get('filtros_texto'):
        elementos += [Paragraph('<b>Filtros aplicados:</b> ' + rep['filtros_texto'], normal), Spacer(1, 6)]

    elementos.append(Paragraph('<b>Descripción de las variables:</b>', normal))
    for var, desc in rep['explicaciones']:
        elementos.append(Paragraph(f'• <b>{var}</b>: {desc}', normal))
    elementos.append(Spacer(1, 10))

    df = rep['df']
    if df.empty:
        elementos.append(Paragraph('<b>No hay datos para la selección actual.</b>', normal))
    else:
        datos = [[Paragraph(str(c), encabezado) for c in df.columns]]
        for registro in df.itertuples(index=False):
            datos.append([Paragraph(_formatear(v), celda) for v in registro])

        # Ancho de columnas proporcional al contenido, usando todo el ancho de la página
        largos = [max(len(str(c)), *(len(_formatear(v)) for v in df[c])) for c in df.columns]
        largos = [min(max(l, 6), 40) for l in largos]
        ancho = doc.width
        col_widths = [ancho * l / sum(largos) for l in largos]

        tabla = Table(datos, colWidths=col_widths, repeatRows=1)
        tabla.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2c3e50')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#bdc3c7')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f2f4f6')]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elementos.append(tabla)

    if rep.get('interpretacion'):
        elementos += [Spacer(1, 10), Paragraph('<b>Interpretación:</b> ' + rep['interpretacion'], normal)]

    def pie(canvas, doc_):
        canvas.setFont('Helvetica', 8)
        canvas.drawString(1.5 * cm, 0.8 * cm, f'Sismos en el Último Siglo · Generado el {dt.datetime.now():%d-%m-%Y %H:%M}')
        canvas.drawRightString(doc_.pagesize[0] - 1.5 * cm, 0.8 * cm, f'Página {doc_.page}')

    doc.build(elementos, onFirstPage=pie, onLaterPages=pie)
    respuesta = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    respuesta['Content-Disposition'] = f'attachment; filename="{_nombre_archivo(rep, "pdf")}"'
    return respuesta
