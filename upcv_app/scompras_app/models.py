from asyncio import open_connection
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.urls import reverse
from django.db.models import Sum, Prefetch
from django.db.models.signals import post_save
from django.utils import timezone

class Institucion(models.Model):
    nombre = models.CharField(max_length=255)
    direccion = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20)
    pagina_web = models.URLField(blank=True, null=True)
    logo = models.ImageField(upload_to='logos/', blank=True, null=True)
    logo2 = models.ImageField(upload_to='logos/', blank=True, null=True)

    def __str__(self):
        return self.nombre


# Modelo de Departamento
class Departamento(models.Model):
    id_departamento = models.CharField(max_length=50, unique=True)  # ID personalizado del departamento
    nombre = models.CharField(max_length=255)
    abreviatura = models.CharField(max_length=10, default='Dept')
    descripcion = models.TextField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)  # Fecha de creación automática
    fecha_actualizacion = models.DateTimeField(auto_now=True)  # Fecha de actualización automática
    activo = models.BooleanField(default=True) # Campo para determinar si el departamento está activo
    
    def __str__(self):
        return self.nombre
   
    
class Seccion(models.Model):
    nombre = models.CharField(max_length=255)
    abreviatura = models.CharField(max_length=10, default='Secc')
    descripcion = models.TextField(blank=True, null=True)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE, related_name='secciones')
    activo = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    firmante_nombre = models.CharField(max_length=150, blank=True, null=True)
    firmante_cargo = models.CharField(max_length=150, blank=True, null=True)


    def __str__(self):
        return f'{self.nombre} ({self.departamento.nombre})'


class TipoProcesoCompra(models.Model):
    nombre = models.CharField(max_length=255)
    codigo = models.SlugField(unique=True)
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True, null=True, blank=True)

    def __str__(self):
        return self.nombre


class SubtipoProcesoCompra(models.Model):
    tipo = models.ForeignKey(TipoProcesoCompra, on_delete=models.CASCADE, related_name="subtipos")
    nombre = models.CharField(max_length=255)
    codigo = models.SlugField()
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tipo", "codigo")

    def __str__(self):
        return f"{self.tipo.nombre} - {self.nombre}"


class ProcesoCompraPaso(models.Model):
    tipo = models.ForeignKey(TipoProcesoCompra, on_delete=models.CASCADE, related_name="pasos")
    subtipo = models.ForeignKey(
        SubtipoProcesoCompra,
        on_delete=models.CASCADE,
        related_name="pasos",
        null=True,
        blank=True,
    )
    numero = models.PositiveIntegerField()
    titulo = models.CharField(max_length=255)
    duracion_referencia = models.CharField(max_length=80, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("tipo", "subtipo", "numero")
        ordering = ["tipo", "subtipo", "numero"]

    def __str__(self):
        subtipo = f" - {self.subtipo.nombre}" if self.subtipo else ""
        return f"{self.tipo.nombre}{subtipo} #{self.numero} {self.titulo}"


class SolicitudCompra(models.Model):
    ESTADOS = [
        ('Creada', 'Creada'),
        ('Rechazada', 'Rechazada'),
        ('Finalizada', 'Finalizada'),
    ]

    PRIORIDADES = [
        ('Baja', 'Baja'),
        ('Media', 'Media'),
        ('Alta', 'Alta'),
    ]

    seccion = models.ForeignKey('Seccion', on_delete=models.CASCADE, related_name='solicitudes')
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    descripcion = models.TextField()
    fecha_solicitud = models.DateTimeField(default=timezone.now)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Creada')
    prioridad = models.CharField(max_length=20, choices=PRIORIDADES, default='Media')
    producto = models.ForeignKey('Producto', on_delete=models.CASCADE, null=True, blank=True)
    subproducto = models.ForeignKey('Subproducto', on_delete=models.CASCADE, null=True, blank=True)
    insumos = models.ManyToManyField('Insumo', related_name='solicitudes', blank=True)
    codigo_correlativo = models.CharField(max_length=50, blank=True, null=True, unique=True)
    analista_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes_asignadas",
    )
    tipo_proceso = models.ForeignKey(
        TipoProcesoCompra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes",
    )
    subtipo_proceso = models.ForeignKey(
        SubtipoProcesoCompra,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="solicitudes",
    )
    paso_actual = models.PositiveIntegerField(default=1)
    fecha_asignacion_analista = models.DateTimeField(null=True, blank=True)


    def __str__(self):
        return f'Solicitud #{self.id} - {self.estado}'

    def delete(self, using=None, keep_parents=False):
        cdp_queryset = getattr(self, 'cdps', None)
        if cdp_queryset and cdp_queryset.filter(estado=CDP.Estado.EJECUTADO).exists():
            raise ValidationError('No se puede eliminar una solicitud con CDP ejecutado.')
        if cdp_queryset and cdp_queryset.filter(estado=CDP.Estado.RESERVADO).exists():
            raise ValidationError('Libere los CDP reservados antes de eliminar la solicitud.')
        return super().delete(using=using, keep_parents=keep_parents)




class UsuarioDepartamento(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    seccion = models.ForeignKey(Seccion, on_delete=models.CASCADE, null=True, blank=True)  # nuevo campo

    class Meta:
        unique_together = ('usuario', 'departamento', 'seccion')  # ahora la combinación incluye seccion

    def __str__(self):
        return f'{self.usuario.username} - {self.departamento.nombre} - {self.seccion.nombre if self.seccion else "Sin Sección"}'

 

class FraseMotivacional(models.Model):
    frase = models.CharField(max_length=500)
    personaje = models.CharField(max_length=100)

    def __str__(self):
        return f'{self.personaje}: {self.frase}'
    


def user_directory_path(instance, filename):
    # El archivo se subirá a MEDIA_ROOT/perfil_usuario/<username>/<filename>
    return f'perfil_usuario/{instance.user.username}/{filename}'

class Perfil(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    foto = models.ImageField(upload_to=user_directory_path, null=True, blank=True)
    cargo = models.CharField(max_length=100, blank=True, null=True) 

    def __str__(self):
        return f'Perfil de {self.user.username}'

# Señal: Crear perfil automáticamente cuando se crea un usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created and not hasattr(instance, 'perfil'):
        Perfil.objects.create(user=instance)

@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    from django.db.utils import ProgrammingError, OperationalError
    from scompras_app.models import Perfil

    try:
        if hasattr(instance, 'perfil'):
            instance.perfil.save()
        else:
            Perfil.objects.get_or_create(user=instance)
    except (ProgrammingError, OperationalError):
        # Si la tabla aún no existe (por ejemplo al migrar o primera conexión)
        pass

        

# Modelo de Insumo (para la importación de datos desde Excel)
class Insumo(models.Model):
    renglon = models.IntegerField()
    codigo_insumo = models.CharField(max_length=100)
    nombre = models.CharField(max_length=500)
    caracteristicas = models.TextField(blank=True, null=True)
    nombre_presentacion = models.CharField(max_length=500)
    cantidad_unidad_presentacion = models.CharField(max_length=100)
    codigo_presentacion = models.CharField(max_length=100, unique=True)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.codigo_insumo} - {self.nombre}"


# Modelo para la fecha de insumo (para la importación de datos desde Excel)
class FechaInsumo(models.Model):
    fechainsumo = models.DateField()  

    def __str__(self):
        return f"{self.fechainsumo}"        
    
class InsumoSolicitud(models.Model):
    solicitud = models.ForeignKey(SolicitudCompra, on_delete=models.CASCADE, related_name='insumos_solicitud')
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)  # o la cantidad que necesites
    caracteristica_especial = models.TextField(blank=True, null=True)
    renglon = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        unique_together = ('solicitud', 'insumo')  # para evitar duplicados

# === NUEVO MODELO DE SERVICIOS ===
class Servicio(models.Model):
    concepto = models.CharField(max_length=500)
    renglon = models.CharField(max_length=100)
    caracteristica_especial = models.TextField(blank=True, null=True)
    unidad_medida = models.CharField(max_length=100)
    fecha_actualizacion = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.concepto} ({self.renglon}) - {self.unidad_medida}"


# === RELACIÓN ENTRE SOLICITUD Y SERVICIO ===
class ServicioSolicitud(models.Model):
    solicitud = models.ForeignKey(SolicitudCompra, on_delete=models.CASCADE, related_name='servicios_solicitud')
    servicio = models.ForeignKey(Servicio, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    observacion = models.TextField(blank=True, null=True)
    nombre_override = models.TextField(blank=True, null=True)
    caracteristica_especial = models.TextField(blank=True, null=True)


    def __str__(self):
        return f"Servicio {self.servicio.concepto} en {self.solicitud}"

    

class Producto(models.Model):
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    codigo = models.CharField(max_length=100, unique=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.codigo})"


class Subproducto(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='subproductos')
    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    codigo = models.CharField(max_length=100)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('producto', 'codigo')  # Un subproducto no puede tener el mismo código dentro del mismo producto

    def __str__(self):
        return f"{self.nombre} ({self.codigo}) - Subproducto de {self.producto.nombre}"


class PresupuestoAnual(models.Model):
    anio = models.PositiveIntegerField(unique=True)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-anio']

    def __str__(self):
        return f"Presupuesto {self.anio}" + (" (Activo)" if self.activo else "")

    def clean(self):
        if self.anio < 2000:
            raise ValidationError('El año de presupuesto debe ser igual o posterior a 2000.')

    @classmethod
    def presupuesto_activo(cls):
        return cls.objects.filter(activo=True).first()

    def activar(self):
        """Activa este presupuesto y desactiva los demás de forma atómica."""
        with transaction.atomic():
            PresupuestoAnual.objects.exclude(pk=self.pk).filter(activo=True).update(activo=False)
            if not self.activo:
                self.activo = True
                self.save(update_fields=['activo'])

    def save(self, *args, **kwargs):
        activar = self.activo
        with transaction.atomic():
            super().save(*args, **kwargs)
            if activar:
                PresupuestoAnual.objects.exclude(pk=self.pk).filter(activo=True).update(activo=False)


class PresupuestoRenglon(models.Model):
    presupuesto_anual = models.ForeignKey(PresupuestoAnual, on_delete=models.CASCADE, related_name='renglones')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, null=True, blank=True)
    subproducto = models.ForeignKey(Subproducto, on_delete=models.PROTECT, null=True, blank=True)
    codigo_renglon = models.CharField(max_length=50)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    monto_inicial = models.DecimalField(max_digits=14, decimal_places=2)
    monto_modificado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_reservado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    monto_ejecutado = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['codigo_renglon']
        constraints = [
            models.UniqueConstraint(
                fields=['presupuesto_anual', 'codigo_renglon', 'producto', 'subproducto'],
                name='uniq_renglon_por_producto_subproducto',
            )
        ]

    def __str__(self):
        return f"{self.codigo_renglon} - {self.presupuesto_anual.anio}"

    @property
    def contexto_programatico(self):
        if self.producto and self.subproducto:
            return f"{self.producto.nombre} / {self.subproducto.nombre}"
        if self.producto:
            return self.producto.nombre
        if self.subproducto:
            return self.subproducto.nombre
        return '-'

    @property
    def label_compacto(self):
        descripcion = self.descripcion or '-'
        if not self.producto:
            return f"Renglon {self.codigo_renglon} - {descripcion}"
        etiqueta = f"Renglon {self.codigo_renglon} - {descripcion} / P-{self.producto.codigo}"
        if self.subproducto:
            etiqueta = f"{etiqueta} / SP-{self.subproducto.codigo}"
        return etiqueta

    @property
    def monto_disponible(self):
        return (self.monto_inicial + self.monto_modificado) - (self.monto_reservado + self.monto_ejecutado)

    def clean(self):
        for campo in ['monto_inicial', 'monto_modificado', 'monto_reservado', 'monto_ejecutado']:
            if getattr(self, campo, Decimal('0.00')) < 0:
                raise ValidationError(f'El campo {campo} no puede ser negativo.')
        if self.subproducto and not self.producto:
            self.producto = self.subproducto.producto
        if self.subproducto and self.producto and self.subproducto.producto_id != self.producto_id:
            raise ValidationError('El subproducto debe pertenecer al producto seleccionado.')

    def save(self, *args, **kwargs):
        es_nuevo = self._state.adding
        referencia_kardex = getattr(self, '_kardex_referencia', None)
        omitir_kardex = getattr(self, '_omitir_kardex', False)
        super().save(*args, **kwargs)
        if es_nuevo and not omitir_kardex:
            self._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.CARGA_INICIAL,
                self.monto_inicial,
                Decimal('0.00'),
                referencia_kardex or 'Carga inicial de presupuesto'
            )

    def _registrar_kardex(
        self,
        tipo,
        monto,
        saldo_anterior,
        referencia,
        solicitud=None,
        cdp=None,
        cdo=None,
        transferencia=None,
    ):
        KardexPresupuesto.objects.create(
            presupuesto_renglon=self,
            solicitud=solicitud,
            cdp=cdp,
            cdo=cdo,
            transferencia=transferencia,
            tipo=tipo,
            monto=monto,
            saldo_anterior=saldo_anterior,
            saldo_nuevo=self.monto_disponible,
            referencia=referencia,
        )

    def reservar_monto(self, monto, referencia, solicitud=None, cdp=None):
        if monto <= 0:
            raise ValidationError('El monto a reservar debe ser mayor que cero.')
        with transaction.atomic():
            renglon = PresupuestoRenglon.objects.select_for_update().get(pk=self.pk)
            saldo_anterior = renglon.monto_disponible
            if monto > saldo_anterior:
                raise ValidationError('Monto insuficiente para reservar en este renglón.')
            renglon.monto_reservado += monto
            renglon.save(update_fields=['monto_reservado', 'fecha_actualizacion'])
            renglon.refresh_from_db()
            renglon._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.RESERVA_CDP,
                monto,
                saldo_anterior,
                referencia,
                solicitud=solicitud,
                cdp=cdp,
            )
        self.refresh_from_db()

    def liberar_reserva(self, monto, referencia, solicitud=None, cdp=None):
        if monto <= 0:
            raise ValidationError('El monto a liberar debe ser mayor que cero.')
        with transaction.atomic():
            renglon = PresupuestoRenglon.objects.select_for_update().get(pk=self.pk)
            saldo_anterior = renglon.monto_disponible
            if monto > renglon.monto_reservado:
                raise ValidationError('No se puede liberar más de lo reservado.')
            renglon.monto_reservado -= monto
            renglon.save(update_fields=['monto_reservado', 'fecha_actualizacion'])
            renglon.refresh_from_db()
            renglon._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.LIBERACION_CDP,
                monto,
                saldo_anterior,
                referencia,
                solicitud=solicitud,
                cdp=cdp,
            )
        self.refresh_from_db()

    def ejecutar_monto(self, monto, referencia, solicitud=None, cdp=None, cdo=None):
        if monto <= 0:
            raise ValidationError('El monto a ejecutar debe ser mayor que cero.')
        with transaction.atomic():
            renglon = PresupuestoRenglon.objects.select_for_update().get(pk=self.pk)
            saldo_anterior = renglon.monto_disponible
            if monto > renglon.monto_reservado:
                raise ValidationError('No se puede ejecutar un monto mayor al reservado.')
            renglon.monto_reservado -= monto
            renglon.monto_ejecutado += monto
            renglon.save(update_fields=['monto_reservado', 'monto_ejecutado', 'fecha_actualizacion'])
            renglon.refresh_from_db()
            renglon._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.EJECUCION_CDP,
                monto,
                saldo_anterior,
                referencia,
                solicitud=solicitud,
                cdp=cdp,
                cdo=cdo,
            )
        self.refresh_from_db()


class SubproductoPresupuestoRenglon(models.Model):
    presupuesto_anual = models.ForeignKey(
        PresupuestoAnual,
        on_delete=models.CASCADE,
        related_name='asignaciones_subproductos',
    )
    subproducto = models.ForeignKey(
        Subproducto,
        on_delete=models.CASCADE,
        related_name='asignaciones_presupuesto',
    )
    presupuesto_renglon = models.ForeignKey(
        PresupuestoRenglon,
        on_delete=models.CASCADE,
        related_name='subproducto_renglones',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('presupuesto_anual', 'subproducto', 'presupuesto_renglon')
        verbose_name = 'Asignación de subproducto a renglón'
        verbose_name_plural = 'Asignaciones de subproductos a renglones'

    def __str__(self):
        return (
            f"{self.subproducto} -> {self.presupuesto_renglon.codigo_renglon} "
            f"({self.presupuesto_anual.anio})"
        )

    def clean(self):
        if (
            self.presupuesto_renglon_id
            and self.presupuesto_anual_id
            and self.presupuesto_renglon.presupuesto_anual_id != self.presupuesto_anual_id
        ):
            raise ValidationError(
                'El renglón debe pertenecer al mismo presupuesto anual indicado en la asignación.'
            )


def prefetch_renglones_con_subproductos(queryset):
    return queryset.prefetch_related(
        Prefetch(
            'subproducto_renglones',
            queryset=SubproductoPresupuestoRenglon.objects.select_related(
                'subproducto',
                'subproducto__producto',
                'presupuesto_anual',
            ),
        ),
    )


class KardexPresupuesto(models.Model):
    class TipoMovimiento(models.TextChoices):
        CARGA_INICIAL = 'CARGA_INICIAL', 'Carga inicial'
        TRANSFERENCIA_SALIDA = 'TRANSFERENCIA_SALIDA', 'Transferencia salida'
        TRANSFERENCIA_ENTRADA = 'TRANSFERENCIA_ENTRADA', 'Transferencia entrada'
        RESERVA_CDP = 'RESERVA_CDP', 'Creación de CDP'
        LIBERACION_CDP = 'LIBERACION_CDP', 'Liberación de CDP'
        EJECUCION_CDP = 'EJECUCION_CDP', 'Ejecución presupuestaria'

    presupuesto_renglon = models.ForeignKey(PresupuestoRenglon, on_delete=models.CASCADE, related_name='kardex')
    solicitud = models.ForeignKey(
        'SolicitudCompra',
        on_delete=models.PROTECT,
        related_name='movimientos_kardex',
        null=True,
        blank=True,
        help_text='Referencia contable a la solicitud de compra vinculada (si aplica)'
    )
    cdp = models.ForeignKey(
        'CDP',
        on_delete=models.PROTECT,
        related_name='kardex_movimientos',
        null=True,
        blank=True,
        help_text='Referencia opcional al CDP asociado al movimiento.'
    )
    cdo = models.ForeignKey(
        'CDO',
        on_delete=models.PROTECT,
        related_name='kardex_movimientos',
        null=True,
        blank=True,
        help_text='Referencia opcional al CDO asociado al movimiento.'
    )
    transferencia = models.ForeignKey(
        'TransferenciaPresupuestaria',
        on_delete=models.PROTECT,
        related_name='kardex_movimientos',
        null=True,
        blank=True,
        help_text='Referencia opcional a la transferencia asociada al movimiento.'
    )
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=50, choices=TipoMovimiento.choices)
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_anterior = models.DecimalField(max_digits=14, decimal_places=2)
    saldo_nuevo = models.DecimalField(max_digits=14, decimal_places=2)
    referencia = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Kardex presupuestario'
        verbose_name_plural = 'Kardex presupuestario'

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.fecha:%Y-%m-%d %H:%M}"

    def save(self, *args, **kwargs):
        if self.pk and not self._state.adding:
            raise ValidationError('Los registros de kardex son de solo lectura.')
        return super().save(*args, **kwargs)


class CDP(models.Model):
    class Estado(models.TextChoices):
        RESERVADO = 'RESERVADO', 'Reservado'
        EJECUTADO = 'EJECUTADO', 'Ejecutado'
        LIBERADO = 'LIBERADO', 'Liberado'

    solicitud = models.ForeignKey(SolicitudCompra, on_delete=models.PROTECT, related_name='cdps')
    renglon = models.ForeignKey(PresupuestoRenglon, on_delete=models.PROTECT, related_name='cdps')
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.RESERVADO)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"CDP #{self.id} - {self.estado}"

    def clean(self):
        if self.monto is None or self.monto <= 0:
            raise ValidationError('El monto del CDP debe ser mayor que cero.')
        if self.renglon_id:
            disponible = self.renglon.monto_disponible
            if self._state.adding and self.monto > disponible:
                raise ValidationError('El monto del CDP excede el presupuesto disponible del renglón.')
            presupuesto_activo = PresupuestoAnual.presupuesto_activo()
            if not presupuesto_activo:
                raise ValidationError('No hay presupuesto activo para registrar el CDP.')
            if self.renglon.presupuesto_anual_id != presupuesto_activo.id:
                raise ValidationError('Solo se pueden registrar CDP sobre el presupuesto activo.')
        if self.estado == CDP.Estado.EJECUTADO and self._state.adding:
            raise ValidationError('Un CDP nuevo solo puede crearse en estado Reservado.')

    def save(self, *args, **kwargs):
        if self.pk:
            original = CDP.objects.get(pk=self.pk)
            if original.estado == CDP.Estado.EJECUTADO:
                raise ValidationError('No se puede modificar un CDP ejecutado.')
            if original.estado != self.estado:
                raise ValidationError('Use los métodos de negocio para cambiar el estado del CDP.')
            if any([
                original.monto != self.monto,
                original.renglon_id != self.renglon_id,
                original.solicitud_id != self.solicitud_id,
            ]):
                raise ValidationError('No se permiten ediciones directas sobre el CDP.')
            return super().save(*args, **kwargs)

        with transaction.atomic():
            self.estado = CDP.Estado.RESERVADO
            self.full_clean()
            super().save(*args, **kwargs)
            self.renglon.reservar_monto(
                self.monto,
                referencia=f'CDP #{self.pk} | Solicitud {self.solicitud.codigo_correlativo or self.solicitud_id} - Reserva',
                solicitud=self.solicitud,
                cdp=self,
            )
        return self

    def _actualizar_estado(self, nuevo_estado):
        self.estado = nuevo_estado
        super().save(update_fields=['estado', 'fecha_actualizacion'])

    def liberar(self):
        if self.estado != CDP.Estado.RESERVADO:
            raise ValidationError('Solo se pueden liberar CDP en estado Reservado.')
        if not self.renglon.presupuesto_anual.activo:
            raise ValidationError('Solo se pueden liberar CDP pertenecientes al presupuesto activo.')
        with transaction.atomic():
            self.renglon.liberar_reserva(
                self.monto,
                referencia=f'CDP #{self.pk} | Solicitud {self.solicitud.codigo_correlativo or self.solicitud_id} - Liberación',
                solicitud=self.solicitud,
                cdp=self,
            )
            self._actualizar_estado(CDP.Estado.LIBERADO)

    def ejecutar(self):
        if self.estado != CDP.Estado.RESERVADO:
            raise ValidationError('Solo se pueden ejecutar CDP en estado Reservado.')
        if not self.renglon.presupuesto_anual.activo:
            raise ValidationError('Solo se pueden ejecutar CDP pertenecientes al presupuesto activo.')
        with transaction.atomic():
            cdo = CDO.objects.create(cdp=self, monto=self.monto)
            self.renglon.ejecutar_monto(
                self.monto,
                referencia=f'CDP #{self.pk} | Solicitud {self.solicitud.codigo_correlativo or self.solicitud_id} - Ejecución',
                solicitud=self.solicitud,
                cdp=self,
                cdo=cdo,
            )
            self._actualizar_estado(CDP.Estado.EJECUTADO)
            return cdo

    def delete(self, using=None, keep_parents=False):
        if self.estado == CDP.Estado.EJECUTADO:
            raise ValidationError('No se puede eliminar un CDP ejecutado.')
        if self.estado == CDP.Estado.RESERVADO:
            raise ValidationError('Libere el CDP antes de eliminarlo.')
        return super().delete(using=using, keep_parents=keep_parents)


class CDO(models.Model):
    cdp = models.OneToOneField(CDP, on_delete=models.PROTECT, related_name='cdo')
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"CDO de CDP #{self.cdp_id}"

    def clean(self):
        if self.monto is None or self.monto <= 0:
            raise ValidationError('El monto del CDO debe ser mayor que cero.')
        if self.cdp_id and self.monto != self.cdp.monto:
            raise ValidationError('El monto del CDO debe coincidir con el monto reservado en el CDP.')
        if self.cdp_id and self.cdp.estado != CDP.Estado.RESERVADO:
            raise ValidationError('Solo se pueden generar CDO a partir de CDP reservados.')

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Los CDO no se pueden editar.')
        self.full_clean()
        return super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        raise ValidationError('Los CDO no pueden eliminarse.')


class TransferenciaPresupuestaria(models.Model):
    presupuesto_anual = models.ForeignKey(PresupuestoAnual, on_delete=models.PROTECT, related_name='transferencias')
    renglon_origen = models.ForeignKey(PresupuestoRenglon, on_delete=models.PROTECT, related_name='transferencias_salida')
    renglon_destino = models.ForeignKey(PresupuestoRenglon, on_delete=models.PROTECT, related_name='transferencias_entrada')
    monto = models.DecimalField(max_digits=14, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"Transferencia {self.presupuesto_anual.anio} - {self.monto}"

    def clean(self):
        if self.monto is None or self.monto <= 0:
            raise ValidationError('El monto de la transferencia debe ser mayor que cero.')
        if self.renglon_origen_id and self.renglon_destino_id:
            if self.renglon_origen_id == self.renglon_destino_id:
                raise ValidationError('El renglón origen y destino deben ser diferentes.')
            if self.renglon_origen.presupuesto_anual_id != self.renglon_destino.presupuesto_anual_id:
                raise ValidationError('Las transferencias solo pueden realizarse entre renglones del mismo año.')

        presupuesto_activo = PresupuestoAnual.presupuesto_activo()
        if not presupuesto_activo:
            raise ValidationError('No hay presupuesto activo para realizar transferencias.')
        if self.presupuesto_anual_id and self.presupuesto_anual_id != presupuesto_activo.id:
            raise ValidationError('Solo se permiten transferencias en el presupuesto activo.')
        if self.renglon_origen_id and self.renglon_origen.presupuesto_anual_id != presupuesto_activo.id:
            raise ValidationError('El renglón origen debe pertenecer al presupuesto activo.')
        if self.renglon_destino_id and self.renglon_destino.presupuesto_anual_id != presupuesto_activo.id:
            raise ValidationError('El renglón destino debe pertenecer al presupuesto activo.')

        if self.pk:
            raise ValidationError('Las transferencias no pueden editarse una vez creadas.')

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError('Las transferencias no pueden editarse una vez creadas.')
        if not self.presupuesto_anual_id:
            activo = PresupuestoAnual.presupuesto_activo()
            if not activo:
                raise ValidationError('No hay presupuesto activo para realizar transferencias.')
            self.presupuesto_anual = activo
        self.full_clean()
        with transaction.atomic():
            origen = PresupuestoRenglon.objects.select_for_update().get(pk=self.renglon_origen_id)
            destino = PresupuestoRenglon.objects.select_for_update().get(pk=self.renglon_destino_id)
            saldo_origen_antes = origen.monto_disponible
            saldo_destino_antes = destino.monto_disponible
            if self.monto > saldo_origen_antes:
                raise ValidationError('El monto a transferir excede el disponible del renglón origen.')
            origen.monto_modificado -= self.monto
            destino.monto_modificado += self.monto
            origen.save(update_fields=['monto_modificado', 'fecha_actualizacion'])
            destino.save(update_fields=['monto_modificado', 'fecha_actualizacion'])
            super().save(*args, **kwargs)
            origen.refresh_from_db()
            destino.refresh_from_db()
            origen._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.TRANSFERENCIA_SALIDA,
                -self.monto,
                saldo_origen_antes,
                f'Transferencia #{self.pk} hacia {destino.codigo_renglon} - Presupuesto {self.presupuesto_anual.anio}',
                transferencia=self,
            )
            destino._registrar_kardex(
                KardexPresupuesto.TipoMovimiento.TRANSFERENCIA_ENTRADA,
                self.monto,
                saldo_destino_antes,
                f'Transferencia #{self.pk} desde {origen.codigo_renglon} - Presupuesto {self.presupuesto_anual.anio}',
                transferencia=self,
            )
        return self


class SolicitudPasoEstado(models.Model):
    solicitud = models.ForeignKey(SolicitudCompra, on_delete=models.CASCADE, related_name="pasos_estado")
    paso = models.ForeignKey(ProcesoCompraPaso, on_delete=models.CASCADE)
    completado = models.BooleanField(default=False)
    fecha_completado = models.DateTimeField(null=True, blank=True)
    completado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    nota = models.TextField(blank=True)

    class Meta:
        unique_together = ("solicitud", "paso")

    def __str__(self):
        return f"{self.solicitud_id} - {self.paso_id}"


class ConstanciaDisponibilidad(models.Model):
    solicitud = models.OneToOneField(
        SolicitudCompra,
        on_delete=models.CASCADE,
        related_name='constancia_disp',
    )
    numero = models.PositiveIntegerField(unique=True)
    ejercicio_fiscal = models.PositiveIntegerField()
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    creado_por = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True)

    class Meta:
        ordering = ['-fecha_creacion', '-numero']

    def __str__(self):
        return f"Constancia {self.numero} - Solicitud {self.solicitud_id}"
    
