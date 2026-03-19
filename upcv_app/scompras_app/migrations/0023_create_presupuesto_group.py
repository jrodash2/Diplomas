from django.db import migrations


def crear_grupo_presupuesto(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.get_or_create(name="PRESUPUESTO")


def eliminar_grupo_presupuesto(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="PRESUPUESTO").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("scompras_app", "0022_serviciosolicitud_nombre_override"),
    ]

    operations = [
        migrations.RunPython(crear_grupo_presupuesto, eliminar_grupo_presupuesto),
    ]
