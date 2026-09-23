from django.db import migrations


def normalize_vehicle_type_names(apps, schema_editor):
    VehicleType = apps.get_model("cars", "VehicleType")

    for contains, final_name in (("car", "Carro"), ("bike", "Moto"), ("moto", "Moto")):
        item = VehicleType.objects.filter(name__icontains=contains).first()
        if item and item.name != final_name:
            existing = VehicleType.objects.filter(name=final_name).exclude(pk=item.pk).first()
            if existing is None:
                item.name = final_name
                item.save(update_fields=("name",))


class Migration(migrations.Migration):
    dependencies = [("cars", "0007_remove_bikeimage_bike_remove_car_brand_and_more")]

    operations = [
        migrations.RunPython(normalize_vehicle_type_names, migrations.RunPython.noop),
    ]
