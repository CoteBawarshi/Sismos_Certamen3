from django.contrib import admin

from .models import Sismo


@admin.register(Sismo)
class SismoAdmin(admin.ModelAdmin):
    list_display = ('usgs_id', 'time', 'mag', 'depth', 'pais')
    list_filter = ('pais',)
    search_fields = ('usgs_id', 'place', 'pais')
