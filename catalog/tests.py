from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Doll, DollPhoto, SiteSettings


def upload(name="test.png", size=(80, 100)):
    output = BytesIO()
    Image.new("RGB", size, "green").save(output, "PNG")
    return SimpleUploadedFile(name, output.getvalue(), content_type="image/png")


@override_settings(
    SECURE_SSL_REDIRECT=False,
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    },
)
class WorkshopTests(TestCase):
    def setUp(self):
        self.media = TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        settings = override_settings(MEDIA_ROOT=self.media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        self.published = Doll.objects.create(
            title="Матушка",
            slug="matushka",
            is_published=True,
            is_featured=True,
        )
        self.draft = Doll.objects.create(title="Черновик", slug="draft", is_featured=True)
        self.photo = DollPhoto.objects.create(doll=self.published, image=upload())
        self.draft_photo = DollPhoto.objects.create(doll=self.draft, image=upload())

    def test_public_pages_and_draft_visibility(self):
        for name in ["home", "catalog", "about", "ordering"]:
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, "Черновик")
        response = self.client.get(self.published.get_absolute_url())
        self.assertContains(response, "Матушка")
        self.assertNotContains(response, "Черновик")
        self.assertEqual(self.client.get(self.draft.get_absolute_url()).status_code, 404)

    def test_photos_are_cacheable_and_accessible_by_direct_url(self):
        response = self.client.get(self.photo.image.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/webp")
        self.assertEqual(response["Cache-Control"], "public, max-age=31536000, immutable")
        response.close()
        response = self.client.get(self.draft_photo.image.url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.published.is_published = False
        self.published.save()
        response = self.client.get(self.photo.image.url)
        self.assertEqual(response.status_code, 200)
        response.close()
        self.assertEqual(self.client.get(self.published.get_absolute_url()).status_code, 404)
        self.assertNotContains(self.client.get(reverse("catalog")), self.published.title)
        self.assertEqual(self.client.get("/media/dolls/" + "0" * 32 + ".webp").status_code, 404)
        self.assertEqual(self.client.get("/media/dolls/../../config/settings.py").status_code, 404)

    def test_filter_and_invalid_filter(self):
        available = Doll.objects.create(
            title="В наличии",
            slug="available",
            is_published=True,
            availability=Doll.Availability.AVAILABLE,
        )
        response = self.client.get(reverse("catalog"), {"status": "available"})
        self.assertContains(response, available.get_absolute_url())
        self.assertNotContains(response, self.published.get_absolute_url())
        response = self.client.get(reverse("catalog"), {"status": "invalid"})
        self.assertContains(response, self.published.get_absolute_url())

    def test_pagination(self):
        for i in range(14):
            Doll.objects.create(title=f"Кукла {i}", slug=f"doll-{i}", is_published=True)
        response = self.client.get(reverse("catalog"))
        self.assertEqual(len(response.context["page_obj"]), 12)
        response = self.client.get(reverse("catalog"), {"page": "2"})
        self.assertEqual(len(response.context["page_obj"]), 3)
        self.assertEqual(self.client.get(reverse("catalog"), {"page": "bad"}).status_code, 200)

    def test_photo_conversion_and_order(self):
        other = DollPhoto.objects.create(
            doll=self.published,
            image=upload(size=(2200, 1600)),
            position=0,
        )
        self.photo.position = 2
        self.photo.save()
        self.assertEqual(self.published.cover, other)
        with Image.open(other.image.path) as image:
            self.assertEqual(image.format, "WEBP")
            self.assertEqual(max(image.size), 1800)
            self.assertFalse(image.getexif())
        self.assertRegex(Path(other.image.name).name, r"^[a-f0-9]{32}\.webp$")

    def test_invalid_and_oversized_uploads_are_rejected(self):
        invalid = DollPhoto(doll=self.published, image=SimpleUploadedFile("bad.png", b"bad"))
        with self.assertRaises(ValidationError):
            invalid.full_clean()
        oversized = SimpleUploadedFile("huge.png", b"x" * (12 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            DollPhoto(doll=self.published, image=oversized).full_clean()
        with self.assertRaises(ValidationError):
            DollPhoto(doll=self.published, image=upload(size=(6000, 4100))).full_clean()

    def test_description_is_escaped_and_optional_price(self):
        self.published.description = '<script>alert("x")</script>'
        self.published.price = 0
        self.published.save()
        response = self.client.get(self.published.get_absolute_url())
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("x")</script>')
        self.assertContains(response, "0 ₽")

    def test_contact_settings_and_singleton(self):
        settings = SiteSettings.objects.create(
            contact_url="https://t.me/example",
            contact_label="Связаться",
            about="О мастерице",
        )
        self.assertContains(self.client.get(reverse("ordering")), "https://t.me/example")
        self.assertContains(self.client.get(reverse("about")), "О мастерице")
        settings.contact_url = "javascript:alert(1)"
        with self.assertRaises(ValidationError):
            settings.full_clean()
        SiteSettings(name="Другое название").save()
        self.assertEqual(SiteSettings.objects.count(), 1)

    def test_missing_contacts_do_not_create_fake_links(self):
        response = self.client.get(reverse("ordering"))
        self.assertContains(response, "Контакты мастерской скоро появятся здесь.")
        self.assertNotContains(response, "mailto:")

    def create_editor(self):
        with patch(
            "catalog.management.commands.create_editor.getpass",
            return_value="a-strong-editor-pass-782!",
        ):
            call_command("create_editor", "editor", stdout=StringIO())
        return get_user_model().objects.get(username="editor")

    def test_editor_can_edit_content_but_not_users_or_permissions(self):
        editor = self.create_editor()
        self.assertTrue(editor.is_staff)
        self.assertFalse(editor.is_superuser)
        self.client.force_login(editor)
        self.assertEqual(self.client.get(reverse("admin:catalog_doll_changelist")).status_code, 200)
        self.assertEqual(self.client.get(reverse("admin:auth_user_changelist")).status_code, 403)
        self.assertEqual(self.client.get(reverse("admin:auth_group_changelist")).status_code, 403)
        response = self.client.get(reverse("admin:catalog_doll_change", args=[self.draft.pk]))
        self.assertContains(response, "Черновик")
        response = self.client.get(reverse("admin:catalog_doll_photo", args=[self.draft_photo.pk]))
        self.assertEqual(response.status_code, 200)
        response.close()
        response = self.client.get(self.draft_photo.image.url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_anonymous_admin_access_redirects_to_login(self):
        response = self.client.get(reverse("admin:catalog_doll_changelist"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response.url)
        response = self.client.get(reverse("admin:catalog_doll_photo", args=[self.draft_photo.pk]))
        self.assertEqual(response.status_code, 302)

    def test_admin_add_item_with_photo_and_publish(self):
        self.client.force_login(self.create_editor())
        response = self.client.post(
            reverse("admin:catalog_doll_add"),
            {
                "title": "Новая кукла",
                "slug": "new-doll",
                "description": "Описание",
                "materials": "Лён",
                "dimensions": "15 см",
                "availability": "available",
                "is_published": "on",
                "position": "0",
                "photos-TOTAL_FORMS": "1",
                "photos-INITIAL_FORMS": "0",
                "photos-MIN_NUM_FORMS": "0",
                "photos-MAX_NUM_FORMS": "1000",
                "photos-0-image": upload(),
                "photos-0-alt": "Новая кукла",
                "photos-0-position": "0",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 302)
        doll = Doll.objects.get(slug="new-doll")
        self.assertEqual(doll.photos.count(), 1)
        self.assertContains(self.client.get(doll.get_absolute_url()), "Описание")

    def test_admin_handles_invalid_photo_without_server_error(self):
        self.client.force_login(self.create_editor())
        response = self.client.post(
            reverse("admin:catalog_doll_add"),
            {
                "title": "Новая",
                "slug": "invalid",
                "availability": "to_order",
                "position": "0",
                "photos-TOTAL_FORMS": "1",
                "photos-INITIAL_FORMS": "0",
                "photos-MIN_NUM_FORMS": "0",
                "photos-MAX_NUM_FORMS": "1000",
                "photos-0-image": upload(size=(6000, 4100)),
                "photos-0-position": "0",
                "_save": "Сохранить",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "24 мегапикселей")
        self.assertFalse(Doll.objects.filter(slug="invalid").exists())

    def test_import_is_idempotent_and_defaults_to_drafts(self):
        from .management.commands.import_photos import ITEMS

        with TemporaryDirectory() as directory:
            for _, _, names in ITEMS:
                for name in names:
                    Path(directory, name).write_bytes(upload().read())
            # Existing published item must not be overwritten by the import.
            call_command("import_photos", directory, stdout=StringIO())
            count = Doll.objects.count()
            photo_count = DollPhoto.objects.count()
            imported = Doll.objects.get(slug="zernovushka")
            self.assertFalse(imported.is_published)
            self.assertEqual(self.client.get(imported.get_absolute_url()).status_code, 404)
            call_command("import_photos", directory, publish=True, stdout=StringIO())
            self.assertEqual(Doll.objects.count(), count)
            self.assertEqual(DollPhoto.objects.count(), photo_count)
            imported.refresh_from_db()
            self.assertFalse(imported.is_published)
            self.published.refresh_from_db()
            self.assertTrue(self.published.is_published)
