APTEKACHI_GROUP = "Aptekachi"


def can_view_catalog(user):
    return user.is_authenticated and user.is_active and (
        user.is_superuser or user.groups.filter(name=APTEKACHI_GROUP).exists()
    )
