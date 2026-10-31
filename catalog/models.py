from io import BytesIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from PIL import Image, ImageOps, UnidentifiedImageError


def validate_image_size(value):
    if value.size > 12 * 1024 * 1024:
        raise ValidationError("Фотография должна быть не больше 12 МБ.")
    try:
        value.seek(0)
        with Image.open(value) as image:
            if image.width * image.height > 24_000_000:
                raise ValidationError("Фотография должна быть не больше 24 мегапикселей.")
            if image.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValidationError("Используйте JPEG, PNG или WebP.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValidationError("Не удалось прочитать фотографию.") from error
    finally:
        value.seek(0)


class Doll(models.Model):
    class Availability(models.TextChoices):
        AVAILABLE = "available", "В наличии"
        TO_ORDER = "to_order", "На заказ"
        SOLD = "sold", "Нашла свой дом"

    title = models.CharField("Название", max_length=160)
    slug = models.SlugField(
        "Адрес страницы", unique=True, help_text="Латиницей, например: matushka"
    )
    description = models.TextField("Описание", blank=True)
    materials = models.CharField("Материалы", max_length=250, blank=True)
    dimensions = models.CharField("Размеры", max_length=120, blank=True)
    price = models.DecimalField(
        "Цена, ₽",
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        help_text="Оставьте пустым, чтобы не показывать цену.",
    )
    availability = models.CharField(
        "Наличие",
        max_length=20,
        choices=Availability.choices,
        default=Availability.TO_ORDER,
    )
    is_published = models.BooleanField("Опубликовано", default=False)
    is_featured = models.BooleanField("На главной", default=False)
    position = models.PositiveIntegerField("Порядок", default=0)
    updated_at = models.DateTimeField("Изменено", auto_now=True)

    class Meta:
        ordering = ["position", "pk"]
        verbose_name = "изделие"
        verbose_name_plural = "Изделия"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("doll", kwargs={"slug": self.slug})

    @property
    def cover(self):
        return next(iter(self.photos.all()), None)


class DollPhoto(models.Model):
    doll = models.ForeignKey(Doll, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(
        "Фотография",
        upload_to="dolls/",
        validators=[validate_image_size],
        help_text="JPEG, PNG или WebP, до 12 МБ. Первая по порядку — обложка.",
    )
    alt = models.CharField("Описание фотографии", max_length=250, blank=True)
    position = models.PositiveIntegerField("Порядок", default=0)

    class Meta:
        ordering = ["position", "pk"]
        verbose_name = "фотография"
        verbose_name_plural = "Фотографии"

    def __str__(self):
        return self.alt or f"Фотография: {self.doll}"

    def save(self, *args, **kwargs):
        if self.image and not self.image._committed:
            validate_image_size(self.image)
            try:
                self.image.seek(0)
                with Image.open(self.image) as original:
                    if original.width * original.height > 24_000_000:
                        raise ValidationError("Фотография должна быть не больше 24 мегапикселей.")
                    photo = ImageOps.exif_transpose(original).convert("RGB")
                    photo.thumbnail((1800, 1800))
                    output = BytesIO()
                    photo.save(output, "WEBP", quality=85)
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
                raise ValidationError("Не удалось прочитать фотографию.") from error
            self.image.save(f"{uuid4().hex}.webp", ContentFile(output.getvalue()), save=False)
        super().save(*args, **kwargs)


class SiteSettings(models.Model):
    name = models.CharField("Название мастерской", max_length=100, default="Обережка")
    introduction = models.TextField(
        "Текст на главной",
        default="Ткань, нити и тепло рук. Куклы, которые хочется рассмотреть поближе.",
    )
    about = models.TextField(
        "О мастерской",
        blank=True,
        help_text="Расскажите о мастерице, её материалах и процессе работы.",
    )
    ordering = models.TextField(
        "Как заказать",
        default="Напишите, какая кукла вам понравилась. Обсудим детали и доставку лично.",
    )
    contact_url = models.URLField(
        "Ссылка для связи",
        blank=True,
        help_text="Например, ссылка на Telegram или ВКонтакте.",
    )
    contact_label = models.CharField("Текст кнопки", max_length=80, default="Написать мастерице")
    email = models.EmailField("Почта", blank=True)

    class Meta:
        verbose_name = "настройки мастерской"
        verbose_name_plural = "Настройки мастерской"
        constraints = [
            models.CheckConstraint(condition=models.Q(pk=1), name="single_site_settings")
        ]

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
