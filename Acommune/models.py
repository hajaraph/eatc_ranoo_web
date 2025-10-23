from django.db import models


class Province(models.Model):
    id_province = models.BigAutoField(primary_key=True)
    province = models.CharField(max_length=50, blank=False, null=False)

    class Meta:
        ordering = ['province']

    def __str__(self):
        return self.province

class Region(models.Model):
    id_region = models.BigAutoField(primary_key=True)
    region = models.CharField(max_length=20, blank=False)
    province = models.ForeignKey(Province, on_delete=models.CASCADE, blank=False, null=False)

    def __str__(self):
        return self.province.province + " " + self.region


class Commune(models.Model):
    cp_commune = models.CharField(max_length=10, primary_key=True)
    commune = models.CharField(max_length=30, blank=False)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, blank=False)

    def __str__(self):
        return self.region.__str__() + " " + self.commune
