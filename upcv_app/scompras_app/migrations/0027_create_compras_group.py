from django.db import migrations


BLOQUEADOS = (
    "presupuesto",
    "renglon",
    "cdp",
    "cdo",
    "kardex",
    "constanciadisponibilidad",
)


def crear_o_actualizar_grupo_compras(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    presupuesto, _ = Group.objects.get_or_create(name="PRESUPUESTO")
    compras, _ = Group.objects.get_or_create(name="COMPRAS")

    # Clonar permisos actuales de PRESUPUESTO
    compras.permissions.set(presupuesto.permissions.all())

    # Remover cualquier permiso de presupuesto/CDP/CDO
    perms_a_remover = []
    for perm in Permission.objects.select_related("content_type").all():
        codename = (perm.codename or "").lower()
        model = (perm.content_type.model or "").lower()
        if any(token in codename or token in model for token in BLOQUEADOS):
            perms_a_remover.append(perm)

    if perms_a_remover:
        compras.permissions.remove(*perms_a_remover)


def eliminar_grupo_compras(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="COMPRAS").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("scompras_app", "0026_seed_procesos_compra"),
    ]

    operations = [
        migrations.RunPython(crear_o_actualizar_grupo_compras, eliminar_grupo_compras),
    ]
