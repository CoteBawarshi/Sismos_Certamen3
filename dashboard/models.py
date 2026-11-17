from django.db import models


class Sismo(models.Model):
    """Un sismo de magnitud >= 5 del catálogo USGS (1926-2026).

    Los datos se cargan desde el CSV original con:
        python manage.py cargar_sismos
    """
    usgs_id = models.CharField('ID USGS', max_length=40, unique=True)
    time = models.DateTimeField('Fecha y hora (UTC)', null=True, db_index=True)
    año = models.IntegerField('Año', null=True, db_index=True)
    latitude = models.FloatField('Latitud', null=True)
    longitude = models.FloatField('Longitud', null=True)
    depth = models.FloatField('Profundidad (km)', null=True)
    mag = models.FloatField('Magnitud', null=True, db_index=True)
    mag_type = models.CharField('Tipo de magnitud', max_length=10, blank=True)
    nst = models.FloatField('Estaciones', null=True)
    gap = models.FloatField('Brecha azimutal', null=True)
    dmin = models.FloatField('Distancia mínima', null=True)
    rms = models.FloatField('RMS', null=True)
    net = models.CharField('Red', max_length=10, blank=True)
    updated = models.CharField('Actualizado', max_length=40, blank=True)
    place = models.CharField('Lugar', max_length=200, blank=True)
    pais = models.CharField('País / Región', max_length=100, blank=True, db_index=True)
    type = models.CharField('Tipo de evento', max_length=40, blank=True)
    status = models.CharField('Estado', max_length=20, blank=True)
    location_source = models.CharField('Fuente ubicación', max_length=10, blank=True)
    mag_source = models.CharField('Fuente magnitud', max_length=10, blank=True)

    class Meta:
        ordering = ['-time']
        verbose_name = 'Sismo'
        verbose_name_plural = 'Sismos'

    def __str__(self):
        return f'{self.usgs_id} M{self.mag} {self.pais}'
