from django import forms

from empleados_app.models import Empleado

from .models import Curso, DisenoDiploma, Firma


class FirmaForm(forms.ModelForm):
    class Meta:
        model = Firma
        fields = ['nombre', 'rol', 'firma']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre completo'}),
            'rol': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej.: Director, Coordinador'}),
            'firma': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class DisenoDiplomaForm(forms.ModelForm):
    class Meta:
        model = DisenoDiploma
        fields = ['nombre', 'descripcion', 'imagen_fondo', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del diseño'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción opcional'}),
            'imagen_fondo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class AgregarEmpleadoCursoForm(forms.Form):
    dpi = forms.CharField(label="DPI del Empleado", max_length=15)
    nombre_completo = forms.CharField(label="Empleado", required=False, disabled=True)
    curso = forms.ModelChoiceField(queryset=Curso.objects.all(), label="Curso")

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


class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ['codigo', 'nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'firmas', 'diseno_diploma']
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'maxlength': '5', 'placeholder': 'Ej: 12345'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del curso'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Descripción del curso'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}, format='%Y-%m-%d'),
            'firmas': forms.SelectMultiple(attrs={'class': 'form-control', 'size': 5}),
            'diseno_diploma': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fecha_inicio'].input_formats = ['%Y-%m-%d']
        self.fields['fecha_fin'].input_formats = ['%Y-%m-%d']
        self.fields['firmas'].queryset = Firma.objects.all()
        self.fields['firmas'].label = "Firmas que aparecerán en el diploma"
        self.fields['diseno_diploma'].queryset = DisenoDiploma.objects.filter(activo=True).order_by('nombre')
        self.fields['diseno_diploma'].required = False
        self.fields['diseno_diploma'].empty_label = "Seleccione un diseño"
        self.fields['diseno_diploma'].label = "Diseño de diploma"

    def clean_codigo(self):
        codigo = self.cleaned_data.get("codigo")
        if len(codigo) != 5 or not codigo.isdigit():
            raise forms.ValidationError("El código debe tener 5 dígitos.")
        return codigo
