from django.contrib.contenttypes.models import ContentType


class DoltError(Exception):
    pass


def author_from_user(usr):
    if usr and usr.username and usr.email:
        return f"{usr.username} <{usr.email}>"
    # default to generic user
    return "nautobot <nautobot@ntc.com>"


def is_dolt_model(model):
    """
    Returns `True` if `instance` is an instance of
    a model from the Dolt plugin. Generally,
    """
    ct = ContentType.objects.get_for_model(model)
    return ct.app_label == "dolt"
