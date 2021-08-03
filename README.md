# Nautobot + Dolt

Nautobot-Dolt is a plugin for Nautobot, a Network Source of Truth and Network Automation Platform.
It was developed to run on top of Dolt, a MySQL-compatible database that supports Git-like branch-and-merge 
operations in a SQL database. 
Nautobot-Dolt exposes Dolt's branch, diff, and merge features in Nautobot at the application layer, allowing
Nautobot users to make changes to the data model on "developement" branches, and merge their changes back 
to the main branch once they've been validated and peer-reviewed.

## Getting Started

Nautobot-Dolt can be deployed with [Docker](https://docs.docker.com/get-docker/) and [Docker-Compose](https://docs.docker.com/compose/)
and assumes that you have them installed. 
Follow each link for instructions on how to install.
Nautobot-Dolt uses [Invoke](http://www.pyinvoke.org/) to execute Docker workflows.
Invoke can be installed using pip: 

```bash
$ pip3 install invoke
```

Using a few invoke commands we can build and run Nautobot with the Nautobot-Dolt plugin installed:

```bash
$ inv build
$ inv migrate
$ inv createsuperuser
$ inv start
```

## Branches

With the Nautobot-Dolt plugin installed, everything within Nautobot happens on a branch. 
The "active branch" is always visible in a banner at the top of page.
The default branch "main" represents the state of the production database, 
all other branches represent the state of in-progress changes to main. 
While changes can be made directly to the main branch (assuming appropriate permissions), 
The recommended workflow is to make changes on a separate branch, review the diff of these changes, 
and merge these changes back to main only after they've been reviewed by someone else. 

## Commits

Each change submitted to Nautobot, either through the UI or the API, is wrapped in Dolt Commit. 
Dolt Commits represent granular units of work that can be individually inspected or undone.
Commits for the active branch can be viewed on the Commit Log page.
The commit log on branch main shows the entire history of commits to the main branch, 
while the commit log for non-main branches shows the history only since it was created.

## Merging

Once a set of changes is complete, it can be applied to the main branch through a merge operation.
Merging combines the data of two branches, source and destination, at the object level by comparing 
what has changed since the branches diverged from each other. 
In the case that both branches made changes to the same object, a merge conflict will occur. 
To resolve a merge conflict, the user must undo the change that created the conflict on the source branch.
Once the merge is free of conflicts, the source branch can be merged into the destination branch.
