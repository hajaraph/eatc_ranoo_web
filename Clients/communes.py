from django.db import models


class Region(models.Model):
    id_region = models.BigAutoField(primary_key=True)
    region = models.CharField(max_length=20, blank=False)


class Commune(models.Model):
    cp_commune = models.CharField(max_length=10, primary_key=True)
    commune = models.CharField(max_length=30, blank=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=False)
