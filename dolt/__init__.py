from django.db.models.signals import post_migrate

from nautobot.extras.plugins import PluginConfig

from dolt.migrations import dolt_autocommit_migration


class NautobotDolt(PluginConfig):
    name = "dolt"
    verbose_name = "Nautobot Dolt"
    description = "Nautobot + Dolt"
    version = "0.1"
    author = "Andy Arthur"
    author_email = "andy@dolthub.com"
    required_settings = []
    default_settings = {
        # TODO: are these respected?
        "DATABASE_ROUTERS": [
            "dolt.routers.GlobalStateRouter",
        ],
        "SESSION_ENGINE": "django.contrib.sessions.backends.signed_cookies",
        "CACHEOPS_ENABLED": False,
    }
    middleware = [
        "dolt.middleware.DoltBranchMiddleware",
        "dolt.middleware.DoltAutoCommitMiddleware",
    ]

    def ready(self):
        super().ready()
        post_migrate.connect(dolt_autocommit_migration, sender=self)


# Registry of Content Types of models that should be under version control.
# Top-level dict keys are app_labels. If the top-level dict value is `True`,
# then all models under that app_label are whitelisted.The top-level value
# may also be a nest dict containing a subset of whitelisted models within
# the app_label.
__MODEL_VERSION_WHITELIST__ = {
    "dolt": {
        "branch": True,
        "branchmeta": True,
        "commit": True,
        "commitancestor": True,
        "conflicts": True,
        "constraintviolations": True,
        # Pull Requests are not versioned
        "pullrequest": False,
        "pullrequestreviewcomments": False,
        "pullrequestreviews": False,
    },
    "dcim": True,
    "circuits": True,
    "ipam": True,
    "virtualization": True,
    "taggit": True,
    "tenancy": True,
    "extras": {
        # TODO: what should be versioned from `extras`?
        "computedfield": True,
        "configcontext": True,
        "configcontextschema": True,
        "customfield": True,
        "customfieldchoice": True,
        "customlink": True,
        "exporttemplate": True,
        # "gitrepository": True,
        "graphqlquery": True,
        "imageattachment": True,
        # "job": True,
        # "jobresult": True,
        "objectchange": True,
        "relationship": True,
        "relationshipassociation": True,
        "status": True,
        "tag": True,
        "taggeditem": True,
        "webhook": True,
    },
}


def register_versioned_models(ct_dict):
    """Register additional content types to be versioned.
    Args:
        ct_dict: a python dictionary following the same
            format as __MODEL_VERSION_WHITELIST__
    """
    err = ValueError("invalid model version whitelist")
    for key, val in ct_dict.items:
        if not isinstance(key, str):
            # key must be string
            raise err
        if isinstance(val, bool):
            # val may be bool
            continue
        if not isinstance(val, dict):
            # val must be dict if not bool
            raise err
        # validate nested dict
        for k, v in val.items():
            if not isinstance(k, str):
                # key must be string
                raise err
            if not isinstance(v, bool):
                # val must be bool
                raise err
    __MODEL_VERSION_WHITELIST__.update(ct_dict)


def is_versioned_model(model):
    """
    Determines whether a model's content type is on the whitelist.
    See __MODEL_VERSION_WHITELIST__ for more info.
    """
    app_label = model._meta.app_label
    model = model.__name__.lower()
    whitelist = __MODEL_VERSION_WHITELIST__

    if app_label not in whitelist:
        return False
    if isinstance(whitelist[app_label], bool):
        return whitelist[app_label]

    # subset specified
    if isinstance(whitelist[app_label], dict):
        if model not in whitelist[app_label]:
            return False
        if isinstance(whitelist[app_label][model], bool):
            return whitelist[app_label][model]

    raise ValueError("invalid model version whitelist")


config = NautobotDolt
