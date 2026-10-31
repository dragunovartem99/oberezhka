from getpass import getpass

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Создать редактора: только изделия, фотографии и настройки мастерской."

    def add_arguments(self, parser):
        parser.add_argument("username")

    def handle(self, *args, **options):
        user_model = get_user_model()
        if user_model.objects.filter(username=options["username"]).exists():
            raise CommandError("Такой пользователь уже существует.")
        user = user_model(username=options["username"], is_staff=True)
        password = getpass("Пароль редактора: ")
        if password != getpass("Повторите пароль: "):
            raise CommandError("Пароли не совпадают.")
        try:
            validate_password(password, user)
        except ValidationError as error:
            raise CommandError(" ".join(error.messages)) from error
        user.set_password(password)
        user.save()
        group, _ = Group.objects.get_or_create(name="Редакторы мастерской")
        group.permissions.set(
            Permission.objects.filter(content_type__app_label="catalog").exclude(
                codename="delete_sitesettings",
            )
        )
        user.groups.add(group)
        self.stdout.write(self.style.SUCCESS(f"Редактор {user.username} создан."))
