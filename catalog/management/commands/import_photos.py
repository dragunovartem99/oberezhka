from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalog.models import Doll, DollPhoto, SiteSettings

ITEMS = [
    ("Матушка", "matushka", ["матушка-1.jpg", "матушка-2.jpg"]),
    ("Зерновушка", "zernovushka", ["зерновушка.jpg"]),
    ("Солнцеворот", "solntsevorot", ["солнцеворот-1.jpg", "солнцеворот-2.jpg"]),
    ("Десятиручка", "desyatiruchka", ["десятиручка.jpg"]),
    ("Семейная", "semeynaya", ["семейная.jpg"]),
    ("Зайчата", "zaychata", ["зайчата.jpg"]),
    ("Кулачная", "kulachnaya", ["кулачная.jpg"]),
    ("Обрядовые куклы", "obryadovye", ["обрядовые-1.jpg", "обрядовые-2.jpg"]),
    ("Пасхальная", "paskhalnaya", ["пасхальная.jpg"]),
    (
        "С узелочками",
        "s-uzelochkami",
        ["с-узелочками.jpg", "с-узелочками-2.jpg", "с-узелочками-3.jpg"],
    ),
    ("Мастер", "master", ["мастер.jpg"]),
    ("Подмастерье", "podmasterye", ["подмастерье.jpg"]),
]


class Command(BaseCommand):
    help = "Импорт фотографий без изменения существующих изделий. По умолчанию — черновики."

    def add_arguments(self, parser):
        parser.add_argument("directory", type=Path)
        parser.add_argument("--publish", action="store_true", help="Опубликовать новые изделия.")

    def handle(self, *args, **options):
        directory = options["directory"]
        missing = [
            name for _, _, names in ITEMS for name in names if not (directory / name).is_file()
        ]
        if missing:
            raise CommandError("Не найдены фотографии: " + ", ".join(missing))
        SiteSettings.objects.get_or_create(pk=1)
        count = 0
        for position, (title, slug, names) in enumerate(ITEMS):
            with transaction.atomic():
                doll, created = Doll.objects.get_or_create(
                    slug=slug,
                    defaults={
                        "title": title,
                        "position": position,
                        "is_featured": position < 4,
                        "is_published": options["publish"],
                    },
                )
                if not created:
                    continue
                for index, name in enumerate(names):
                    with (directory / name).open("rb") as source:
                        photo = DollPhoto(doll=doll, alt=title, position=index)
                        photo.image = File(source, name=name)
                        photo.save()
                count += 1
        self.stdout.write(
            self.style.SUCCESS(f"Добавлено изделий: {count}. Существующие не изменены.")
        )
