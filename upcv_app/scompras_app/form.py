from django import forms
from django.contrib.auth.models import User, Group
from django.forms import CheckboxInput, DateInput, inlineformset_factory, modelformset_factory
from django.core.exceptions import ValidationError
from django.utils.text import slugify


from .models import (
    FechaInsumo,
    Insumo,
    Perfil,
    Departamento,
    Seccion,
    SolicitudCompra,
    Producto,
    Subproducto,
    UsuarioDepartamento,
    Institucion,
    CDP,
    PresupuestoRenglon,
    PresupuestoAnual,
    TransferenciaPresupuestaria,
    TipoProcesoCompra,
    SubtipoProcesoCompra,
    ProcesoCompraPaso,
)

from django.db.models import Sum, F, Value
from django.db.models.functions import Coalesce



from django import forms
from .models import Institucion

from django.core.exceptions import ValidationError

class InstitucionForm(forms.ModelForm):
    pagina_web = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text='Ingrese URL que comience con www., sin http/https.'
    )

    class Meta:
        model = Institucion
        fields = ['nombre', 'direccion', 'telefono', 'pagina_web', 'logo', 'logo2']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'direccion': forms.TextInput(attrs={'class': 'form-control'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            # 'pagina_web': forms.URLInput(attrs={'class': 'form-control'}),  # quitamos este
            'logo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'logo2': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }

    def clean_pagina_web(self):
        url = self.cleaned_data.get('pagina_web')
        if url:
            if not url.startswith('www.'):
                raise ValidationError('La URL debe comenzar con "www."')
            # Añadimos http:// para que sea una URL válida
            url = 'http://' + url
        return url



from django import forms
from django.contrib.auth.models import User, Group
from .models import Perfil

class UserCreateForm(forms.ModelForm):
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        required=True,
        label="Confirmar Contraseña"
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )
    cargo = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('new_password')
        confirm = cleaned_data.get('confirm_password')

        if password != confirm:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get('new_password')
        user.set_password(password)

        if commit:
            user.save()
            # Asignar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])

            # Crear perfil
            cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')
            Perfil.objects.update_or_create(
                user=user,
                defaults={'cargo': cargo, 'foto': foto}
            )

        return user

class UserEditForm(forms.ModelForm):
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label="Grupo",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    cargo = forms.CharField(
        max_length=100,
        required=False,
        label="Cargo",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    foto = forms.ImageField(
        required=False,
        label="Foto de perfil",
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['username'].required = False

        # Cargar valores iniciales del perfil (cargo y foto)
        if self.instance and self.instance.pk:
            perfil = getattr(self.instance, 'perfil', None)
            if perfil:
                self.fields['cargo'].initial = perfil.cargo
                self.fields['foto'].initial = perfil.foto

            groups = self.instance.groups.all()
            if groups.exists():
                self.fields['group'].initial = groups.first()

    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            # Actualizar grupo
            group = self.cleaned_data.get('group')
            if group:
                user.groups.set([group])
            else:
                user.groups.clear()

            # Actualizar perfil
            perfil, created = Perfil.objects.get_or_create(user=user)
            perfil.cargo = self.cleaned_data.get('cargo')
            foto = self.cleaned_data.get('foto')

            if foto:
                perfil.foto = foto

            perfil.save()

        return user


class TipoProcesoCompraForm(forms.ModelForm):
    class Meta:
        model = TipoProcesoCompra
        fields = ["nombre", "codigo", "activo"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not codigo and nombre:
            codigo = slugify(nombre)
        if not codigo:
            raise ValidationError("El código es obligatorio.")
        qs = TipoProcesoCompra.objects.filter(codigo=codigo)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise ValidationError("Ya existe un tipo con este código.")
        return codigo


class SubtipoProcesoCompraForm(forms.ModelForm):
    class Meta:
        model = SubtipoProcesoCompra
        fields = ["tipo", "nombre", "codigo", "activo"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, tipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tipo:
            self.fields["tipo"].initial = tipo
            self.fields["tipo"].widget = forms.HiddenInput()

    def clean_codigo(self):
        codigo = (self.cleaned_data.get("codigo") or "").strip()
        nombre = (self.cleaned_data.get("nombre") or "").strip()
        if not codigo and nombre:
            codigo = slugify(nombre)
        if not codigo:
            raise ValidationError("El código es obligatorio.")
        tipo = self.cleaned_data.get("tipo") or self.instance.tipo
        if tipo:
            qs = SubtipoProcesoCompra.objects.filter(tipo=tipo, codigo=codigo)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un subtipo con este código para el tipo seleccionado.")
        return codigo


class ProcesoCompraPasoForm(forms.ModelForm):
    class Meta:
        model = ProcesoCompraPaso
        fields = ["tipo", "subtipo", "numero", "titulo", "duracion_referencia", "activo"]
        widgets = {
            "tipo": forms.Select(attrs={"class": "form-select"}),
            "subtipo": forms.Select(attrs={"class": "form-select"}),
            "numero": forms.NumberInput(attrs={"class": "form-control", "min": 1}),
            "titulo": forms.TextInput(attrs={"class": "form-control"}),
            "duracion_referencia": forms.TextInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, tipo=None, subtipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tipo:
            self.fields["tipo"].initial = tipo
            self.fields["tipo"].widget = forms.HiddenInput()
            self.fields["subtipo"].queryset = SubtipoProcesoCompra.objects.filter(tipo=tipo)
        if subtipo:
            self.fields["subtipo"].initial = subtipo
            self.fields["subtipo"].widget = forms.HiddenInput()

    def clean_numero(self):
        numero = self.cleaned_data.get("numero")
        if numero is None or numero < 1:
            raise ValidationError("El número de paso debe ser mayor o igual a 1.")
        return numero

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get("tipo") or self.instance.tipo
        subtipo = cleaned_data.get("subtipo") or self.instance.subtipo
        numero = cleaned_data.get("numero")
        if tipo and numero:
            qs = ProcesoCompraPaso.objects.filter(tipo=tipo, subtipo=subtipo, numero=numero)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError("Ya existe un paso con este número para el tipo/subtipo seleccionado.")
        return cleaned_data



class DepartamentoForm(forms.ModelForm):
    class Meta:
        model = Departamento
        fields = ['id_departamento', 'nombre', 'abreviatura', 'descripcion']  # <-- agregado 'abreviatura'
        widgets = {
            'id_departamento': forms.TextInput(attrs={'placeholder': 'ID del departamento', 'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre del departamento', 'class': 'form-control'}),
            'abreviatura': forms.TextInput(attrs={'placeholder': 'Abreviatura del departamento', 'class': 'form-control'}),  # <-- nuevo widget
            'descripcion': forms.Textarea(attrs={'placeholder': 'Descripción del departamento', 'rows': 4, 'cols': 40, 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super(DepartamentoForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

class SeccionForm(forms.ModelForm):
    class Meta:
        model = Seccion
        fields = [
            'nombre',
            'abreviatura',
            'descripcion',
            'departamento',
            'firmante_nombre',
            'firmante_cargo',
            'activo',
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'placeholder': 'Nombre de la Sección', 'class': 'form-control'}),
            'abreviatura': forms.TextInput(attrs={'placeholder': 'Abreviatura', 'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'placeholder': 'Descripción', 'rows': 3, 'class': 'form-control'}),
            'departamento': forms.Select(attrs={'class': 'form-select'}),
            'firmante_nombre': forms.TextInput(attrs={'placeholder': 'Nombre del firmante', 'class': 'form-control'}),
            'firmante_cargo': forms.TextInput(attrs={'placeholder': 'Cargo del firmante', 'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'firmante_nombre': 'Nombre del firmante',
            'firmante_cargo': 'Cargo del firmante',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['firmante_nombre'].required = True
        self.fields['firmante_cargo'].required = True

    def clean(self):
        cleaned_data = super().clean()
        for field in ('firmante_nombre', 'firmante_cargo'):
            value = cleaned_data.get(field, '')
            if value is not None:
                value = value.strip()
            if not value:
                self.add_error(field, 'Este campo es obligatorio.')
            cleaned_data[field] = value
        return cleaned_data

class UserForm(forms.ModelForm):
    new_password = forms.CharField(
        required=True, 
        widget=forms.PasswordInput, 
        label="Contraseña"
    )
    confirm_password = forms.CharField(
        required=True, 
        widget=forms.PasswordInput, 
        label="Confirmar Contraseña"
    )
    group = forms.ModelChoiceField(queryset=Group.objects.all(), required=True, label="Grupo")
    foto = forms.ImageField(required=False, label="Foto de perfil")
    cargo = forms.CharField(required=False, label="Cargo", widget=forms.TextInput(attrs={'class': 'form-control'}))  # nuevo campo cargo

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def __init__(self, *args, **kwargs):
        super(UserForm, self).__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

        # Mostrar foto y cargo existentes si está editando
        if self.instance.pk:
            try:
                self.fields['foto'].initial = self.instance.perfil.foto
                self.fields['cargo'].initial = self.instance.perfil.cargo  # inicializamos cargo
            except Perfil.DoesNotExist:
                pass

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise ValidationError("Las contraseñas no coinciden.")
        
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)

        if self.cleaned_data.get("new_password"):
            user.set_password(self.cleaned_data["new_password"])

        if commit:
            user.save()
            user.groups.set([self.cleaned_data['group']])
            # Guardar o crear perfil
            foto = self.cleaned_data.get('foto')
            cargo = self.cleaned_data.get('cargo')  # obtener valor cargo
            perfil, created = Perfil.objects.get_or_create(user=user)
            if foto:
                perfil.foto = foto
            perfil.cargo = cargo  # guardamos cargo
            perfil.save()

        return user

            
from django import forms
from django.contrib.auth.models import User
from scompras_app.models import UsuarioDepartamento, Departamento, Seccion


class UsuarioDepartamentoForm(forms.Form):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.all().order_by('username'),
        label="Usuario (Tickets)",
        required=True
    )


    departamento = forms.ModelChoiceField(
        queryset=Departamento.objects.all(),
        required=True
    )

    seccion = forms.ModelChoiceField(
        queryset=Seccion.objects.none(),
        required=False
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Etiqueta bonita
        self.fields['usuario'].label_from_instance = (
            lambda u: f"{u.first_name} {u.last_name} ({u.username})"
        )

        # Estilos
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})

        # Cargar secciones según dep seleccionado
        if 'departamento' in self.data:
            try:
                dep_id = int(self.data.get('departamento'))
                self.fields['seccion'].queryset = Seccion.objects.filter(
                    departamento_id=dep_id
                ).order_by("nombre")
            except:
                pass


        
class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['foto']
        widgets = {
            'foto': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
  
from django import forms
from .models import SolicitudCompra, Subproducto

class SolicitudCompraForm(forms.ModelForm):
    class Meta:
        model = SolicitudCompra
        # En edición no se expone codigo_correlativo para evitar regeneración accidental.
        fields = ['descripcion', 'producto', 'subproducto', 'prioridad']
        widgets = {
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'producto': forms.Select(attrs={'class': 'form-control', 'id': 'id_producto'}),
            'subproducto': forms.Select(attrs={'class': 'form-control', 'id': 'id_subproducto'}),
           
            'prioridad': forms.Select(attrs={'class': 'form-control'}),
            'fecha_solicitud': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
      
        self.fields['prioridad'].choices = SolicitudCompra.PRIORIDADES
        self.fields['subproducto'].queryset = Subproducto.objects.none()

        # Para el autollenado de subproductos según el producto seleccionado
        if 'producto' in self.data:
            try:
                producto_id = int(self.data.get('producto'))
                self.fields['subproducto'].queryset = Subproducto.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.producto:
            self.fields['subproducto'].queryset = self.instance.producto.subproductos.all()


class SolicitudCompraFormcrear(forms.ModelForm):
    class Meta:
        model = SolicitudCompra
        fields = ['descripcion', 'producto', 'subproducto', 'prioridad']
        widgets = {
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'producto': forms.Select(attrs={'class': 'form-control', 'id': 'id_producto'}),
            'subproducto': forms.Select(attrs={'class': 'form-control', 'id': 'id_subproducto'}),
            'estado': forms.Select(attrs={'class': 'form-control'}),
            'prioridad': forms.Select(attrs={'class': 'form-control'}),
         
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
       
        self.fields['prioridad'].choices = SolicitudCompra.PRIORIDADES
        self.fields['subproducto'].queryset = Subproducto.objects.none()

        # Para el autollenado de subproductos según el producto seleccionado
        if 'producto' in self.data:
            try:
                producto_id = int(self.data.get('producto'))
                self.fields['subproducto'].queryset = Subproducto.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.producto:
            self.fields['subproducto'].queryset = self.instance.producto.subproductos.all()



class ExcelUploadForm(forms.Form):
    archivo_excel = forms.FileField()

    def __init__(self, *args, **kwargs):
        super(ExcelUploadForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            # Si es tipo FileField, normalmente se usa 'form-control' o 'form-control-file'
            css_class = 'form-control'
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + f' {css_class}'

class InsumoForm(forms.ModelForm):
    class Meta:
        model = Insumo
        fields = ['renglon', 'codigo_insumo', 'nombre', 'caracteristicas', 
                  'nombre_presentacion', 'cantidad_unidad_presentacion', 
                  'codigo_presentacion', 'fecha_actualizacion']
        widgets = {
            'fecha_actualizacion': forms.DateTimeInput(attrs={'type': 'datetime-local'})  # Usamos el widget para una entrada de fecha y hora
        }

class FechaInsumoForm(forms.ModelForm):
    class Meta:
        model = FechaInsumo
        fields = ['fechainsumo']
        widgets = {
            'fechainsumo': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super(FechaInsumoForm, self).__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class CDPForm(forms.ModelForm):
    def __init__(self, solicitud, *args, **kwargs):
        self.solicitud = solicitud
        super().__init__(*args, **kwargs)
        activo = PresupuestoAnual.presupuesto_activo()
        queryset = PresupuestoRenglon.objects.select_related(
            'presupuesto_anual',
            'producto',
            'subproducto',
        ).order_by('codigo_renglon')
        if activo:
            queryset = queryset.filter(presupuesto_anual=activo)
        else:
            queryset = queryset.none()

        self.presupuesto_activo = activo
        self.fields['renglon'].queryset = queryset
        self.fields['renglon'].label_from_instance = (
            lambda obj: f"{obj.label_compacto} / Disponible: {obj.monto_disponible}"
        )
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

    class Meta:
        model = CDP
        fields = ['renglon', 'monto']
        widgets = {
            'monto': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        renglon = cleaned_data.get('renglon')
        monto = cleaned_data.get('monto')

        if not self.solicitud:
            raise ValidationError('Debe asociar la solicitud para crear el CDP.')

        if self.solicitud.cdps.filter(cdo__isnull=False).exists():
            raise ValidationError('La solicitud ya tiene un CDO; no se pueden crear nuevos CDP.')

        if renglon and monto is not None:
            if monto <= 0:
                raise ValidationError('El monto debe ser mayor que cero.')
            if not self.presupuesto_activo:
                raise ValidationError('No hay presupuesto activo para registrar el CDP.')
            if renglon.presupuesto_anual_id != self.presupuesto_activo.id:
                raise ValidationError('El renglón seleccionado no pertenece al presupuesto activo.')
            if monto > renglon.monto_disponible:
                raise ValidationError('El monto del CDP excede la disponibilidad del renglón.')

        return cleaned_data


class PresupuestoAnualForm(forms.ModelForm):
    class Meta:
        model = PresupuestoAnual
        fields = ['anio', 'descripcion']
        widgets = {
            'anio': forms.NumberInput(attrs={'class': 'form-control', 'min': '2000'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_anio(self):
        anio = self.cleaned_data.get('anio')
        if anio is None or anio < 2000:
            raise ValidationError('El año debe ser 2000 o superior.')
        if PresupuestoAnual.objects.exclude(pk=self.instance.pk).filter(anio=anio).exists():
            raise ValidationError('Ya existe un presupuesto para este año.')
        return anio


class PresupuestoRenglonForm(forms.ModelForm):
    class Meta:
        model = PresupuestoRenglon
        fields = ['producto', 'subproducto', 'codigo_renglon', 'descripcion', 'monto_inicial']
        widgets = {
            'producto': forms.Select(attrs={'class': 'form-control', 'id': 'id_producto'}),
            'subproducto': forms.Select(attrs={'class': 'form-control', 'id': 'id_subproducto'}),
            'codigo_renglon': forms.TextInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control'}),
            'monto_inicial': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        self.presupuesto_anual = kwargs.pop('presupuesto_anual', None)
        super().__init__(*args, **kwargs)
        self.fields['subproducto'].queryset = Subproducto.objects.none()
        if 'producto' in self.data:
            try:
                producto_id = int(self.data.get('producto'))
                self.fields['subproducto'].queryset = Subproducto.objects.filter(producto_id=producto_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk and self.instance.producto:
            self.fields['subproducto'].queryset = self.instance.producto.subproductos.all()

    def clean_monto_inicial(self):
        monto = self.cleaned_data.get('monto_inicial')
        if monto is None or monto <= 0:
            raise ValidationError('El monto inicial debe ser mayor que cero.')
        return monto

    def clean(self):
        cleaned = super().clean()
        producto = cleaned.get('producto')
        subproducto = cleaned.get('subproducto')
        presupuesto_anual = self.presupuesto_anual or self.instance.presupuesto_anual

        if subproducto and not producto:
            cleaned['producto'] = subproducto.producto
            producto = cleaned['producto']
        if subproducto and producto and subproducto.producto_id != producto.id:
            raise ValidationError('El subproducto debe pertenecer al producto seleccionado.')

        if presupuesto_anual and cleaned.get('codigo_renglon'):
            existe = PresupuestoRenglon.objects.filter(
                presupuesto_anual=presupuesto_anual,
                codigo_renglon=cleaned['codigo_renglon'],
                producto=producto,
                subproducto=subproducto,
            ).exclude(pk=self.instance.pk).exists()
            if existe:
                raise ValidationError(
                    'Ya existe este renglón para el mismo producto/subproducto en este presupuesto.'
                )

        return cleaned


class PresupuestoCargaMasivaForm(forms.Form):
    archivo = forms.FileField(label='Archivo (CSV o XLSX)')
    modo = forms.ChoiceField(
        choices=[
            ('solo_crear', 'Solo crear (no actualizar)'),
            ('actualizar_si_sin_movimientos', 'Actualizar si no tiene movimientos'),
        ],
        required=False,
        initial='solo_crear',
        label='Modo de carga',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'

class EjecutarCDPForm(forms.Form):
    confirmar = forms.BooleanField(
        required=True,
        label='Confirmo la ejecución del CDP',
        help_text='Esta acción ejecuta definitivamente el presupuesto reservado.',
    )
    monto = forms.DecimalField(disabled=True, required=False, label='Monto a ejecutar')

    def __init__(self, cdp, *args, **kwargs):
        self.cdp = cdp
        initial = kwargs.pop('initial', {})
        initial.setdefault('monto', cdp.monto)
        kwargs['initial'] = initial
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-control' if not isinstance(field.widget, forms.CheckboxInput) else 'form-check-input'
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + f' {css_class}'

    def clean(self):
        cleaned = super().clean()
        if self.cdp.estado != CDP.Estado.RESERVADO:
            raise ValidationError('Solo se pueden ejecutar CDP en estado Reservado.')
        if hasattr(self.cdp, 'cdo'):
            raise ValidationError('El CDP ya tiene un CDO generado.')
        return cleaned

    def save(self):
        return self.cdp.ejecutar()


class LiberarCDPForm(forms.Form):
    confirmar = forms.BooleanField(
        required=True,
        label='Confirmo la liberación del CDP',
        help_text='La reserva se devolverá al presupuesto disponible.',
    )

    def __init__(self, cdp, *args, **kwargs):
        self.cdp = cdp
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-control' if not isinstance(field.widget, forms.CheckboxInput) else 'form-check-input'
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + f' {css_class}'

    def clean(self):
        cleaned = super().clean()
        if self.cdp.estado != CDP.Estado.RESERVADO:
            raise ValidationError('Solo se pueden liberar CDP en estado Reservado.')
        return cleaned

    def save(self):
        self.cdp.liberar()
        return self.cdp


class LiberarCDPSolicitudForm(forms.Form):
    """Confirmación única para liberar todos los CDP reservados de una solicitud."""

    confirmar = forms.BooleanField(
        required=True,
        label='Confirmo liberar todos los CDP reservados de la solicitud',
        help_text='Esta acción devolverá al disponible cada monto reservado.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-control' if not isinstance(field.widget, forms.CheckboxInput) else 'form-check-input'
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + f' {css_class}'

class TransferenciaPresupuestariaForm(forms.ModelForm):
    """Formulario para transferir entre renglones del presupuesto activo."""

    class Meta:
        model = TransferenciaPresupuestaria
        fields = ['renglon_origen', 'renglon_destino', 'monto', 'descripcion']
        widgets = {
            'renglon_origen': forms.Select(attrs={'class': 'form-control js-renglon-ajax'}),
            'renglon_destino': forms.Select(attrs={'class': 'form-control js-renglon-ajax'}),
            'monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        self.presupuesto_activo = kwargs.pop('presupuesto_activo', None) or PresupuestoAnual.presupuesto_activo()
        super().__init__(*args, **kwargs)
        self.fields['renglon_origen'].queryset = PresupuestoRenglon.objects.none()
        self.fields['renglon_destino'].queryset = PresupuestoRenglon.objects.none()
        self.fields['renglon_origen'].label_from_instance = lambda obj: obj.label_compacto
        self.fields['renglon_destino'].label_from_instance = lambda obj: obj.label_compacto
        self.fields['descripcion'].label = 'Observación'
        self._incluir_renglon_seleccionado('renglon_origen')
        self._incluir_renglon_seleccionado('renglon_destino')

    def _incluir_renglon_seleccionado(self, field_name):
        if not self.presupuesto_activo:
            return
        field = self.fields[field_name]
        valor = self.data.get(self.add_prefix(field_name)) if self.is_bound else self.initial.get(field_name)
        if not valor and getattr(self.instance, f'{field_name}_id', None):
            valor = getattr(self.instance, f'{field_name}_id')
        try:
            valor = int(valor)
        except (TypeError, ValueError):
            return
        field.queryset = PresupuestoRenglon.objects.select_related(
            'presupuesto_anual',
            'producto',
            'subproducto',
        ).filter(presupuesto_anual=self.presupuesto_activo, pk=valor)

    def clean(self):
        cleaned = super().clean()
        if not self.presupuesto_activo:
            raise ValidationError('No hay presupuesto activo para realizar transferencias.')

        origen = cleaned.get('renglon_origen')
        destino = cleaned.get('renglon_destino')
        monto = cleaned.get('monto')

        if origen and origen.presupuesto_anual_id != self.presupuesto_activo.id:
            raise ValidationError('El renglón origen debe pertenecer al presupuesto activo.')
        if destino and destino.presupuesto_anual_id != self.presupuesto_activo.id:
            raise ValidationError('El renglón destino debe pertenecer al presupuesto activo.')
        if origen and destino and origen == destino:
            raise ValidationError('El renglón origen y destino deben ser diferentes.')
        if monto is not None and monto <= 0:
            raise ValidationError('El monto debe ser mayor que cero.')
        if monto is not None and origen and monto > origen.monto_disponible:
            raise ValidationError('El monto a transferir excede el disponible del renglón origen.')

        return cleaned

    def save(self, commit=True):
        instancia = super().save(commit=False)
        instancia.presupuesto_anual = self.presupuesto_activo
        if commit:
            instancia.save()
        return instancia


class TransferenciaMultipleForm(forms.Form):
    """Formulario base para transferencia desde un único renglón origen."""

    renglon_origen = forms.ModelChoiceField(
        queryset=PresupuestoRenglon.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control js-renglon-ajax'}),
        label='Renglón origen',
    )
    descripcion = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        label='Observación',
    )

    def __init__(self, *args, **kwargs):
        self.presupuesto_activo = kwargs.pop('presupuesto_activo', None) or PresupuestoAnual.presupuesto_activo()
        renglones_qs = kwargs.pop('renglones_qs', None)
        super().__init__(*args, **kwargs)
        self.fields['renglon_origen'].queryset = renglones_qs if renglones_qs is not None else PresupuestoRenglon.objects.none()
        self.fields['renglon_origen'].label_from_instance = lambda obj: obj.label_compacto
        if renglones_qs is None and self.presupuesto_activo:
            valor = self.data.get(self.add_prefix('renglon_origen')) if self.is_bound else self.initial.get('renglon_origen')
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                valor = None
            if valor:
                self.fields['renglon_origen'].queryset = PresupuestoRenglon.objects.select_related(
                    'presupuesto_anual',
                    'producto',
                    'subproducto',
                ).filter(presupuesto_anual=self.presupuesto_activo, pk=valor)

    def clean(self):
        cleaned = super().clean()
        origen = cleaned.get('renglon_origen')
        if not self.presupuesto_activo:
            raise ValidationError('No hay presupuesto activo para realizar transferencias.')
        if origen and origen.presupuesto_anual_id != self.presupuesto_activo.id:
            raise ValidationError('El renglón origen debe pertenecer al presupuesto activo.')
        return cleaned


class TransferenciaDestinoForm(forms.Form):
    renglon_destino = forms.ModelChoiceField(
        queryset=PresupuestoRenglon.objects.none(),
        widget=forms.Select(attrs={'class': 'form-control js-renglon-ajax'}),
        label='Renglón destino',
    )
    monto = forms.DecimalField(
        max_digits=14,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        label='Monto',
    )

    def __init__(self, *args, **kwargs):
        self.presupuesto_activo = kwargs.pop('presupuesto_activo', None)
        renglones_qs = kwargs.pop('renglones_qs', None)
        super().__init__(*args, **kwargs)
        self.fields['renglon_destino'].label_from_instance = lambda obj: obj.label_compacto
        self.fields['renglon_destino'].queryset = renglones_qs if renglones_qs is not None else PresupuestoRenglon.objects.none()
        if renglones_qs is None and self.presupuesto_activo:
            valor = self.data.get(self.add_prefix('renglon_destino')) if self.is_bound else self.initial.get('renglon_destino')
            try:
                valor = int(valor)
            except (TypeError, ValueError):
                valor = None
            if valor:
                self.fields['renglon_destino'].queryset = PresupuestoRenglon.objects.select_related(
                    'presupuesto_anual',
                    'producto',
                    'subproducto',
                ).filter(presupuesto_anual=self.presupuesto_activo, pk=valor)


class BaseTransferenciaDestinoFormSet(forms.BaseFormSet):
    def __init__(self, *args, **kwargs):
        self.presupuesto_activo = kwargs.pop('presupuesto_activo', None)
        self.origen = kwargs.pop('origen', None)
        super().__init__(*args, **kwargs)
        for form in self.forms:
            form.fields['renglon_destino'].label_from_instance = lambda obj: obj.label_compacto

    def clean(self):
        if any(self.errors):
            return

        destinos = set()
        total = 0
        filas_validas = 0

        for form in self.forms:
            if not form.cleaned_data:
                continue
            if form.cleaned_data.get('DELETE'):
                continue

            destino = form.cleaned_data.get('renglon_destino')
            monto = form.cleaned_data.get('monto')
            if not destino or monto is None:
                continue

            filas_validas += 1

            if monto <= 0:
                raise ValidationError('Cada monto destino debe ser mayor que cero.')
            if self.presupuesto_activo and destino.presupuesto_anual_id != self.presupuesto_activo.id:
                raise ValidationError('Todos los destinos deben pertenecer al presupuesto activo.')
            if self.origen and destino.id == self.origen.id:
                raise ValidationError('El renglón origen y destino deben ser diferentes.')
            if destino.id in destinos:
                raise ValidationError('No se permiten renglones destino duplicados en la misma transferencia.')

            destinos.add(destino.id)
            total += monto

        if filas_validas == 0:
            raise ValidationError('Debe agregar al menos un renglón destino.')

        self.total_monto = total


TransferenciaDestinoFormSet = forms.formset_factory(
    TransferenciaDestinoForm,
    formset=BaseTransferenciaDestinoFormSet,
    extra=1,
    can_delete=True,
)
