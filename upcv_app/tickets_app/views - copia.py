
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.utils import timezone
from django.contrib.auth.models import Group, User
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Ticket
from .forms import TicketForm
from .forms import TickettecForm
from django.db.models import Case, When, IntegerField
from .forms import TicketForm
from .models import Oficina
from .models import fechainsumo
from .forms import OficinaForm
from .models import TipoEquipo
from .forms import TipoEquipoForm
from .forms import UserForm
from .forms import FechaInsumoForm

from django.http import JsonResponse
from django.db.models import Count
from django.db.models.functions import TruncWeek
from django.utils import timezone
import datetime


import pandas as pd
from .forms import ExcelUploadForm
from .models import Insumo # Cambia esto por tu modelo real
from django.core.paginator import Paginator


def insumos_json(request):
    draw = int(request.GET.get('draw', 1))
    start = int(request.GET.get('start', 0))
    length = int(request.GET.get('length', 10))
    search_value = request.GET.get('search[value]', '')

    queryset = Insumo.objects.all()

    if search_value:
        queryset = queryset.filter(nombre__icontains=search_value)

    total = queryset.count()
    paginator = Paginator(queryset, length)
    page_number = start // length + 1
    page = paginator.page(page_number)

    data = []
    for insumo in page.object_list:
        data.append([
            insumo.renglon,
            insumo.codigo_insumo,
            insumo.nombre,
            insumo.caracteristicas,
            insumo.nombre_presentacion,
            insumo.cantidad_unidad_presentacion,
            insumo.codigo_presentacion
        ])

    return JsonResponse({
        'draw': draw,
        'recordsTotal': total,
        'recordsFiltered': total,
        'data': data
    })

def importar_excel(request):
    if request.method == 'POST':
        form = ExcelUploadForm(request.POST, request.FILES)
        fecha_form = FechaInsumoForm(request.POST)  # Formulario para la fecha

        if form.is_valid() and fecha_form.is_valid():  # Validar ambos formularios
            archivo = request.FILES['archivo_excel']
            df = pd.read_excel(archivo)

            # Eliminar los datos anteriores
            Insumo.objects.all().delete()

            # Crear una lista para guardar los objetos que se crearán
            nuevos_insumos = []

            for _, row in df.iterrows():
                insumo = Insumo(
                    renglon=row['RENGLÓN'],
                    codigo_insumo=row['CÓDIGO DE INSUMO'],
                    nombre=row['NOMBRE'],
                    caracteristicas=row['CARACTERÍSTICAS'],
                    nombre_presentacion=row['NOMBRE DE LA PRESENTACIÓN'],
                    cantidad_unidad_presentacion=row['CANTIDAD Y UNIDAD DE MEDIDA DE LA PRESENTACIÓN'],
                    codigo_presentacion=row['CÓDIGO DE PRESENTACIÓN'],
                    fecha_actualizacion=timezone.now()
                )
                nuevos_insumos.append(insumo)

            # Guardar todos los nuevos insumos de una vez
            Insumo.objects.bulk_create(nuevos_insumos)

            # Aquí es donde se captura la fecha del formulario de fecha
            fecha_in = fecha_form.save(commit=False)
            # La fecha capturada será la fecha proporcionada por el formulario (no la actual)
            fecha_in.fechainsumo = fecha_form.cleaned_data['fechainsumo']
            fecha_in.save()

            # Redirigir con un parámetro de sesión para pasar los últimos insumos
            request.session['importados'] = True
            return redirect('tickets:catalogo_insumos_view')
    else:
        form = ExcelUploadForm()
        fecha_form = FechaInsumoForm()  # Iniciar el formulario de fecha

    return render(request, 'tickets/importar_excel.html', {'form': form, 'fecha_form': fecha_form})



def catalogo_insumos_view(request):
    # Obtener los insumos
    insumos = Insumo.objects.all().order_by('-fecha_actualizacion')
    
    # Obtener la última fecha de insumo (último registro de fechainsumo)
    ultima_fecha_insumo = fechainsumo.objects.last()  # Obtiene el último registro de la tabla fechainsumo
    
    return render(request, 'tickets/confirmacion.html', {
        'insumos': insumos,
        'ultima_fecha_insumo': ultima_fecha_insumo
    })

@login_required
def user_create(request):
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()  # Guarda el usuario si el formulario es válido
            return redirect('tickets:user_create')  # Redirige a la misma página
    else:
        form = UserForm()

    users = User.objects.all()  # Obtener todos los usuarios
    return render(request, 'tickets/user_form.html', {'form': form, 'users': users})


@login_required
def user_delete(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        user.delete()
        return redirect('tickets:user_create')  # Redirige a la misma página para mostrar la lista actualizada
    return render(request, 'tickets/user_confirm_delete.html', {'user': user})

@login_required
def oficina_create(request):
    if request.method == 'POST':
        form = OficinaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tickets:oficina_create')  # Redirige a la misma página para mostrar la lista actualizada
    else:
        form = OficinaForm()
    
    oficinas = Oficina.objects.all()  # Obtener todas las oficinas
    return render(request, 'tickets/oficina_form_adm.html', {'form': form, 'oficinas': oficinas})


@login_required
def tipo_equipo_create(request):
    if request.method == 'POST':
        form = TipoEquipoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tickets:tipo_equipo_create') 
    else:
        form = TipoEquipoForm()
    
    tipos_equipo = TipoEquipo.objects.all()  
    return render(request, 'tickets/tipo_equipo_form_adm.html', {'form': form, 'tipos_equipo': tipos_equipo})

@login_required
def tickets_dahsboard(request):
    tickets = Ticket.objects.filter(tecnico_asignado=request.user).annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_dahsboard.html', {'tickets': tickets})



@login_required
def tickets_dahsboard_adm(request):
    # Obtener todos los tickets ordenados por estado
    tickets = Ticket.objects.all().annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')

    # Verificar el conteo de tickets
    print(f"Total de tickets encontrados: {tickets.count()}")

    # Estadísticas de tickets
    total_tickets = tickets.count()
    tickets_abiertos = tickets.filter(estado='abierto').count()
    tickets_cerrados = tickets.filter(estado='cerrado').count()
    tickets_en_proceso = tickets.filter(estado='en_proceso').count()
    tickets_pendientes = tickets.filter(estado='pendiente').count()

    tickets_alta_prioridad = tickets.filter(prioridad='alta').count()
    tickets_media_prioridad = tickets.filter(prioridad='media').count()
    tickets_baja_prioridad = tickets.filter(prioridad='baja').count()

    # Generar fechas para las semanas del mes actual
    today = timezone.now().date()
    first_day_of_month = today.replace(day=1)
    last_day_of_month = today.replace(day=28) + datetime.timedelta(days=4)  # Último día del mes

    weeks = []
    current_date = first_day_of_month

    while current_date <= last_day_of_month:
        sunday = current_date + datetime.timedelta(days=(6 - current_date.weekday()))
        weeks.append(sunday.strftime('%B %d, %Y'))
        current_date = sunday + datetime.timedelta(days=1)  # Avanzar al lunes de la siguiente semana

    # Obtener el conteo de tickets por semana (utilizando TruncWeek para truncar por semana)
    tickets_por_semana = tickets.annotate(week=TruncWeek('fecha_creacion')) \
        .filter(fecha_creacion__gte=first_day_of_month, fecha_creacion__lte=last_day_of_month) \
        .values('week') \
        .annotate(ticket_count=Count('id')) \
        .order_by('week')

    semanas = [ticket['week'].strftime('%B %d, %Y') for ticket in tickets_por_semana]
    cantidad_tickets = [ticket['ticket_count'] for ticket in tickets_por_semana]

    # Datos para los gráficos
    estado_labels = ['Abiertos', 'Cerrados', 'En Proceso', 'Pendientes']
    estado_data = [tickets_abiertos, tickets_cerrados, tickets_en_proceso, tickets_pendientes]

    prioridad_labels = ['Alta', 'Media', 'Baja']
    prioridad_data = [tickets_alta_prioridad, tickets_media_prioridad, tickets_baja_prioridad]

    context = {
        'total_tickets': total_tickets,
        'tickets_abiertos': tickets_abiertos,
        'tickets_cerrados': tickets_cerrados,
        'tickets_en_proceso': tickets_en_proceso,
        'tickets_pendientes': tickets_pendientes,
        'tickets_alta_prioridad': tickets_alta_prioridad,
        'tickets_media_prioridad': tickets_media_prioridad,
        'tickets_baja_prioridad': tickets_baja_prioridad,
        'estado_labels': estado_labels,
        'estado_data': estado_data,
        'prioridad_labels': prioridad_labels,
        'prioridad_data': prioridad_data,
        'semanas': semanas,
        'cantidad_tickets': cantidad_tickets,
        'tickets': tickets,  # Asegúrate de pasar los tickets a la plantilla
    }

    return render(request, 'tickets/tickets_dahsboard_adm.html', context)



@login_required
def tickets_abiertos(request):
    tickets = Ticket.objects.filter(tecnico_asignado=request.user, estado='abierto').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_abiertos.html', {'tickets': tickets})


@login_required
def tickets_abiertos_adm(request):
    tickets = Ticket.objects.filter(estado='abierto').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_abiertos_adm.html', {'tickets': tickets})

@login_required
def tickets_proceso(request):
    tickets = Ticket.objects.filter(tecnico_asignado=request.user, estado='en_proceso').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_proceso.html', {'tickets': tickets})


@login_required
def tickets_proceso_adm(request):
    tickets = Ticket.objects.filter(estado='en_proceso').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_proceso_adm.html', {'tickets': tickets})


@login_required
def tickets_cerrado_adm(request):
    tickets = Ticket.objects.filter(estado='cerrado').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_cerrado_adm.html', {'tickets': tickets})


@login_required
def tickets_cerrado(request):
    tickets = Ticket.objects.filter(tecnico_asignado=request.user, estado='cerrado').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_cerrado.html', {'tickets': tickets})



@login_required
def tickets_pendiente_adm(request):
    tickets = Ticket.objects.filter(estado='pendiente').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_pendiente_adm.html', {'tickets': tickets})



@login_required
def tickets_pendiente(request):
    tickets = Ticket.objects.filter(tecnico_asignado=request.user, estado='pendiente').annotate(
        estado_order=Case(
            When(estado='abierto', then=0),
            When(estado='en_proceso', then=1),
            When(estado='cerrado', then=2),
            When(estado='pendiente', then=3),
            output_field=IntegerField(),
        )
    ).order_by('estado_order', '-fecha_creacion')
    return render(request, 'tickets/tickets_pendiente.html', {'tickets': tickets})


@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return render(request, 'tickets/ticket_detail.html', {'ticket': ticket})


@login_required
def ticket_detail_tec(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    return render(request, 'tickets/ticket_detail_tec.html', {'ticket': ticket})

@login_required
def ticket_update(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.method == 'POST':
        form = TickettecForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            return redirect('tickets:tickets_dahsboard')
    else:
        form = TickettecForm(instance=ticket)
    return render(request, 'tickets/ticket_form.html', {'form': form, 'ticket': ticket})

@login_required
def update_adm(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.method == 'POST':
        form = TicketForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            return redirect('tickets:tickets_dahsboard_adm')
    else:
        form = TicketForm(instance=ticket)
    return render(request, 'tickets/ticket_form_adm.html', {'form': form})

@login_required
def ticket_create(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tickets:tickets_dahsboard')
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form.html', {'form': form})


@login_required
def ticket_create_adm(request):
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('tickets:tickets_dahsboard_adm')
    else:
        form = TicketForm()
    return render(request, 'tickets/ticket_form_adm.html', {'form': form})


@login_required 
def manuales(request):
    return render(request, 'tickets/tickets_manuales.html')

@login_required 
def manualesadm(request):
    return render(request, 'tickets/tickets_manualesadm.html')


