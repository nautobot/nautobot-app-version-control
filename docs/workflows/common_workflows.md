# Common Workflows


## Proposing Data Changes

### Creating A Branch

To create a new branch, navigate to *Version Control --> Branches --> +* or *Version Control --> Branches --> + Add*.

Fill out the form, filling in the Name and selecting the starting branch (defaults to *main*).

> **NOTE**: The branch name must be in slug form, consisting of letters, numbers, underscores or hyphens (no spaces).

Click the *Create* button.

Once the branch is created:
* You will be taken to the detail view for the branch
* A banner will appear, notifying you that the branch was created
* A second banner will appear, showing that the newly created branch is now the active branch

### Making Changes To The Data

Any changes to data in Nautobot will be limited to the active branch. To avoid making changes to production data, ensure a non-main branch is active:
* Create a new branch: upon creation, that branch will become active
* Switch to an existing non-main branch: *Version Control --> Branches --> 'Activate' a non-main branch*

You should see a banner indicating that the created/selected branch is the *Active Branch*.

Make changes to the data as necessary.

### Reviewing Changes

## The Pull Request (PR) Process


## Reverting Changes

### Reverting Single Commits

A single commit is a specific change to the database. A commit is generated each time the user clicks on a *Create*, *Delete*, *Update*, or *Merge*.

### Reverting Multiple Commits







