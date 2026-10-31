from django.core.paginator import Paginator
from django.db.models import Prefetch
from django.http import FileResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_safe

from .models import Doll, DollPhoto


def published_dolls():
    return Doll.objects.filter(is_published=True).prefetch_related(
        Prefetch("photos", queryset=DollPhoto.objects.order_by("position", "pk")),
    )


def home(request):
    dolls = published_dolls()
    featured = list(dolls.filter(is_featured=True)[:4])
    if not featured:
        featured = list(dolls[:4])
    return render(
        request,
        "catalog/home.html",
        {"featured": featured, "hero": featured[0] if featured else None},
    )


def catalog(request):
    status = request.GET.get("status", "")
    if status not in Doll.Availability.values:
        status = ""
    dolls = published_dolls()
    if status:
        dolls = dolls.filter(availability=status)
    return render(
        request,
        "catalog/catalog.html",
        {
            "page_obj": Paginator(dolls, 12).get_page(request.GET.get("page")),
            "status": status,
            "statuses": Doll.Availability.choices,
        },
    )


def doll(request, slug):
    item = get_object_or_404(published_dolls(), slug=slug)
    related = published_dolls().exclude(pk=item.pk)[:3]
    return render(request, "catalog/doll.html", {"doll": item, "related": related})


def about(request):
    return render(request, "catalog/about.html")


def ordering(request):
    return render(request, "catalog/ordering.html")


@require_safe
def photo(request, filename):
    image = get_object_or_404(
        DollPhoto,
        image=f"dolls/{filename}",
    )
    response = FileResponse(image.image.open("rb"), content_type="image/webp")
    # Uploads receive a new UUID filename, so an existing URL never changes content.
    response["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
