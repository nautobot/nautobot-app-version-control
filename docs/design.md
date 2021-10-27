# Motivation
Nautobot is an open source Network Source of Truth and Network Automation Platform. 
Nautobot provides a number of features to validate its data model and safeguard network configuration from errors. 
Adding database versioning with Dolt provides another layer of assurance by enabling human review of changesets and database rollback in the case of errors. 
Dolt’s branch and merge versioning model allows operators to safely modify the data model on feature branches, merging to production only after validation is complete.

## Dolt

Dolt is a MySQL compatible relational database that supports Git-like versioning features. 
Git version files, Dolt versions database tables. 
Running Nautobot on Dolt means operators can use version-control workflows from software development when managing the network data model.

Dolt is built on top of a custom storage layer that supports structural sharing and efficient diff operations. 
At the core of Dolt’s storage are [Prolly Trees](https://docs.dolthub.com/reference/architecture#overview), 
an index data-structure that combines properties of [B-Trees](https://en.wikipedia.org/wiki/B-tree) 
and [Merkle Trees](https://en.wikipedia.org/wiki/Merkle_tree).  
Prolly trees allow the database to maintain multiple versions of a database table without duplicating any of the tree nodes that make up the table storage. 
Further, each of the nodes is [content-addressable](https://en.wikipedia.org/wiki/Content-addressable_storage), 
meaning that Dolt can compare different versions of the database using the same performant algorithms that Git uses to compare versions of source files. 
The result is a relational database that can branch, diff, merge, push and pull.


# Version Control Plugin Design

The core features of the Version Control plugin are commits and branches. 
All database reads and writes happen on a branch. 
All database writes create a commit.

### Requesting Info From A Branch

All requests served through the web interface or API fetch data from a specific database branch. 
The choice of branch is encoded in the request by the client: 
* For web requests, the branch state is stored in a cookie using Django cookie sessions
* For API requests, the branch state is encoded in a request header

When the server receives a request, it looks for this state and uses it to select the correct database branch to serve the request: 
* If the requested branch cannot be found or if the requested branch does not exist, the main branch is used.
* In the web interface, a banner is displayed to notify the user of their “active” branch

![active branch banner](images/active-branch-banner.png)

The business logic to handle branch selection is performed in [middleware](https://docs.djangoproject.com/en/stable/topics/http/middleware/), 
specifically in [DoltBranchMiddleware](https://github.com/nautobot/nautobot-plugin-version-control/blob/develop/dolt/middleware.py#L36) 

### Database Versioning

Database versioning happens on a per-connection basis. Each connection will read from a specific branch. 
Database connections outside of the web server, such as through nbshell are also versioned. 
When connecting directly to the database you can check your current branch with the active_branch() function and switch branches with the checkout() method:

```python
>>> from dolt.models import Branch
>>> from dolt.utils import active_branch
>>> active_branch()
    'main'
>>> Branch.objects.get(name="foo").checkout()
>>> active_branch()
    'foo'
```

# REST API

The Version Control plugin extends the Nautobot's core [REST API](https://nautobot.readthedocs.io/en/stable/rest-api/overview/#rest-api-overview) with endpoints for plugin models. 

## REST API EndPoints

The top level API endpoint is `/api/plugins/dolt/`. 
Below this, there are endpoints for the following models:

- Branch: `api/plugins/dolt/branches`
- Commit: `api/plugins/dolt/commits`
- Pull Request: `api/plugins/dolt/pull_requests` 
- Pull Request Reviews: `api/plugins/dolt/pull_requests_reviews`

The Version Control API shares a common implementation with Nautobot's core API.
Features suchs as [pagination](https://nautobot.readthedocs.io/en/stable/rest-api/overview/#pagination) and
[filtering](https://nautobot.readthedocs.io/en/stable/rest-api/filtering/) have the same interface for both APIs.

## REST API Authentication

The REST API primarily employs token-based authentication using the same mechanisms as the core Nautobot API.
See the [Nautobot docs](https://nautobot.readthedocs.io/en/stable/rest-api/authentication/#rest-api-authentication) for more detail.

## Dolt Branch Header

When querying the API, clients can choose a specific branch using a `dolt-branch` header. 
For example, the following request will list all the commits from `my-feature-branch`:

```bash
$ curl -s \
-H "Authorization: Token 90579810c8d2d2e98fb34d69025f6a1cc3fa9943" \
-H "dolt-branch: my-feature-branch"  \
0.0.0.0:8080/api/plugins/dolt/commits/
```

Versioning requests works with all API endpoints, not just models from the Version Control plugin. This example queries for devices in a `my-branch`: 

```bash
$ curl -s \
-H "Authorization: Token 90579810c8d2d2e98fb34d69025f6a1cc3fa9943" \
-H "dolt-branch: my-branch"  \
0.0.0.0:8080/api/dcim/devices/
```

This is a python example of querying for devices in the `atl` site in the `atl-leaf-agument` branch:

```python
import requests

from pprint import pprint

url = "http://0.0.0.0:8080/api/dcim/devices/?site=atl"

payload={}
headers = {
  'Authorization': 'Token nnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnnn',
  'dolt-branch': 'atl-leaf-augment'
}

response = requests.request("GET", url, headers=headers, data=payload)

pprint(response.json())
```

# Implementation Details

## Commit Logic

The committing logic is implemented using a combination of middleware and [Django signals](https://docs.djangoproject.com/en/3.2/topics/signals/),
specifically [DoltAutoCommitMiddleWare](https://github.com/nautobot/nautobot-plugin-version-control/blob/develop/dolt/middleware.py#L118). 
DoltAutoCommitMiddleWare wraps every server request in a [AutoDoltCommit](https://github.com/nautobot/nautobot-plugin-version-control/blob/develop/dolt/middleware.py#L134)
context manager which listens for and responds to database writes made while processing the request. 
AutoDoltCommit listens for signals fired by Django model updates and makes a Dolt commit if updates were made during the lifetime of the context manager. 
The message for the commit is derived from the model signals that were captured.

## DoltSystemTables
[DoltSystemTable](https://github.com/nautobot/nautobot-plugin-version-control/blob/3020d86159b92edfb68abefd1079c84f54a358b8/dolt/models.py#L21)
is an abstract base class that forms the basis of Django models that expose Dolt [system tables](https://github.com/nautobot/nautobot-plugin-version-control/blob/3020d86159b92edfb68abefd1079c84f54a358b8/dolt/models.py#L21)
to the Object Relational Mapping (ORM). 
Plugin models such as *Commit* and *Branch* that inherit from DoltSystemTable are [unmanaged](https://github.com/nautobot/nautobot-plugin-version-control/blob/3020d86159b92edfb68abefd1079c84f54a358b8/dolt/models.py#L21),
meaning that Django will ignore these models for the purposes of database migrations. 
This is important because Dolt system tables exist from the time the database is created and cannot be modified or deleted. 
Internally, Dolt generates system table data on-the-fly rather than reading it from a traditional database index.

## BranchMeta
The Branch model is one such "unmanaged" model. 
It exposes the dolt_branches system table to the ORM. 
System tables have a static schema, so additional object fields such as "created by" and "source branch" must be stored in another model. 
The [BranchMeta](https://github.com/nautobot/nautobot-plugin-version-control/blob/3020d86159b92edfb68abefd1079c84f54a358b8/dolt/models.py#L194) model does exactly that. 
Each Branch object has an associated BranchMeta object where the `BranchMeta.branch field` is equal to the name field of the associated branch. 
However, this relationship is not formalized with a Foreign Key due to limitations with the dolt_branches table.
Branch objects lookup their associated BranchMeta objects on a best-effort basis.

## Merge Candidates
The Version Control plugin prevents Pull Requests from being merged if it will create merge conflicts. 
In order to determine if merging a Pull Request will cause conflicts, the merge is precomputed when rendering the PR view. 
The result of pre-computing this merge is called a “merge candidate”. 
Merge candidates are generated by making a hidden branch starting at the tip of the PRs destination branch, and merging the PRs source branch into this new branch. 
The resulting merge candidate is then inspected for merge conflicts. 
Merge candidates are generated on demand when a PR view is rendered, unless a valid merge candidate has already been cached. 
If the source and destination branch of a PR are unchanged since the merge candidate was computed, it is considered valid.

## Versioned Models
Within the Nautobot data model, database models are divided into two groups: versioned and non-versioned. 
Generally speaking, database models that represent a part of the network state will be versioned models (e.g. Devices, IP Addresses, Sites). 
Database models that are specific to the Nautobot application (e.g. Users, Web Hooks, Permissions) will not be versioned. 
Versioning features are restricted for some models such that they have a single “global” state. 
This is especially important for models that affect permissions and authentication: we need a single place where we can read and update security-sensitive data.


### Model Behavior

Versioned and non-versioned models have different behavior when working on a non-main feature branch: 
* Versioned models will be read from the tip of the feature branch
* Versioned models can also be edited on a feature branch, and the edits will be versioned in commits 

Non-versioned models:
* Cannot be edited on feature branches, they must only be edited on the main branch 
* Will always be read from the tip of the main branch, rather than from a feature branch, regardless of what branch is specified in a request
* Can’t have multiple versions: there is always a single version which is read-from, and edited on main.

## Global State Router
The business logic for differentiating versioned and non-versioned models is implemented in a Django [database router](https://docs.djangoproject.com/en/3.2/topics/db/multi-db/#automatic-database-routing), 
specifically the [GlobalStateRouter](https://github.com/nautobot/nautobot-plugin-version-control/blob/c9f49b8e007ca22afe0d6e3ddb5066e31b37dc64/dolt/routers.py#L11). 
The GlobalStateRouter is responsible for choosing a database connection to read an object from or write an object to, depending on its model class. 
There are two connections to choose from when accessing the database. 
The “default” connection will access the database on the Dolt branch that was specified in the request. 
This connection is used to read and write versioned models. 
The “global” connection always accesses the database on the main branch, it is used for non-versioned models.

In order to choose a connection for a model, the router first references the 
[versioned model registry](https://github.com/nautobot/nautobot-plugin-version-control/blob/c9f49b8e007ca22afe0d6e3ddb5066e31b37dc64/dolt/__init__.py#L83)
to determine if the model is under version control. 
Currently, this registry is a hardcoded mapping from ContentType to versioned/non-versioned. 
The versioned model registry is structured as an ["allow-list"](https://help.dnsfilter.com/hc/en-us/articles/1500008111381-Allow-and-Block-Lists).
If a model is absent from the list, it is assumed to be non-versioned.
[Future work](https://github.com/nautobot/nautobot/issues/748)
in Nautobot core will make it possible for models to declare themselves whether they should be version controlled.

Database connections for versioned and non-versioned models are defined in 
[nautobot_config.py](https://github.com/nautobot/nautobot-plugin-version-control/blob/abd12aae0f1c4a684ce89c7eaeaca81bd1d37e68/development/nautobot_config.py#L54). 
The database configuration is as follows:
```python
DATABASES = {
    "default": {
        "NAME": "nautobot",  # Database name
        "USER": os.getenv("DOLT_USER", ""),  # Database username
        "PASSWORD": os.getenv("DOLT_PASSWORD", ""),  # Database password
        "HOST": os.getenv("DOLT_HOST", "localhost"),  # Database server
        "PORT": os.getenv("DOLT_PORT", ""),  # Database port
        "ENGINE": "django.db.backends.mysql",
    },
    "global": {
        "NAME": "nautobot",  # Database username
        "USER": os.getenv("DOLT_USER", ""),  # Database username
        "PASSWORD": os.getenv("DOLT_PASSWORD", ""),  # Database password
        "HOST": os.getenv("DOLT_HOST", "localhost"),  # Database server
        "PORT": os.getenv("DOLT_PORT", ""),  # Database port
        "ENGINE": "django.db.backends.mysql",
        "TEST": {
            "MIRROR": "default",
        },
    },
}
```

These two database connections are logically separate at the Django layer, but in fact point to the same physical Dolt instance. 
The “default” database handles versioned models, the “global” database handles non-versioned models. 
For test purposes, the databases are configured as replicas. 
The “TEST” entry in the config dict for the “global” database is a [primary/replica](https://docs.djangoproject.com/en/3.2/topics/testing/advanced/#testing-primary-replica-configurations)
configuration for testing. 
This indicates that under testing “global” should be treated as a mirror of “default”.

## Diff Tables

Diff views are rendered for Commits and Branches. 
Object changes are rendered in a list view, grouped by model, and annotated with diff information. 
New objects are highlighted in green, deleted objects in red, and modified objects in gold.

![diff table](images/diff-table.png)

Diff views are derived directly from model list views in Nautobot core. 
Each diff table in a diff view displays the same columns as the table in the associated model list view, with the addition of the “Diff Type” column.
Diff tables are created by subclassing the table from a core model's list view. 
Custom rendering functions are added to apply diff styling to the list view. 

Diff table classes are created dynamically at runtime. 
When a diff table is needed to display model changes, the core model's table is looked up from the 
[diff table registry](https://github.com/nautobot/nautobot-plugin-version-control/blob/c5ca7c4467b7588b5eb925523a51ce0eab62df4e/dolt/__init__.py#L175)
and then a new subclass is created to extend the core table.
The diff table registry works much like the versioned model registry, it is a mapping from a models content type to its table.
Tables in Nautobot core are all subclasses of [`django-tables2`](https://django-tables2.readthedocs.io/en/latest/).
All entries in the diff table registry must also be subclasses of `django-tables2`.

# Plugin Integration and Model Registration

The Version Control plugin is designed to be used in coordination with other Nautobot plugins.
By default, any models registered by other plugins will be considered non-versioned. 
In order to make use of version control and diff features, plugins must register their models in 
the [versioned models registry](https://github.com/nautobot/nautobot-plugin-version-control/blob/c5ca7c4467b7588b5eb925523a51ce0eab62df4e/dolt/__init__.py#L139) 
and the [diff table registry](https://github.com/nautobot/nautobot-plugin-version-control/blob/c5ca7c4467b7588b5eb925523a51ce0eab62df4e/dolt/__init__.py#L186). 
Both of these functions take nested dictionaries as arguments:
```python
register_versioned_models({
    "my-app-label": {
        "my-model-name": True,
        "my-other-model-name": True,
    }
})
register_diff_tables({
    "my-app-label": {
        "my-model-name": "import.path.to.table",
        "my-other-model-name": "import.path.to.other.table",
    }   
})
```
The dictionaries are keyed by content type (app-label, model) pairs. 
Values for the versioned model registry are `bool`s indicating whether the model should be versioned.
Values for the diff table registry are `string` import paths pointing to the `django-tables2` table that will be subclassed for diff views. 

