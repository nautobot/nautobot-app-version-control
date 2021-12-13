# Welcome to Nautobot Version Control's documentation!

Nautobot Version Control brings Git-style version control to the [Nautobot](https://github.com/nautobot/nautobot) open source Network Source of Truth and Network Automation Platform.

Nautobot provides a number of features to validate its data model and safeguard network configuration from errors. Adding database versioning provides another layer of assurance by enabling human review of proposed changes to production data, use of automated testing pipelines, and database rollback in the case of errors.

The database versioning is made possible by the use of a [Dolt](https://github.com/dolthub/dolt) database. Dolt is a MySQL-compatible SQL database that you can fork, clone, branch, merge, push and pull just like a Git repository.

Dolt’s *branch* and *merge* versioning model allows operators to safely modify the data model on feature branches, merging to production only after validation is complete.

```{toctree}
:maxdepth: 2
:caption: "Contents:"

design.md
version-control-operations.md
workflows/common_workflows.md
```
