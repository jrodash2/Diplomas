from datetime import date, timedelta
from tempfile import TemporaryDirectory

from django.contrib.auth.models import Group, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings

from empleados_app.models import ConfiguracionGeneral, DatosBasicosEmpleado, Empleado

from .design_engine import build_diploma_render_context
from .models import Curso, CursoEmpleado, Diploma, DisenoDiploma, Firma, UbicacionDiploma, UsuarioUbicacionDiploma
from .views import get_course_diploma_download_status


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

        self.ubicacion_a = UbicacionDiploma.objects.create(nombre="Sede Central", abreviatura="SC", activa=True)
        self.ubicacion_b = UbicacionDiploma.objects.create(nombre="Sede Norte", abreviatura="SN", activa=True)
        UsuarioUbicacionDiploma.objects.create(usuario=self.manager, ubicacion=self.ubicacion_a, asignado_por=self.admin)

        self.firma_a = Firma.objects.create(nombre="Firma A", rol="Director", firma="firmas/a.png", ubicacion=self.ubicacion_a)
        self.firma_b = Firma.objects.create(nombre="Firma B", rol="Director", firma="firmas/b.png", ubicacion=self.ubicacion_b)
        self.configuracion = ConfiguracionGeneral.objects.create(
            nombre_institucion="UPCV Inicial",
            direccion="Ciudad",
        )

        self.diseno_a = DisenoDiploma.objects.create(nombre="Diseño A", activo=True, ubicacion=self.ubicacion_a)
        self.diseno_b = DisenoDiploma.objects.create(nombre="Diseño B", activo=True, ubicacion=self.ubicacion_b)

        today = timezone.localdate()

        self.curso_a = Curso.objects.create(
            ubicacion=self.ubicacion_a,
            codigo="10001",
            nombre="Curso A",
            descripcion="Desc A",
            fecha_inicio=today - timedelta(days=10),
            fecha_fin=today - timedelta(days=1),
            diseno_diploma=self.diseno_a,
        )
        self.curso_a.firmas.add(self.firma_a)

        self.curso_b = Curso.objects.create(
            ubicacion=self.ubicacion_b,
            codigo="10002",
            nombre="Curso B",
            descripcion="Desc B",
            fecha_inicio=today - timedelta(days=2),
            fecha_fin=today + timedelta(days=10),
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
        self.participante_curso_abierto = self.curso_b.participantes.create(
            participante_dpi="5554443330101",
            participante_nombre="Participante Abierto",
        )

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
        upload = SimpleUploadedFile("imagen-extra.png", TEST_PNG_BYTES, content_type="image/png")
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
                        "label": "Imagen adicional",
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
        self.participante.refresh_from_db()
        self.assertTrue(Diploma.objects.filter(curso_empleado=self.participante).exists())
        self.assertEqual(self.participante.diploma.numero_diploma, "UPCV-SC-0001-2026")

    def test_diploma_number_is_scoped_per_location(self):
        participant_same_location = self.curso_a.participantes.create(
            participante_dpi="9999999990101",
            participante_nombre="Segundo Participante",
        )
        participant_other_location = self.curso_b.participantes.create(
            participante_dpi="8888888880101",
            participante_nombre="Participante Norte",
        )

        diploma_a1 = Diploma.ensure_for_course_employee(self.participante)
        diploma_a2 = Diploma.ensure_for_course_employee(participant_same_location)
        diploma_b1 = Diploma.ensure_for_course_employee(participant_other_location)

        self.assertEqual(diploma_a1.numero_diploma, "UPCV-SC-0001-2026")
        self.assertEqual(diploma_a2.numero_diploma, "UPCV-SC-0002-2026")
        self.assertEqual(diploma_b1.numero_diploma, "UPCV-SN-0001-2026")

    def test_public_diploma_download_shows_clear_message_when_employee_is_not_enrolled(self):
        empleado_no_inscrito = Empleado.objects.create(
            dpi="3216549870101",
            nombres="No",
            apellidos="Inscrito",
            tipoc="029",
            activo=True,
        )
        response = self.client.post(
            reverse("diplomas:public_diploma_download"),
            {
                "codigo_curso": self.curso_a.codigo,
                "dpi": empleado_no_inscrito.dpi,
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

    def test_public_pages_show_location_context_and_branding(self):
        response = self.client.get(
            reverse("diplomas:public_course_registration"),
            {"codigo_curso": self.curso_a.codigo},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ubicación:")
        self.assertContains(response, self.curso_a.ubicacion.nombre)

        lookup_response = self.client.get(
            reverse("diplomas:public_buscar_curso_por_codigo"),
            {"codigo_curso": self.curso_a.codigo},
        )
        self.assertEqual(lookup_response.status_code, 200)
        self.assertEqual(lookup_response.json()["ubicacion_abreviatura"], "SC")

    def test_dynamic_institution_text_is_not_frozen_in_saved_design(self):
        self.diseno_a.estilos = {
            "version": 2,
            "canvas": {"width": 3508, "height": 2480},
            "elements": {
                "titulo_institucional": {
                    "key": "titulo_institucional",
                    "type": "texto",
                    "texto": "Texto congelado",
                    "token": "",
                    "x": 900,
                    "y": 300,
                    "width": 1908,
                    "height": 120,
                    "font_size": 54,
                    "font_weight": "700",
                    "z_index": 20,
                    "visible": True,
                },
            },
        }
        self.diseno_a.save(update_fields=["estilos"])
        self.configuracion.nombre_institucion = "UPCV Actualizada"
        self.configuracion.save(update_fields=["nombre_institucion"])

        render_context = build_diploma_render_context(self.participante)
        render_map = {item["key"]: item for item in render_context["render_elements"]}
        self.assertEqual(render_map["titulo_institucional"]["rendered_value"], "UPCV Actualizada")

    def test_signature_updates_and_removed_slots_are_resolved_dynamically(self):
        self.diseno_a.estilos = {
            "version": 2,
            "canvas": {"width": 3508, "height": 2480},
            "elements": {
                "firma_1_nombre": {"key": "firma_1_nombre", "type": "texto", "texto": "Nombre viejo", "token": "", "x": 700, "y": 1700, "width": 600, "height": 50, "z_index": 31},
                "firma_1_cargo": {"key": "firma_1_cargo", "type": "texto", "texto": "Cargo viejo", "token": "", "x": 650, "y": 1760, "width": 700, "height": 50, "z_index": 32},
                "firma_1_imagen": {"key": "firma_1_imagen", "type": "imagen", "image_url": "/media/firmas/vieja.png", "token": "", "x": 760, "y": 1550, "width": 420, "height": 150, "z_index": 30},
                "firma_2_nombre": {"key": "firma_2_nombre", "type": "texto", "texto": "Firma eliminada", "token": "", "x": 2260, "y": 1700, "width": 600, "height": 50, "z_index": 34},
            },
        }
        self.diseno_a.save(update_fields=["estilos"])

        self.firma_a.nombre = "Directora Actualizada"
        self.firma_a.rol = "Dirección General"
        self.firma_a.save(update_fields=["nombre", "rol"])
        self.curso_a.firmas.set([self.firma_a])

        render_context = build_diploma_render_context(self.participante)
        render_map = {item["key"]: item for item in render_context["render_elements"]}
        self.assertEqual(render_map["firma_1_nombre"]["rendered_value"], "Directora Actualizada")
        self.assertEqual(render_map["firma_1_cargo"]["rendered_value"], "Dirección General")
        self.assertNotIn("firma_2_nombre", render_map)

    def test_internal_enrollment_is_blocked_when_course_is_out_of_range(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.post(
            reverse("diplomas:agregar_empleado_detalle", args=[self.curso_a.id]),
            {
                "enrollment_mode": "manual",
                "curso": self.curso_a.id,
                "participante_dpi": "9990001110101",
                "participante_nombre": "Fuera de rango",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CursoEmpleado.objects.filter(curso=self.curso_a, participante_dpi="9990001110101").exists())
        self.assertContains(response, "La inscripción a este curso ha finalizado.")

    def test_public_registration_is_blocked_when_course_is_out_of_range(self):
        response = self.client.post(
            reverse("diplomas:public_course_registration"),
            {
                "codigo_curso": self.curso_a.codigo,
                "dpi": "1231231230101",
                "participante_nombre": "Intento Público",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "La inscripción a este curso ha finalizado.")
        self.assertFalse(CursoEmpleado.objects.filter(curso=self.curso_a, participante_dpi="1231231230101").exists())

    def test_public_download_is_blocked_until_course_has_finished(self):
        participant_open_course = self.curso_b.participantes.create(
            participante_dpi="7777777770101",
            participante_nombre="Curso Abierto",
        )
        response = self.client.post(
            reverse("diplomas:public_diploma_download"),
            {
                "codigo_curso": self.curso_b.codigo,
                "dpi": participant_open_course.participante_dpi,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No se puede descargar el diploma porque el curso aún no ha finalizado.")

    def test_legacy_internal_download_status_helper_does_not_block_open_course(self):
        can_download, message = get_course_diploma_download_status(self.curso_b)
        self.assertTrue(can_download)
        self.assertEqual(message, "")

    def test_internal_preview_and_download_are_available_before_course_end(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.get(
            reverse("diplomas:ver_diploma", args=[self.curso_b.id, self.participante_curso_abierto.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Descargar JPG")
        self.assertNotContains(response, "No se puede descargar el diploma porque el curso aún no ha finalizado.")
        self.assertNotContains(response, 'data-download-locked="true"')

    def test_internal_download_button_is_enabled_when_course_is_finished(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.get(
            reverse("diplomas:ver_diploma", args=[self.curso_a.id, self.participante.id]),
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'data-download-locked="true"')

    def test_internal_course_detail_does_not_show_public_download_block_message(self):
        self.client.login(username="admin_diplomas", password="test12345")
        response = self.client.get(reverse("diplomas:detalle_curso", args=[self.curso_b.id]))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "No se puede descargar el diploma porque el curso aún no ha finalizado.")

    def test_eye_action_points_to_internal_preview_and_allows_download_controls(self):
        self.client.login(username="admin_diplomas", password="test12345")
        detail_response = self.client.get(reverse("diplomas:detalle_curso", args=[self.curso_b.id]))
        self.assertEqual(detail_response.status_code, 200)
        preview_url = reverse("diplomas:ver_diploma", args=[self.curso_b.id, self.participante_curso_abierto.id])
        self.assertContains(detail_response, preview_url)

        preview_response = self.client.get(preview_url)
        self.assertEqual(preview_response.status_code, 200)
        self.assertContains(preview_response, "Descargar JPG")

    def test_public_download_is_blocked_after_six_month_window(self):
        today = timezone.localdate()
        old_course = Curso.objects.create(
            ubicacion=self.ubicacion_a,
            codigo="90001",
            nombre="Curso Antiguo",
            descripcion="Antiguo",
            fecha_inicio=today - timedelta(days=240),
            fecha_fin=today - timedelta(days=220),
            diseno_diploma=self.diseno_a,
        )
        old_course.firmas.add(self.firma_a)
        old_participant = old_course.participantes.create(
            participante_dpi="1010101010101",
            participante_nombre="Participante Antiguo",
        )

        response = self.client.post(
            reverse("diplomas:public_diploma_download"),
            {
                "codigo_curso": old_course.codigo,
                "dpi": old_participant.participante_dpi,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "El plazo disponible para descargar este diploma desde este enlace ya ha vencido.")

    def test_public_download_page_shows_informative_window_message(self):
        response = self.client.get(reverse("diplomas:public_diploma_download"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            "el diploma puede descargarse desde este enlace únicamente hasta 6 meses después de finalizado el curso",
        )
