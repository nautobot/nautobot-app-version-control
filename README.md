# Nautobot Version Control

<p align="center">
  <img src="https://raw.githubusercontent.com/nautobot/nautobot-app-version-control/develop/docs/images/icon-nautobot-version-control.png" class="logo" height="200px">
  <br>
  <a href="https://github.com/nautobot/nautobot-app-version-control/actions"><img src="https://github.com/nautobot/nautobot-app-version-control/actions/workflows/ci.yml/badge.svg?branch=main"></a>
  <a href="https://docs.nautobot.com/projects/version-control/en/latest/"><img src="https://readthedocs.org/projects/nautobot-plugin-version-control/badge/"></a>
  <a href="https://pypi.org/project/nautobot-version-control/"><img src="https://img.shields.io/pypi/v/nautobot-version-control"></a>
  <a href="https://pypi.org/project/nautobot-version-control/"><img src="https://img.shields.io/pypi/dm/nautobot-version-control"></a>
  <br>
  An <a href="https://www.networktocode.com/nautobot/apps/">App</a> for <a href="https://nautobot.com/">Nautobot</a>.
</p>

## Overview

The Nautobot Version Control app brings version control to the [Nautobot](https://github.com/nautobot/nautobot) open source Network Source of Truth and Network Automation Platform. 

Nautobot provides a number of features to validate its data model and safeguard network configuration from errors. Adding database versioning provides another layer of assurance by enabling human review of proposed changes to production data, use of automated testing pipelines, and database rollback in the case of errors. 

The database versioning is made possible by the use of a [Dolt](https://github.com/dolthub/dolt) database. Dolt is a MySQL-compatible SQL database that you can fork, clone, branch, merge, push and pull just like a Git repository.

Dolt’s *branch* and *merge* versioning model allows operators to safely modify the data model on feature branches, merging to production only after validation is complete.


### Screenshots

> Developer Note: Add any representative screenshots of the App in action. These images should also be added to the `docs/user/app_use_cases.md` section.

> Developer Note: Place the files in the `docs/images/` folder and link them using only full URLs from GitHub, for example: `![Overview](https://raw.githubusercontent.com/nautobot/nautobot-plugin-version-control/develop/docs/images/plugin-overview.png)`. This absolute static linking is required to ensure the README renders properly in GitHub, the docs site, and any other external sites like PyPI.

More screenshots can be found in the [Using the App](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/user/app_use_cases/) page in the documentation. Here's a quick overview of some of the plugin's added functionality:

![](https://raw.githubusercontent.com/nautobot/nautobot-plugin-version-control/develop/docs/images/placeholder.png)

## Try it out!

> Developer Note: Only keep this section if appropriate. Update link to correct sandbox.

This App is installed in the Nautobot Community Sandbox found over at [demo.nautobot.com](https://demo.nautobot.com/)!

> For a full list of all the available always-on sandbox environments, head over to the main page on [networktocode.com](https://www.networktocode.com/nautobot/sandbox-environments/).

## Documentation

Full documentation for this App can be found over on the [Nautobot Docs](https://docs.nautobot.com) website:

- [User Guide](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/user/app_overview/) - Overview, Using the App, Getting Started.
- [Administrator Guide](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/admin/install/) - How to Install, Configure, Upgrade, or Uninstall the App.
- [Developer Guide](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/dev/contributing/) - Extending the App, Code Reference, Contribution Guide.
- [Release Notes / Changelog](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/admin/release_notes/).
- [Frequently Asked Questions](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/user/faq/).

### Contributing to the Documentation

You can find all the Markdown source for the App documentation under the [`docs`](https://github.com/nautobot/nautobot-plugin-version-control/tree/develop/docs) folder in this repository. For simple edits, a Markdown capable editor is sufficient: clone the repository and edit away.

If you need to view the fully-generated documentation site, you can build it with [MkDocs](https://www.mkdocs.org/). A container hosting the documentation can be started using the `invoke` commands (details in the [Development Environment Guide](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/dev/dev_environment/#docker-development-environment)) on [http://localhost:8001](http://localhost:8001). Using this container, as your changes to the documentation are saved, they will be automatically rebuilt and any pages currently being viewed will be reloaded in your browser.

Any PRs with fixes or improvements are very welcome!

## Questions

For any questions or comments, please check the [FAQ](https://docs.nautobot.com/projects/nautobot-version-control/en/latest/user/faq/) first. Feel free to also swing by the [Network to Code Slack](https://networktocode.slack.com/) (channel `#nautobot`), sign up [here](http://slack.networktocode.com/) if you don't have an account.
