from django.db.models.signals import post_migrate

from nautobot.extras.plugins import PluginConfig

from dolt.migrations import auto_dolt_commit_migration


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
        #   this is also set in /development/nautobot_config.py
        "DATABASE_ROUTERS": [
            "dolt.routers.GlobalStateRouter",
        ],
        "SESSION_ENGINE": "django.contrib.sessions.backends.signed_cookies",
        "CACHEOPS_ENABLED": False,
    }
    middleware = [
        "dolt.middleware.dolt_health_check_intercept_middleware",
        "dolt.middleware.DoltBranchMiddleware",
        "dolt.middleware.DoltAutoCommitMiddleware",
    ]

    def ready(self):
        super().ready()

        # make a Dolt commit to save database migrations
        post_migrate.connect(auto_dolt_commit_migration, sender=self)


config = NautobotDolt


# Registry of Content Types of models that should be under version control.
# Top-level dict keys are app_labels. If the top-level dict value is `True`,
# then all models under that app_label are allowlisted.The top-level value
# may also be a nest dict containing a subset of version-controlled models
# within the app_label.
__MODELS_UNDER_VERSION_CONTROL__ = {
    "dolt": {
        # Pull Requests are not versioned
        "pullrequest": False,
        "pullrequestreviewcomments": False,
        "pullrequestreviews": False,
        "branchmeta": False,
        # todo: calling the following "versioned" is odd.
        #   their contents are parameterized by branch
        #   changes, but they are not under VCS.
        "branch": True,
        "commit": True,
        "commitancestor": True,
        "conflicts": True,
        "constraintviolations": True,
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
            format as __MODELS_UNDER_VERSION_CONTROL__
    eg:
        register_versioned_models({
            "my_app_label": {
                "my_content_type": True,
            },
            "my_other_app_label": True,
        })

    """
    err = ValueError("invalid model version allowlist")
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
    __MODELS_UNDER_VERSION_CONTROL__.update(ct_dict)


def is_versioned_model(model):
    """
    Determines whether a model's is under version control.
    See __MODELS_UNDER_VERSION_CONTROL__ for more info.
    """
    allowlist = __MODELS_UNDER_VERSION_CONTROL__
    return _lookup_allowlist(model, allowlist)


def _lookup_allowlist(model, allowlist):
    """
    performs a lookup on allowlists with the structure
    of  __MODELS_UNDER_VERSION_CONTROL__
    """
    app_label = model._meta.app_label
    model = model.__name__.lower()

    if app_label not in allowlist:
        return False
    if isinstance(allowlist[app_label], bool):
        return allowlist[app_label]

    # subset specified
    if isinstance(allowlist[app_label], dict):
        if model not in allowlist[app_label]:
            return False
        if isinstance(allowlist[app_label][model], bool):
            return allowlist[app_label][model]
    raise ValueError("invalid g allowlist")
