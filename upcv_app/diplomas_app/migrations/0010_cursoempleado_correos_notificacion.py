from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("diplomas_app", "0009_ubicaciondiploma_abreviatura"),
    ]

    operations = [
        migrations.AddField(
            model_name="cursoempleado",
            name="correo_finalizacion_enviado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cursoempleado",
            name="correo_inscripcion_enviado_en",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="cursoempleado",
            name="ultimo_error_correo_finalizacion",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="cursoempleado",
            name="ultimo_error_correo_inscripcion",
            field=models.TextField(blank=True, default=""),
        ),
    ]
