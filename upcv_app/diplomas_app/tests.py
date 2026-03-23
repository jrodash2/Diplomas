from datetime import date

from django.contrib.auth.models import Group, User
from django.test import Client, TestCase
from django.urls import reverse

from .models import Curso, DisenoDiploma, Firma, UbicacionDiploma, UsuarioUbicacionDiploma


class DiplomasScopeTests(TestCase):
    def setUp(self):
        self.group_admin, _ = Group.objects.get_or_create(name="Diplomas")
        self.group_manager, _ = Group.objects.get_or_create(name="Gestor_Diplomas")

        self.admin = User.objects.create_user(username="admin_diplomas", password="test12345")
        self.admin.groups.add(self.group_admin)

        self.manager = User.objects.create_user(username="gestor_diplomas", password="test12345")
        self.manager.groups.add(self.group_manager)

        self.ubicacion_a = UbicacionDiploma.objects.create(nombre="Sede Central", activa=True)
        self.ubicacion_b = UbicacionDiploma.objects.create(nombre="Sede Norte", activa=True)
        UsuarioUbicacionDiploma.objects.create(usuario=self.manager, ubicacion=self.ubicacion_a, asignado_por=self.admin)

        self.firma_a = Firma.objects.create(nombre="Firma A", rol="Director", firma="firmas/a.png", ubicacion=self.ubicacion_a)
        self.firma_b = Firma.objects.create(nombre="Firma B", rol="Director", firma="firmas/b.png", ubicacion=self.ubicacion_b)

        self.diseno_a = DisenoDiploma.objects.create(nombre="Diseño A", activo=True, ubicacion=self.ubicacion_a)
        self.diseno_b = DisenoDiploma.objects.create(nombre="Diseño B", activo=True, ubicacion=self.ubicacion_b)

        self.curso_a = Curso.objects.create(
            ubicacion=self.ubicacion_a,
            codigo="10001",
            nombre="Curso A",
            descripcion="Desc A",
            fecha_inicio=date(2026, 1, 1),
            fecha_fin=date(2026, 1, 2),
            diseno_diploma=self.diseno_a,
        )
        self.curso_a.firmas.add(self.firma_a)

        self.curso_b = Curso.objects.create(
            ubicacion=self.ubicacion_b,
            codigo="10002",
            nombre="Curso B",
            descripcion="Desc B",
            fecha_inicio=date(2026, 2, 1),
            fecha_fin=date(2026, 2, 2),
            diseno_diploma=self.diseno_b,
        )
        self.curso_b.firmas.add(self.firma_b)

        self.client = Client()

    def test_admin_sees_all_courses(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.get(reverse("diplomas:cursos_lista"))
        self.assertEqual(response.status_code, 200)
        cursos = list(response.context["cursos"])
        self.assertEqual({curso.id for curso in cursos}, {self.curso_a.id, self.curso_b.id})

    def test_manager_only_sees_own_location_courses(self):
        self.client.login(username="gestor_diplomas", password="test12345")
        response = self.client.get(reverse("diplomas:cursos_lista"))
        self.assertEqual(response.status_code, 200)
        cursos = list(response.context["cursos"])
        self.assertEqual([curso.id for curso in cursos], [self.curso_a.id])
        self.assertContains(response, "Sede Central")
        self.assertNotContains(response, "Curso B")

    def test_manager_cannot_access_foreign_course_detail_by_url(self):
        self.client.login(username="gestor_diplomas", password="test12345")
        response = self.client.get(reverse("diplomas:detalle_curso", args=[self.curso_b.id]))
        self.assertEqual(response.status_code, 403)

    def test_manager_creation_is_forced_to_assigned_location(self):
        self.client.login(username="gestor_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:crear_curso_modal"),
            {
                "ubicacion": self.ubicacion_b.id,
                "codigo": "10003",
                "nombre": "Curso Gestor",
                "descripcion": "Texto",
                "fecha_inicio": "2026-03-01",
                "fecha_fin": "2026-03-02",
                "firmas": [self.firma_a.id],
                "diseno_diploma": self.diseno_a.id,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        curso = Curso.objects.get(codigo="10003")
        self.assertEqual(curso.ubicacion, self.ubicacion_a)

    def test_admin_can_create_assignment(self):
        new_manager = User.objects.create_user(username="gestor2", password="test12345")
        new_manager.groups.add(self.group_manager)
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:crear_asignacion_ubicacion"),
            {"usuario": new_manager.id, "ubicacion": self.ubicacion_b.id},
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UsuarioUbicacionDiploma.objects.filter(usuario=new_manager, ubicacion=self.ubicacion_b).exists())
