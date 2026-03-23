from django.db import migrations, models


def build_abbreviation(name, fallback):
    words = [word for word in str(name or "").replace("-", " ").split() if word]
    if words:
        initials = "".join(word[0] for word in words if word[0].isalnum()).upper()
        compact = "".join(char for char in initials if char.isalnum())[:10]
        if compact:
            return compact
    return fallback


def seed_location_abbreviations(apps, schema_editor):
    UbicacionDiploma = apps.get_model("diplomas_app", "UbicacionDiploma")
    used = set()
    for ubicacion in UbicacionDiploma.objects.order_by("id"):
        base = build_abbreviation(ubicacion.nombre, f"UBI{ubicacion.id}")
        candidate = base
        suffix = 1
        while candidate in used:
            suffix_text = str(suffix)
            candidate = f"{base[: max(0, 10 - len(suffix_text))]}{suffix_text}"
            suffix += 1
        used.add(candidate)
        ubicacion.abreviatura = candidate
        ubicacion.save(update_fields=["abreviatura"])


class Migration(migrations.Migration):

    dependencies = [
        ("diplomas_app", "0008_cursoempleado_observaciones_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="ubicaciondiploma",
            name="abreviatura",
            field=models.CharField(blank=True, max_length=10, null=True),
        ),
        migrations.RunPython(seed_location_abbreviations, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="ubicaciondiploma",
            name="abreviatura",
            field=models.CharField(max_length=10, unique=True),
        ),
    ]
