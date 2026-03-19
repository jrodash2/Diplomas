from django.db import migrations


def seed_procesos(apps, schema_editor):
    TipoProcesoCompra = apps.get_model('scompras_app', 'TipoProcesoCompra')
    SubtipoProcesoCompra = apps.get_model('scompras_app', 'SubtipoProcesoCompra')
    ProcesoCompraPaso = apps.get_model('scompras_app', 'ProcesoCompraPaso')

    tipos = [
        ('baja-cuantia', 'Baja cuantía'),
        ('compra-directa', 'Compra directa'),
        ('cotizacion', 'Cotización'),
        ('contrato-abierto', 'Contrato abierto'),
        ('licitacion', 'Licitación'),
    ]

    pasos_iniciales = [
        (1, 'Recepción de solicitud', '1 día'),
        (2, 'Análisis y validación', '2 días'),
        (3, 'Gestión de compra', '3 días'),
        (4, 'Adjudicación', '2 días'),
        (5, 'Cierre y entrega', '1 día'),
    ]

    tipos_map = {}
    for codigo, nombre in tipos:
        tipo, _ = TipoProcesoCompra.objects.get_or_create(
            codigo=codigo,
            defaults={'nombre': nombre, 'activo': True},
        )
        if tipo.nombre != nombre:
            tipo.nombre = nombre
            tipo.save(update_fields=['nombre'])
        tipos_map[codigo] = tipo

    baja_cuantia = tipos_map.get('baja-cuantia')
    if baja_cuantia:
        SubtipoProcesoCompra.objects.get_or_create(
            tipo=baja_cuantia,
            codigo='tramite-cheque',
            defaults={'nombre': 'Trámite de cheque', 'activo': True},
        )
        SubtipoProcesoCompra.objects.get_or_create(
            tipo=baja_cuantia,
            codigo='acreditamiento-cuenta',
            defaults={'nombre': 'Acreditamiento a cuenta', 'activo': True},
        )

    for tipo in tipos_map.values():
        for numero, titulo, duracion in pasos_iniciales:
            ProcesoCompraPaso.objects.get_or_create(
                tipo=tipo,
                subtipo=None,
                numero=numero,
                defaults={'titulo': titulo, 'duracion_referencia': duracion, 'activo': True},
            )


def unseed_procesos(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('scompras_app', '0025_procesos_compra'),
    ]

    operations = [
        migrations.RunPython(seed_procesos, unseed_procesos),
    ]
