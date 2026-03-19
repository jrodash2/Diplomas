from django import forms
from django.contrib.auth.models import User, Group
from .models import Ticket, TipoEquipo, Insumo, FechaInsumo
from django.core.exceptions import ValidationError

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['oficina', 'via_contacto', 'telefono', 'correo', 'prioridad', 'tipo_equipo', 'problema', 'responsable', 'tecnico_asignado', 'estado']

    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        
        # Filtrar usuarios por grupo 'tecnico'
        try:
            tecnicos_group = Group.objects.get(name='tecnico')
            self.fields['tecnico_asignado'].queryset = User.objects.filter(groups=tecnicos_group)
        except Group.DoesNotExist:
            self.fields['tecnico_asignado'].queryset = User.objects.none()
        
        # Agregar la clase 'form-control' a todos los campos del formulario
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


from django import forms
from django.contrib.auth.models import User, Group

class UserForm(forms.ModelForm):
    dpi = forms.CharField(required=False)
    new_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput()
    )
    confirm_password = forms.CharField(
        required=False,
        widget=forms.PasswordInput()
    )
    group = forms.ModelChoiceField(
        queryset=Group.objects.all(),
        required=True
    )

    def __init__(self, *args, **kwargs):
        self.edit = kwargs.pop('edit', False)
        super().__init__(*args, **kwargs)

        # ================================
        # 🔵 AÑADIR form-control A TODO
        # ================================
        for field_name, field in self.fields.items():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs.update({
                    'class': 'form-control'
                })

        # ================================
        # 🟢 MOSTRAR GRUPO ACTUAL DEL USUARIO
        # ================================
        if self.edit and self.instance and self.instance.pk:
            grupos = self.instance.groups.all()
            if grupos.exists():
                self.fields['group'].initial = grupos.first()

        # ================================
        # 🔴 OCULTAR CAMPOS SOLO AL EDITAR
        # ================================
        if self.edit:
            self.fields['dpi'].widget = forms.HiddenInput()
            self.fields['new_password'].widget = forms.HiddenInput()
            self.fields['confirm_password'].widget = forms.HiddenInput()

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']

    def clean(self):
        cleaned = super().clean()

        # Validación sólo en creación
        if not self.edit:
            new_password = cleaned.get('new_password')
            confirm_password = cleaned.get('confirm_password')

            if new_password != confirm_password:
                raise forms.ValidationError("Las contraseñas no coinciden.")

        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)

        # Guardar contraseña sólo en creación
        if not self.edit:
            password = self.cleaned_data.get('new_password')
            if password:
                user.set_password(password)

        if commit:
            user.save()

        # Asignar grupo
        group = self.cleaned_data.get('group')
        if group:
            user.groups.clear()
            user.groups.add(group)

        return user





            
class TickettecForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ['detalle_problema', 'solucion_problema', 'estado']

    def __init__(self, *args, **kwargs):
        super(TickettecForm, self).__init__(*args, **kwargs)
        

       
        
         # Filtrar estados
        ESTADOS_PERMITIDOS = ['en_proceso', 'cerrado', 'pendiente']
        self.fields['estado'].choices = [(key, value) for key, value in self.fields['estado'].choices if key in ESTADOS_PERMITIDOS]
        # Agregar la clase 'form-control' a todos los campos del formulario
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


from .models import Oficina

class OficinaForm(forms.ModelForm):
    class Meta:
        model = Oficina
        fields = ['nombre']

        
    def __init__(self, *args, **kwargs):
        super(OficinaForm, self).__init__(*args, **kwargs)
        
        
        # Agregar la clase 'form-control' a todos los campos del formulario
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'


class TipoEquipoForm(forms.ModelForm):
    class Meta:
        model = TipoEquipo
        fields = ['nombre']

          
    def __init__(self, *args, **kwargs):
        super(TipoEquipoForm, self).__init__(*args, **kwargs)
        
        
        # Agregar la clase 'form-control' a todos los campos del formulario
        for field in self.fields.values():
            field.widget.attrs['class'] = field.widget.attrs.get('class', '') + ' form-control'



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
   


