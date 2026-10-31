from .models import SiteSettings


def site_settings(request):
    return {"workshop": SiteSettings.objects.first() or SiteSettings()}
