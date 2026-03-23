from datetime import date
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.test.utils import override_settings

from empleados_app.models import DatosBasicosEmpleado, Empleado

from .design_engine import build_diploma_render_context
from .models import Curso, CursoEmpleado, DisenoDiploma, Firma, UbicacionDiploma, UsuarioUbicacionDiploma


TEST_PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\rIDATx\x9cc`\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


class DiplomasScopeTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_dir = TemporaryDirectory()
        cls._override = override_settings(MEDIA_ROOT=cls._media_dir.name)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        cls._media_dir.cleanup()
        super().tearDownClass()

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

        self.empleado = Empleado.objects.create(
            dpi="1234567890101",
            nombres="Ana",
            apellidos="Prueba",
            tipoc="029",
            activo=True,
        )
        self.datos_basicos = DatosBasicosEmpleado.objects.create(
            empleado=self.empleado,
            telefono_personal="4444-5555",
            correo_institucional="ana@example.com",
        )
        self.participante = self.curso_a.participantes.create(empleado=self.empleado)

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

    def test_manager_course_detail_shows_public_links_for_current_course(self):
        self.client.login(username="gestor_diplomas", password="test12345")
        response = self.client.get(reverse("diplomas:detalle_curso", args=[self.curso_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Enlaces para participantes")
        self.assertContains(response, "Abrir registro")
        self.assertContains(response, "Copiar link")
        self.assertContains(response, reverse("diplomas:public_course_registration"))
        self.assertContains(response, reverse("diplomas:public_diploma_download"))
        self.assertContains(response, f"codigo_curso={self.curso_a.codigo}")
        self.assertNotContains(response, 'class="form-control js-public-link"')

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

    def test_editor_can_upload_custom_image_asset(self):
        self.client.login(username="admin_diplomas", password="test12345")
        upload = SimpleUploadedFile("sello.png", TEST_PNG_BYTES, content_type="image/png")
        response = self.client.post(
            reverse("diplomas:subir_imagen_diseno_visual", args=[self.diseno_a.id]),
            {"image": upload},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["success"])
        self.assertIn("/media/diplomas/editor/", payload["image_url"])

    def test_editor_persists_custom_text_and_image_for_render(self):
        self.client.login(username="admin_diplomas", password="test12345")
        upload = SimpleUploadedFile("logo-extra.png", TEST_PNG_BYTES, content_type="image/png")
        upload_response = self.client.post(
            reverse("diplomas:subir_imagen_diseno_visual", args=[self.diseno_a.id]),
            {"image": upload},
        )
        self.assertEqual(upload_response.status_code, 200)
        image_url = upload_response.json()["image_url"]

        save_response = self.client.post(
            reverse("diplomas:guardar_diseno_visual", args=[self.diseno_a.id]),
            data={
                "elementos": {
                    "custom_text_demo": {
                        "key": "custom_text_demo",
                        "label": "Leyenda especial",
                        "type": "text",
                        "texto": "Texto libre para diploma",
                        "x": 200,
                        "y": 300,
                        "width": 900,
                        "height": 160,
                        "font_size": 40,
                        "font_family": 'Arial, "Helvetica Neue", Helvetica, sans-serif',
                        "font_weight": "700",
                        "color": "#123456",
                        "align": "left",
                        "visible": True,
                        "z_index": 88,
                    },
                    "custom_image_demo": {
                        "key": "custom_image_demo",
                        "label": "Sello adicional",
                        "type": "image",
                        "image_url": image_url,
                        "x": 1200,
                        "y": 250,
                        "width": 240,
                        "height": 240,
                        "visible": True,
                        "z_index": 89,
                    },
                }
            },
            content_type="application/json",
        )
        self.assertEqual(save_response.status_code, 200)
        self.diseno_a.refresh_from_db()

        elements = self.diseno_a.estilos["elements"]
        self.assertIn("custom_text_demo", elements)
        self.assertEqual(elements["custom_text_demo"]["type"], "texto")
        self.assertEqual(elements["custom_text_demo"]["texto"], "Texto libre para diploma")
        self.assertIn("custom_image_demo", elements)
        self.assertEqual(elements["custom_image_demo"]["type"], "imagen")
        self.assertEqual(elements["custom_image_demo"]["image_url"], image_url)

        render_context = build_diploma_render_context(self.participante)
        render_map = {item["key"]: item for item in render_context["render_elements"]}
        self.assertIn("custom_text_demo", render_map)
        self.assertEqual(render_map["custom_text_demo"]["rendered_value"], "Texto libre para diploma")
        self.assertIn("custom_image_demo", render_map)
        self.assertEqual(render_map["custom_image_demo"]["image_url"], image_url)

    def test_manual_enrollment_accepts_required_fields_only(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:agregar_empleado_detalle", args=[self.curso_a.id]),
            {
                "curso": self.curso_a.id,
                "participante_dpi": "5555555550101",
                "participante_nombre": "Participante Manual",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        participante = CursoEmpleado.objects.get(curso=self.curso_a, participante_dpi="5555555550101")
        self.assertIsNone(participante.empleado)
        self.assertEqual(participante.nombre_participante, "Participante Manual")
        self.assertEqual(participante.participante_correo, "")
        self.assertEqual(participante.participante_telefono, "")
        self.assertEqual(participante.observaciones, "")

    def test_manual_enrollment_stores_optional_fields_and_photo(self):
        self.client.login(username="admin_diplomas", password="test12345")
        upload = SimpleUploadedFile("participante.png", TEST_PNG_BYTES, content_type="image/png")
        response = self.client.post(
            reverse("diplomas:agregar_empleado_detalle", args=[self.curso_a.id]),
            {
                "curso": self.curso_a.id,
                "participante_dpi": "6666666660101",
                "participante_nombre": "Participante Opcional",
                "participante_correo": "manual@example.com",
                "participante_telefono": "5555-0000",
                "observaciones": "Participante agregado manualmente",
                "participante_foto": upload,
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        participante = CursoEmpleado.objects.get(curso=self.curso_a, participante_dpi="6666666660101")
        self.assertEqual(participante.participante_correo, "manual@example.com")
        self.assertEqual(participante.participante_telefono, "5555-0000")
        self.assertEqual(participante.observaciones, "Participante agregado manualmente")
        self.assertTrue(bool(participante.participante_foto))

    def test_existing_dpi_enrollment_still_links_employee(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:agregar_empleado_detalle", args=[self.curso_b.id]),
            {
                "enrollment_mode": "quick",
                "curso": self.curso_b.id,
                "dpi": self.empleado.dpi,
                "nombre_completo": f"{self.empleado.nombres} {self.empleado.apellidos}",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        participante = CursoEmpleado.objects.get(curso=self.curso_b, participante_dpi=self.empleado.dpi)
        self.assertEqual(participante.empleado, self.empleado)

    def test_participant_table_fallbacks_use_employee_contact_data(self):
        self.assertEqual(self.participante.correo_participante, "ana@example.com")
        self.assertEqual(self.participante.telefono_participante, "4444-5555")
        self.assertEqual(self.participante.observaciones_participante, "")

    def test_quick_enrollment_rejects_unknown_dpi(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:agregar_empleado_detalle", args=[self.curso_b.id]),
            {
                "enrollment_mode": "quick",
                "curso": self.curso_b.id,
                "dpi": "9999999990101",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CursoEmpleado.objects.filter(curso=self.curso_b, participante_dpi="9999999990101").exists())

    def test_public_course_lookup_returns_course_name(self):
        response = self.client.get(reverse("diplomas:public_buscar_curso_por_codigo"), {"codigo_curso": self.curso_a.codigo})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["existe"])
        self.assertEqual(payload["nombre"], self.curso_a.nombre)

    def test_public_participant_lookup_returns_course_participant(self):
        response = self.client.get(
            reverse("diplomas:public_buscar_participante_por_dpi"),
            {"codigo_curso": self.curso_a.codigo, "dpi": "1234 56789 0101"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["existe"])
        self.assertTrue(payload["inscrito_en_curso"])
        self.assertEqual(payload["nombre_completo"], self.participante.nombre_participante)

    def test_public_registration_creates_manual_participant(self):
        response = self.client.post(
            reverse("diplomas:public_course_registration"),
            {
                "codigo_curso": self.curso_b.codigo,
                "dpi": "7777 77777 0101",
                "participante_nombre": "Registro Público",
                "participante_correo": "publico@example.com",
                "participante_telefono": "3333-2222",
                "observaciones": "Alta por formulario público",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        participante = CursoEmpleado.objects.get(curso=self.curso_b, participante_dpi="7777777770101")
        self.assertEqual(participante.participante_nombre, "Registro Público")
        self.assertEqual(participante.participante_correo, "publico@example.com")
        self.assertContains(response, "Registro completado correctamente")

    def test_public_registration_links_existing_employee_when_dpi_has_spaces(self):
        response = self.client.post(
            reverse("diplomas:public_course_registration"),
            {
                "codigo_curso": self.curso_b.codigo,
                "dpi": "1234 56789 0101",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        participante = CursoEmpleado.objects.get(curso=self.curso_b, empleado=self.empleado)
        self.assertEqual(participante.participante_dpi, "1234567890101")
        self.assertEqual(participante.participante_nombre, "Ana Prueba")

    def test_public_diploma_download_renders_diploma_for_registered_participant(self):
        response = self.client.post(
            reverse("diplomas:public_diploma_download"),
            {
                "codigo_curso": self.curso_a.codigo,
                "dpi": "1234 56789 0101",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.participante.nombre_participante)
        self.assertTemplateUsed(response, "diplomas/ver_diploma.html")
        self.assertContains(response, 'class="diploma-image-media"')
        self.assertContains(response, 'data-diploma-image-shape="rect"')
        self.assertContains(response, "diploma-export-fitted-image")

    def test_public_diploma_download_shows_clear_message_when_employee_is_not_enrolled(self):
        response = self.client.post(
            reverse("diplomas:public_diploma_download"),
            {
                "codigo_curso": self.curso_b.codigo,
                "dpi": "1234 56789 0101",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El participante existe, pero no está inscrito en ese curso.")

    def test_public_pages_prefill_course_code_from_querystring(self):
        registration_response = self.client.get(
            reverse("diplomas:public_course_registration"),
            {"codigo_curso": self.curso_a.codigo},
        )
        self.assertEqual(registration_response.status_code, 200)
        self.assertContains(registration_response, f'value="{self.curso_a.codigo}"')
        self.assertContains(registration_response, self.curso_a.nombre)

        download_response = self.client.get(
            reverse("diplomas:public_diploma_download"),
            {"codigo_curso": self.curso_a.codigo},
        )
        self.assertEqual(download_response.status_code, 200)
        self.assertContains(download_response, f'value="{self.curso_a.codigo}"')
        self.assertContains(download_response, self.curso_a.nombre)
