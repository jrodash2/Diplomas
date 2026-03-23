from django import forms
from django.contrib.auth import get_user_model

from empleados_app.models import Empleado

from .models import (
    Curso,
    CursoEmpleado,
    DisenoDiploma,
    Firma,
    UbicacionDiploma,
    UsuarioUbicacionDiploma,
)
from .utils import available_manager_users

User = get_user_model()


class ScopedModelFormMixin:
    scope_field_name = "ubicacion"

    def __init__(self, *args, scope=None, **kwargs):
        self.scope = scope or {}
        super().__init__(*args, **kwargs)
        if self.scope_field_name in self.fields:
            if self.scope.get("is_admin"):
                self.fields[self.scope_field_name].queryset = UbicacionDiploma.objects.filter(activa=True).order_by("nombre")
                self.fields[self.scope_field_name].required = True
            else:
                location = self.scope.get("location")
                if location:
                    self.fields[self.scope_field_name].initial = location
                self.fields[self.scope_field_name].widget = forms.HiddenInput()
                self.fields[self.scope_field_name].required = False

    def clean(self):
        cleaned_data = super().clean()
        if self.scope_field_name in self.fields and not self.scope.get("is_admin"):
            location = self.scope.get("location")
            if not location:
                raise forms.ValidationError("Su usuario no tiene una ubicación asignada.")
            cleaned_data[self.scope_field_name] = location
        return cleaned_data


class UbicacionDiplomaForm(forms.ModelForm):
    class Meta:
        model = UbicacionDiploma
        fields = ["nombre", "descripcion", "activa"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre de la ubicación"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción opcional"}),
            "activa": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class UsuarioUbicacionDiplomaForm(forms.ModelForm):
    usuario = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Usuario gestor",
    )
    ubicacion = forms.ModelChoiceField(
        queryset=UbicacionDiploma.objects.filter(activa=True).order_by("nombre"),
        widget=forms.Select(attrs={"class": "form-control"}),
        label="Ubicación",
    )

    class Meta:
        model = UsuarioUbicacionDiploma
        fields = ["usuario", "ubicacion"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["usuario"].queryset = available_manager_users()

    def save(self, commit=True, assigned_by=None):
        instance = super().save(commit=False)
        if assigned_by is not None:
            instance.asignado_por = assigned_by
        if commit:
            instance.save()
        return instance


class FirmaForm(ScopedModelFormMixin, forms.ModelForm):
    class Meta:
        model = Firma
        fields = ["ubicacion", "nombre", "rol", "firma"]
        widgets = {
            "ubicacion": forms.Select(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre completo"}),
            "rol": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ej.: Director, Coordinador"}),
            "firma": forms.ClearableFileInput(attrs={"class": "form-control"}),
        }


class DisenoDiplomaForm(ScopedModelFormMixin, forms.ModelForm):
    class Meta:
        model = DisenoDiploma
        fields = ["ubicacion", "nombre", "descripcion", "imagen_fondo", "activo"]
        widgets = {
            "ubicacion": forms.Select(attrs={"class": "form-control"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del diseño"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción opcional"}),
            "imagen_fondo": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "activo": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }


class AgregarEmpleadoCursoForm(forms.Form):
    dpi = forms.CharField(label="DPI del Empleado", max_length=15)
    nombre_completo = forms.CharField(label="Empleado", required=False, disabled=True)
    curso = forms.ModelChoiceField(queryset=Curso.objects.none(), label="Curso")

    def __init__(self, *args, scope=None, **kwargs):
        self.scope = scope or {}
        super().__init__(*args, **kwargs)
        cursos = Curso.objects.all().order_by("nombre")
        if not self.scope.get("is_admin"):
            location = self.scope.get("location")
            cursos = cursos.filter(ubicacion=location) if location else cursos.none()
        self.fields["curso"].queryset = cursos
        self.fields["curso"].widget.attrs.update({"class": "form-control"})
        self.fields["dpi"].widget.attrs.update({"class": "form-control"})
        self.fields["nombre_completo"].widget.attrs.update({"class": "form-control"})

    def clean(self):
        cleaned_data = super().clean()
        dpi = cleaned_data.get("dpi")

        if dpi:
            try:
                empleado = Empleado.objects.get(dpi=dpi)
                cleaned_data["empleado"] = empleado
                cleaned_data["nombre_completo"] = f"{empleado.nombres} {empleado.apellidos}"
            except Empleado.DoesNotExist:
                raise forms.ValidationError("No existe un empleado con ese DPI.")

        return cleaned_data


class AgregarParticipanteRapidoForm(forms.Form):
    curso = forms.ModelChoiceField(queryset=Curso.objects.none(), widget=forms.HiddenInput(), required=True)
    dpi = forms.CharField(
        label="DPI *",
        max_length=15,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "Ingrese DPI para buscar participante existente",
        }),
        help_text="Escriba el DPI y el sistema autocompletará el nombre si el participante existe.",
    )
    nombre_completo = forms.CharField(
        label="Nombre autocompletado",
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "readonly": "readonly",
            "placeholder": "El nombre aparecerá automáticamente si el DPI existe",
        }),
    )

    def __init__(self, *args, scope=None, course=None, **kwargs):
        self.scope = scope or {}
        self.course = course
        super().__init__(*args, **kwargs)
        cursos = Curso.objects.all().order_by("nombre")
        if not self.scope.get("is_admin"):
            location = self.scope.get("location")
            cursos = cursos.filter(ubicacion=location) if location else cursos.none()
        self.fields["curso"].queryset = cursos
        if course is not None:
            self.fields["curso"].initial = course

    def clean_dpi(self):
        dpi = "".join(str(self.cleaned_data.get("dpi") or "").split())
        if not dpi:
            raise forms.ValidationError("Debe ingresar un DPI.")
        return dpi

    def clean(self):
        cleaned_data = super().clean()
        dpi = cleaned_data.get("dpi")
        if dpi:
            try:
                empleado = Empleado.objects.get(dpi=dpi)
                cleaned_data["empleado"] = empleado
                cleaned_data["nombre_completo"] = f"{empleado.nombres} {empleado.apellidos}".strip()
            except Empleado.DoesNotExist:
                raise forms.ValidationError("No existe un participante registrado con ese DPI. Use la matrícula manual.")
        return cleaned_data


class MatriculaManualParticipanteForm(forms.ModelForm):
    curso = forms.ModelChoiceField(queryset=Curso.objects.none(), widget=forms.HiddenInput(), required=True)

    class Meta:
        model = CursoEmpleado
        fields = [
            "curso",
            "participante_dpi",
            "participante_nombre",
            "participante_foto",
            "participante_correo",
            "participante_telefono",
            "observaciones",
        ]
        widgets = {
            "participante_dpi": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese DPI del participante",
            }),
            "participante_nombre": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ingrese nombre completo del participante",
            }),
            "participante_foto": forms.ClearableFileInput(attrs={"class": "form-control"}),
            "participante_correo": forms.EmailInput(attrs={
                "class": "form-control",
                "placeholder": "correo@ejemplo.com",
            }),
            "participante_telefono": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Número telefónico opcional",
            }),
            "observaciones": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Notas internas u observaciones opcionales",
            }),
        }
        help_texts = {
            "participante_dpi": "Campo obligatorio. Ingrese el DPI del participante en formato habitual.",
            "participante_nombre": "Campo obligatorio. Puede escribir el nombre completo aunque el DPI no exista en empleados.",
            "participante_foto": "Opcional. Suba una imagen del participante si desea usarla en el diploma.",
            "participante_correo": "Opcional. Si se completa, debe ser un correo válido.",
            "participante_telefono": "Opcional. Puede registrar un teléfono de contacto.",
            "observaciones": "Opcional. Use este espacio para notas internas del curso.",
        }
        labels = {
            "participante_dpi": "DPI *",
            "participante_nombre": "Nombre del participante *",
            "participante_foto": "Fotografía (opcional)",
            "participante_correo": "Correo electrónico (opcional)",
            "participante_telefono": "Teléfono (opcional)",
            "observaciones": "Observaciones (opcional)",
        }

    def __init__(self, *args, scope=None, course=None, **kwargs):
        self.scope = scope or {}
        self.course = course
        super().__init__(*args, **kwargs)
        cursos = Curso.objects.all().order_by("nombre")
        if not self.scope.get("is_admin"):
            location = self.scope.get("location")
            cursos = cursos.filter(ubicacion=location) if location else cursos.none()
        self.fields["curso"].queryset = cursos
        if course is not None:
            self.fields["curso"].initial = course
        self.fields["participante_dpi"].required = True
        self.fields["participante_nombre"].required = True
        self.fields["participante_foto"].required = False
        self.fields["participante_correo"].required = False
        self.fields["participante_telefono"].required = False
        self.fields["observaciones"].required = False

    def clean_participante_dpi(self):
        dpi = "".join(str(self.cleaned_data.get("participante_dpi") or "").split())
        if not dpi:
            raise forms.ValidationError("El DPI es obligatorio.")
        return dpi

    def clean_participante_nombre(self):
        nombre = " ".join(str(self.cleaned_data.get("participante_nombre") or "").split())
        if not nombre:
            raise forms.ValidationError("El nombre del participante es obligatorio.")
        return nombre

    def clean(self):
        cleaned_data = super().clean()
        curso = cleaned_data.get("curso") or self.course
        dpi = cleaned_data.get("participante_dpi")
        if curso and dpi and CursoEmpleado.objects.filter(curso=curso, participante_dpi=dpi).exists():
            raise forms.ValidationError("Ya existe un participante inscrito en este curso con ese DPI.")
        return cleaned_data


class CursoForm(ScopedModelFormMixin, forms.ModelForm):
    class Meta:
        model = Curso
        fields = ["ubicacion", "codigo", "nombre", "descripcion", "fecha_inicio", "fecha_fin", "firmas", "diseno_diploma"]
        widgets = {
            "ubicacion": forms.Select(attrs={"class": "form-control"}),
            "codigo": forms.TextInput(attrs={"class": "form-control", "maxlength": "5", "placeholder": "Ej: 12345"}),
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre del curso"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Descripción del curso"}),
            "fecha_inicio": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "fecha_fin": forms.DateInput(attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"),
            "firmas": forms.SelectMultiple(attrs={"class": "form-control", "size": 5}),
            "diseno_diploma": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, scope=None, **kwargs):
        super().__init__(*args, scope=scope, **kwargs)
        self.fields["fecha_inicio"].input_formats = ["%Y-%m-%d"]
        self.fields["fecha_fin"].input_formats = ["%Y-%m-%d"]
        firmas = Firma.objects.all().order_by("nombre")
        disenos = DisenoDiploma.objects.filter(activo=True).order_by("nombre")
        if not (self.scope or {}).get("is_admin"):
            location = (self.scope or {}).get("location")
            firmas = firmas.filter(ubicacion=location) if location else firmas.none()
            disenos = disenos.filter(ubicacion=location) if location else disenos.none()
        self.fields["firmas"].queryset = firmas
        self.fields["firmas"].label = "Firmas que aparecerán en el diploma"
        self.fields["diseno_diploma"].queryset = disenos
        self.fields["diseno_diploma"].required = False
        self.fields["diseno_diploma"].empty_label = "Seleccione un diseño"
        self.fields["diseno_diploma"].label = "Diseño de diploma"

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo")
        if len(codigo) != 5 or not codigo.isdigit():
            raise forms.ValidationError("El código debe tener 5 dígitos.")
        return codigo

    def clean(self):
        cleaned_data = super().clean()
        ubicacion = cleaned_data.get("ubicacion")
        diseno = cleaned_data.get("diseno_diploma")
        firmas = cleaned_data.get("firmas")

        if ubicacion and diseno and diseno.ubicacion_id != ubicacion.id:
            self.add_error("diseno_diploma", "El diseño seleccionado no pertenece a la ubicación del curso.")

        if ubicacion and firmas:
            firmas_invalidas = [firma.nombre for firma in firmas if firma.ubicacion_id != ubicacion.id]
            if firmas_invalidas:
                self.add_error("firmas", f"Las siguientes firmas no pertenecen a la ubicación seleccionada: {', '.join(firmas_invalidas)}")

        return cleaned_data
