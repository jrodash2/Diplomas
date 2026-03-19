from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('scompras_app', '0023_create_presupuesto_group'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConstanciaDisponibilidad',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField(unique=True)),
                ('ejercicio_fiscal', models.PositiveIntegerField()),
                ('fecha_creacion', models.DateTimeField(auto_now_add=True)),
                ('creado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ('solicitud', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='constancia_disp', to='scompras_app.solicitudcompra')),
            ],
            options={
                'ordering': ['-fecha_creacion', '-numero'],
            },
        ),
    ]
