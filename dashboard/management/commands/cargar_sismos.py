"""Carga el CSV de sismos USGS en la base de datos (tabla dashboard_sismo).

Uso:
    python manage.py cargar_sismos               # descarga el CSV desde GitHub
    python manage.py cargar_sismos --csv ruta.csv  # usa un archivo local
"""
import pandas as pd
from django.core.management.base import BaseCommand
from django.db import transaction

from dashboard.models import Sismo
from dashboard.views import CSV_URL, extraer_pais_limpio


def _num(valor):
    return None if pd.isna(valor) else float(valor)


def _txt(valor):
    return '' if pd.isna(valor) else str(valor)


class Command(BaseCommand):
    help = 'Carga (o recarga) el dataset de sismos en la base de datos.'

    def add_arguments(self, parser):
        parser.add_argument('--csv', default=CSV_URL, help='Ruta o URL del CSV (por defecto, el de GitHub).')

    def handle(self, *args, **opciones):
        self.stdout.write(f'Leyendo {opciones["csv"]} ...')
        df = pd.read_csv(opciones['csv'])
        df['time'] = pd.to_datetime(df['time'], utc=True, errors='coerce', format='mixed')
        df['pais'] = df['place'].apply(extraer_pais_limpio)

        sismos = [
            Sismo(
                usgs_id=fila['id'],
                time=None if pd.isna(fila['time']) else fila['time'].to_pydatetime(),
                año=None if pd.isna(fila['time']) else int(fila['time'].year),
                latitude=_num(fila['latitude']),
                longitude=_num(fila['longitude']),
                depth=_num(fila['depth']),
                mag=_num(fila['mag']),
                mag_type=_txt(fila['magType']),
                nst=_num(fila['nst']),
                gap=_num(fila['gap']),
                dmin=_num(fila['dmin']),
                rms=_num(fila['rms']),
                net=_txt(fila['net']),
                updated=_txt(fila['updated']),
                place=_txt(fila['place']),
                pais=fila['pais'],
                type=_txt(fila['type']),
                status=_txt(fila['status']),
                location_source=_txt(fila['locationSource']),
                mag_source=_txt(fila['magSource']),
            )
            for fila in df.drop_duplicates('id').to_dict('records')
        ]

        with transaction.atomic():
            Sismo.objects.all().delete()
            Sismo.objects.bulk_create(sismos, batch_size=2000)

        self.stdout.write(self.style.SUCCESS(f'{len(sismos)} sismos cargados en la base de datos.'))
