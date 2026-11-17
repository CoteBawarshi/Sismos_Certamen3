#!/usr/bin/env bash
# Script de despliegue en una instancia EC2 Ubuntu 24.04.
# Uso (dentro de la instancia, en la carpeta del proyecto):  bash deploy/setup_ec2.sh
set -e

PROYECTO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROYECTO"

echo "==> 1. Paquetes del sistema"
sudo apt update
sudo apt install -y python3-venv python3-pip nginx sqlite3

echo "==> 2. Entorno virtual y dependencias"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "==> 3. Archivo .env"
if [ ! -f .env ]; then
  IP=$(curl -s http://checkip.amazonaws.com || echo "")
  CLAVE=$(./venv/bin/python -c "import secrets; print(secrets.token_urlsafe(50))")
  cat > .env <<EOF
DJANGO_SECRET_KEY=$CLAVE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1,$IP
SQLITE_PATH=$PROYECTO/db.sqlite3
EOF
  echo "   .env creado con la IP pública $IP"
fi

echo "==> 4. Base de datos SQLite: tablas + carga de los 104.974 sismos"
./venv/bin/python manage.py migrate
./venv/bin/python manage.py cargar_sismos
./venv/bin/python manage.py collectstatic --noinput

echo "==> 5. Servicio gunicorn (systemd)"
sudo tee /etc/systemd/system/sismos.service > /dev/null <<EOF
[Unit]
Description=Django Sismos (gunicorn)
After=network.target

[Service]
User=$USER
WorkingDirectory=$PROYECTO
ExecStart=$PROYECTO/venv/bin/gunicorn --workers 2 --timeout 120 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now sismos
sudo systemctl restart sismos

echo "==> 6. Nginx (puerto 80 -> gunicorn)"
sudo tee /etc/nginx/sites-available/sismos > /dev/null <<EOF
server {
    listen 80;
    server_name _;
    client_max_body_size 10M;
    location /static/ { alias $PROYECTO/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120;
    }
}
EOF
sudo ln -sf /etc/nginx/sites-available/sismos /etc/nginx/sites-enabled/sismos
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl restart nginx

# El usuario de nginx debe poder entrar a la carpeta del proyecto para los estáticos
chmod o+x "$HOME"

echo "==> Listo. Abrir en el navegador: http://$(curl -s http://checkip.amazonaws.com)/"
