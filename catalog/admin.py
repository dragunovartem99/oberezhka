from django.contrib import admin
from django.http import FileResponse, Http404
from django.urls import path, reverse
from django.utils.html import format_html

from .models import Doll, DollPhoto, SiteSettings

admin.site.site_header = "Обережка · Мастерская"
admin.site.site_title = "Обережка"
admin.site.index_title = "Управление мастерской"


class DollPhotoInline(admin.TabularInline):
    model = DollPhoto
    extra = 1
    fields = ["preview", "image", "alt", "position"]
    readonly_fields = ["preview"]

    @admin.display(description="Просмотр")
    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html(
                '<img src="{}" alt="" width="100" loading="lazy">',
                reverse("admin:catalog_doll_photo", args=[obj.pk]),
            )
        return "—"


@admin.register(Doll)
class DollAdmin(admin.ModelAdmin):
    list_display = ["title", "availability", "is_published", "is_featured", "position"]
    list_editable = ["availability", "is_published", "is_featured", "position"]
    list_filter = ["is_published", "availability", "is_featured"]
    search_fields = ["title", "description"]
    prepopulated_fields = {"slug": ["title"]}
    inlines = [DollPhotoInline]

    def get_urls(self):
        return [
            path(
                "photo/<int:photo_id>/",
                self.admin_site.admin_view(self.photo),
                name="catalog_doll_photo",
            )
        ] + super().get_urls()

    def photo(self, request, photo_id):
        photo = DollPhoto.objects.select_related("doll").filter(pk=photo_id).first()
        if photo is None or not self.has_view_or_change_permission(request, photo.doll):
            raise Http404
        return FileResponse(photo.image.open("rb"), content_type="image/webp")

    fieldsets = [
        (None, {"fields": ["title", "slug", "description"]}),
        ("Подробности", {"fields": ["materials", "dimensions", "price", "availability"]}),
        ("Публикация", {"fields": ["is_published", "is_featured", "position"]}),
    ]


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    fields = ["name", "introduction", "about", "ordering", "contact_url", "contact_label", "email"]

    def has_add_permission(self, request):
        return not SiteSettings.objects.exists() and super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False
