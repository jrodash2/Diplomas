from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('scompras_app', '0024_constanciadisponibilidad'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='TipoProcesoCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('codigo', models.SlugField(unique=True)),
                ('activo', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(blank=True, null=True, auto_now_add=True)),
                ('updated_at', models.DateTimeField(blank=True, null=True, auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubtipoProcesoCompra',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre', models.CharField(max_length=255)),
                ('codigo', models.SlugField()),
                ('activo', models.BooleanField(default=True)),
                ('tipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='subtipos', to='scompras_app.tipoprocesocompra')),
            ],
            options={
                'unique_together': {('tipo', 'codigo')},
            },
        ),
        migrations.CreateModel(
            name='ProcesoCompraPaso',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.PositiveIntegerField()),
                ('titulo', models.CharField(max_length=255)),
                ('duracion_referencia', models.CharField(blank=True, max_length=80)),
                ('activo', models.BooleanField(default=True)),
                ('subtipo', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pasos', to='scompras_app.subtipoprocesocompra')),
                ('tipo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pasos', to='scompras_app.tipoprocesocompra')),
            ],
            options={
                'ordering': ['tipo', 'subtipo', 'numero'],
                'unique_together': {('tipo', 'subtipo', 'numero')},
            },
        ),
        migrations.AddField(
            model_name='solicitudcompra',
            name='analista_asignado',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes_asignadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='solicitudcompra',
            name='fecha_asignacion_analista',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='solicitudcompra',
            name='paso_actual',
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddField(
            model_name='solicitudcompra',
            name='subtipo_proceso',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes', to='scompras_app.subtipoprocesocompra'),
        ),
        migrations.AddField(
            model_name='solicitudcompra',
            name='tipo_proceso',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='solicitudes', to='scompras_app.tipoprocesocompra'),
        ),
        migrations.CreateModel(
            name='SolicitudPasoEstado',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('completado', models.BooleanField(default=False)),
                ('fecha_completado', models.DateTimeField(blank=True, null=True)),
                ('nota', models.TextField(blank=True)),
                ('completado_por', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('paso', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='scompras_app.procesocomprapaso')),
                ('solicitud', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pasos_estado', to='scompras_app.solicitudcompra')),
            ],
            options={
                'unique_together': {('solicitud', 'paso')},
            },
        ),
    ]
