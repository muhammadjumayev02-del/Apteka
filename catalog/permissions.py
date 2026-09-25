from functools import wraps

from django.core.exceptions import PermissionDenied


def superuser_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_active or not request.user.is_superuser:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped


def catalog_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        from .roles import can_view_catalog

        if not can_view_catalog(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapped
