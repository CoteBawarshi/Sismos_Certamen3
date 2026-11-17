# Sismos en el Último Siglo

Aplicación web en **Django** que analiza los sismos de magnitud ≥ 5 registrados en el mundo entre 1926 y 2026 (catálogo USGS, 104.974 registros).

**Taller de Visualización de Datos – UDD** · Profesor: Cristián García
**Integrantes:** José Pablo Bawarshi, Carlos Espinoza, Maida Luna, Federico Orueta

## Entrega Certamen 3 – Parte 1

| Enlace | |
|---|---|
| 🌐 Sitio desplegado en AWS | **http://TU_IP_PUBLICA_EC2/** ← completar |
| 🎥 Video 1 – Proceso de despliegue en AWS | ← completar enlace |
| 🎥 Video 2 – Presentación del software y explicación del código | ← completar enlace |

## Contenido

**Reportes** (los 3 listados del Certamen 2 + 1 nuevo). Todos tienen, al final, los botones **"Descarga en PDF"** y **"Descarga en Excel"**:
1. Columnas Principales
2. Columnas Relevantes
3. Información Específica
4. **Sismicidad por Región y Año** (nuevo): tabla con los mismos datos y filtros del gráfico dinámico, explicación del origen, las variables y los cálculos, e interpretación automática.

**Gráficos:** evolución histórica (líneas), top 10 regiones (barras), evolución temporal interactiva, profundidad vs magnitud (dispersión), mapa 3D y **gráfico dinámico** (nuevo).

### Gráfico dinámico (nuevo)
- Filtros: **región/país**, **año desde – hasta** y **magnitud mínima**. Los filtros se envían por GET, así que quedan en la URL.
- Barras: cantidad de sismos por año. Color: magnitud promedio. Línea (eje derecho): magnitud máxima.
- Si la selección no tiene datos, se muestra el mensaje *"No hay datos para la selección actual"*.
- El botón "Ver estos datos en el Reporte 4" abre el reporte con los mismos filtros, y los resultados coinciden porque ambos usan la función `datos_dinamicos()`.

## Estructura del código (nuevas funcionalidades)

| Archivo | Qué contiene |
|---|---|
| `dashboard/models.py` | Modelo `Sismo` (tabla `dashboard_sismo` en SQLite). |
| `dashboard/management/commands/cargar_sismos.py` | Comando que carga el CSV del USGS en la base de datos. |
| `dashboard/views.py` | `cargar_datos()` lee desde la BD. Vistas `vista_grafico_dinamico`, `vista_reporte`, `descargar_pdf`, `descargar_excel`. |
| `dashboard/reportes.py` | Definición de los 4 reportes, filtros (`leer_filtros`, `datos_dinamicos`), interpretación y exportación a PDF (ReportLab) y Excel (openpyxl). |
| `dashboard/urls.py` | Rutas `grafico-dinamico/`, `reporte-dinamico/`, `reportes/<nombre>/pdf/` y `reportes/<nombre>/excel/`. |
| `dashboard/templates/dashboard/` | `reporte.html` (4 reportes + botones), `grafico_dinamico.html`, `_filtros.html` (formulario compartido), `_descripcion.html`. |
| `config/settings.py` | Lee `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` y la ruta de SQLite desde `.env`. |
| `deploy/setup_ec2.sh` | Script de despliegue automático en EC2. |

**Cómo se garantiza que pantalla, PDF y Excel coinciden:** cada reporte es una función en `reportes.py` que devuelve título, explicación y un DataFrame. La página, el PDF y el Excel llaman a la misma función con el mismo `request`, y los botones de descarga llevan los filtros vigentes en la URL (`?{{ request.GET.urlencode }}`).

## Instalación y ejecución local

Requisitos: Python 3.12 o superior.

```
python -m venv venv
venv\Scripts\activate            # en Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # en Linux/Mac: cp .env.example .env  (editar los valores)
python manage.py migrate
python manage.py cargar_sismos   # descarga el CSV y lo guarda en db.sqlite3 (~1 minuto)
python manage.py runserver
```

Luego abrir http://127.0.0.1:8000/

### Dependencias (`requirements.txt`)
Django · pandas · numpy · matplotlib · seaborn · plotly · **openpyxl** (Excel) · **reportlab** (PDF) · **python-dotenv** (variables de entorno) · **gunicorn** (servidor en AWS)

## Despliegue en AWS (EC2 + SQLite)

La base de datos es **SQLite** y vive en la instancia EC2: el archivo `db.sqlite3` está en el servidor y Django lo lee desde ahí. Los datos se cargan en la BD del servidor con el comando `cargar_sismos`.

### 1. Crear la instancia EC2
1. Entrar a la consola de AWS → **EC2** → **Launch instance**.
2. Nombre: `sismos-django`. AMI: **Ubuntu Server 24.04 LTS**. Tipo: **t2.micro / t3.micro** (capa gratuita). Si va lento al cargar los datos, usar **t3.small**.
3. **Key pair:** crear una nueva (`sismos-key.pem`) y descargarla. **No se sube al repositorio.**
4. **Network settings → Security group**: permitir
   - SSH (puerto 22) desde *My IP*
   - HTTP (puerto 80) desde *Anywhere (0.0.0.0/0)*
5. Storage: 8–10 GB. → **Launch instance**.
6. Copiar la **Public IPv4 address** de la instancia (por ejemplo `3.x.x.x`).

### 2. Conectarse a la instancia
Desde la consola: botón **Connect → EC2 Instance Connect**. También se puede usar SSH:
```
ssh -i sismos-key.pem ubuntu@TU_IP_PUBLICA_EC2
```

### 3. Descargar el proyecto y desplegar
```
git clone https://github.com/USUARIO/REPOSITORIO.git Sismos_en_el_ultimo_siglo
cd Sismos_en_el_ultimo_siglo
bash deploy/setup_ec2.sh
```
El script hace lo siguiente:
1. Instala Python, nginx y sqlite3.
2. Crea el entorno virtual e instala `requirements.txt`.
3. Crea el `.env` con una `SECRET_KEY` aleatoria, `DEBUG=False` y la IP pública en `ALLOWED_HOSTS`.
4. Ejecuta `migrate` y `cargar_sismos`, que crean `db.sqlite3` en el servidor con los 104.974 sismos.
5. Deja Django corriendo con **gunicorn** como servicio (`systemd`), para que siga activo al cerrar la terminal.
6. Configura **nginx** para atender en el puerto 80.

### 4. Comprobar desde un navegador externo
Abrir `http://TU_IP_PUBLICA_EC2/` desde otro computador o desde el celular, y revisar el gráfico dinámico, el Reporte 4 y las descargas PDF y Excel.

Para comprobar que los datos están en la base de datos del servidor:
```
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM dashboard_sismo;"
```

### Comandos útiles en el servidor
```
sudo systemctl status sismos                 # estado de Django/gunicorn
sudo journalctl -u sismos -n 50              # ver errores
git pull && sudo systemctl restart sismos    # actualizar el código
```

### Seguridad / credenciales
- `SECRET_KEY`, `DEBUG` y `ALLOWED_HOSTS` se leen desde el archivo `.env` con `python-dotenv`.
- `.env`, `db.sqlite3`, `venv/` y la llave `.pem` están en `.gitignore` y no se suben a GitHub. El repositorio solo incluye `.env.example` como plantilla.

## Tecnologías
Django · pandas · Matplotlib · Seaborn · Plotly · ReportLab · openpyxl · SQLite · AWS EC2 · gunicorn · nginx
