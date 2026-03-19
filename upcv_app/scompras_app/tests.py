from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse

from .models import KardexPresupuesto, PresupuestoAnual, PresupuestoRenglon, TransferenciaPresupuestaria


class TransferenciaMultipleTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='PRESUPUESTO')
        self.user = User.objects.create_user(username='presupuesto', password='secret123')
        self.user.groups.add(self.group)
        self.client.force_login(self.user)

        self.presupuesto = PresupuestoAnual.objects.create(anio=2026, activo=True)
        self.origen = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='100',
            descripcion='Origen',
            monto_inicial=Decimal('1000.00'),
        )
        self.destino_1 = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='200',
            descripcion='Destino 1',
            monto_inicial=Decimal('200.00'),
        )
        self.destino_2 = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='300',
            descripcion='Destino 2',
            monto_inicial=Decimal('300.00'),
        )

    def _payload_multiple(self, monto_1='100.00', monto_2='50.00', destino_1=None, destino_2=None):
        return {
            'renglon_origen': str(self.origen.id),
            'descripcion': 'Ajuste de prueba',
            'destinos-TOTAL_FORMS': '2',
            'destinos-INITIAL_FORMS': '0',
            'destinos-MIN_NUM_FORMS': '0',
            'destinos-MAX_NUM_FORMS': '1000',
            'destinos-0-renglon_destino': str((destino_1 or self.destino_1).id),
            'destinos-0-monto': str(monto_1),
            'destinos-0-DELETE': '',
            'destinos-1-renglon_destino': str((destino_2 or self.destino_2).id),
            'destinos-1-monto': str(monto_2),
            'destinos-1-DELETE': '',
        }

    def test_transferencia_simple_sigue_funcionando(self):
        response = self.client.post(
            reverse('scompras:transferencia_crear'),
            {
                'renglon_origen': self.origen.id,
                'renglon_destino': self.destino_1.id,
                'monto': '100.00',
                'descripcion': 'Simple',
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 1)
        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('900.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('300.00'))

    def test_transferencia_multiple_dos_destinos_ok(self):
        response = self.client.post(reverse('scompras:transferencia_multiple_crear'), self._payload_multiple(), follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 2)
        self.assertEqual(KardexPresupuesto.objects.filter(tipo=KardexPresupuesto.TipoMovimiento.TRANSFERENCIA_SALIDA).count(), 2)
        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.destino_2.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('850.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('300.00'))
        self.assertEqual(self.destino_2.monto_disponible, Decimal('350.00'))

    def test_transferencia_multiple_suma_supera_disponible_no_aplica(self):
        response = self.client.post(
            reverse('scompras:transferencia_multiple_crear'),
            self._payload_multiple(monto_1='700.00', monto_2='400.00'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'excede el disponible', status_code=200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 0)
        self.origen.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('1000.00'))

    def test_transferencia_multiple_destino_duplicado_error(self):
        response = self.client.post(
            reverse('scompras:transferencia_multiple_crear'),
            self._payload_multiple(destino_2=self.destino_1),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'destino duplicados', status_code=200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 0)

    def test_transferencia_multiple_monto_cero_o_negativo_error(self):
        response = self.client.post(
            reverse('scompras:transferencia_multiple_crear'),
            self._payload_multiple(monto_1='0', monto_2='-2.00'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 0)

    def test_transferencia_multiple_error_en_una_fila_rollback(self):
        response = self.client.post(
            reverse('scompras:transferencia_multiple_crear'),
            self._payload_multiple(monto_1='100.00', monto_2='2000.00'),
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(TransferenciaPresupuestaria.objects.count(), 0)
        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('1000.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('200.00'))

    def test_transferencia_multiple_usa_select_for_update(self):
        with patch('scompras_app.views.PresupuestoRenglon.objects.select_for_update', wraps=PresupuestoRenglon.objects.select_for_update) as mocked:
            response = self.client.post(reverse('scompras:transferencia_multiple_crear'), self._payload_multiple(), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mocked.called)


class TransferenciaReversaTests(TestCase):
    def setUp(self):
        self.group = Group.objects.create(name='PRESUPUESTO')
        self.user = User.objects.create_user(username='admin_presupuesto', password='secret123')
        self.user.groups.add(self.group)
        self.client.force_login(self.user)

        self.presupuesto = PresupuestoAnual.objects.create(anio=2027, activo=True)
        self.origen = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='100',
            descripcion='Origen',
            monto_inicial=Decimal('1000.00'),
        )
        self.destino_1 = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='200',
            descripcion='Destino 1',
            monto_inicial=Decimal('100.00'),
        )
        self.destino_2 = PresupuestoRenglon.objects.create(
            presupuesto_anual=self.presupuesto,
            codigo_renglon='300',
            descripcion='Destino 2',
            monto_inicial=Decimal('100.00'),
        )

    def test_reversa_simple_ok(self):
        transferencia = TransferenciaPresupuestaria.objects.create(
            presupuesto_anual=self.presupuesto,
            renglon_origen=self.origen,
            renglon_destino=self.destino_1,
            monto=Decimal('50.00'),
            descripcion='Simple',
        )
        response = self.client.post(
            reverse('scompras:reversar_transferencia', args=[transferencia.id]),
            {'motivo': 'Ajuste contable'},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('1000.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('100.00'))

    def test_reversa_multiple_ok(self):
        t1 = TransferenciaPresupuestaria.objects.create(
            presupuesto_anual=self.presupuesto,
            renglon_origen=self.origen,
            renglon_destino=self.destino_1,
            monto=Decimal('50.00'),
            descripcion='Multiple',
        )
        t2 = TransferenciaPresupuestaria.objects.create(
            presupuesto_anual=self.presupuesto,
            renglon_origen=self.origen,
            renglon_destino=self.destino_2,
            monto=Decimal('25.00'),
            descripcion='Multiple',
        )
        self.client.post(reverse('scompras:reversar_transferencia', args=[t1.id]), {'motivo': 'Ajuste 1'})
        self.client.post(reverse('scompras:reversar_transferencia', args=[t2.id]), {'motivo': 'Ajuste 2'})

        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.destino_2.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('1000.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('100.00'))
        self.assertEqual(self.destino_2.monto_disponible, Decimal('100.00'))

    def test_no_permite_reversa_doble(self):
        transferencia = TransferenciaPresupuestaria.objects.create(
            presupuesto_anual=self.presupuesto,
            renglon_origen=self.origen,
            renglon_destino=self.destino_1,
            monto=Decimal('20.00'),
            descripcion='Simple',
        )
        self.client.post(reverse('scompras:reversar_transferencia', args=[transferencia.id]), {'motivo': 'Ajuste 1'})
        response = self.client.post(
            reverse('scompras:reversar_transferencia', args=[transferencia.id]),
            {'motivo': 'Ajuste 2'},
            follow=True,
        )

        self.assertContains(response, 'ya fue revertida', status_code=200)
        self.assertEqual(
            KardexPresupuesto.objects.filter(
                transferencia=transferencia,
                referencia__startswith='REVERSA|Transferencia #',
            ).count(),
            2,
        )

    def test_reversa_sin_stock_en_destino_hace_rollback(self):
        transferencia = TransferenciaPresupuestaria.objects.create(
            presupuesto_anual=self.presupuesto,
            renglon_origen=self.origen,
            renglon_destino=self.destino_1,
            monto=Decimal('80.00'),
            descripcion='Simple',
        )

        self.destino_1.monto_modificado -= Decimal('80.00')
        self.destino_1.save(update_fields=['monto_modificado', 'fecha_actualizacion'])

        response = self.client.post(
            reverse('scompras:reversar_transferencia', args=[transferencia.id]),
            {'motivo': 'Intento inválido'},
            follow=True,
        )

        self.assertContains(response, 'no tiene disponible suficiente', status_code=200)
        self.origen.refresh_from_db()
        self.destino_1.refresh_from_db()
        self.assertEqual(self.origen.monto_disponible, Decimal('920.00'))
        self.assertEqual(self.destino_1.monto_disponible, Decimal('0.00'))
