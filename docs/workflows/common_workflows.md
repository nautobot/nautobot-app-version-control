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

To review changes in your branch (compared to the starting branch): *Version Control --> Diffs*.

The diffs page contains:
* A diff summary pane
* Metadata about the PR
* A list of all the diffs between the current branch and the starting branch

Use this screen to review/confirm your changes prior to submitting a pull request to merge the changes into the main (production) branch.

### Viewing Branch Commits

There are two ways to view commits in a branch:
* Click on item in the **Diff Type** column on the branch's diffs page
  * *Version Control --> Diffs --> Click on one of the changes*
  * This will show the commit details for the diff 
* Navigate to *Version Control --> Commits* 
  * This will show a list of the commits in the active branch
  * Clicking on a given commit will take you to a screen with the commit details

## The Pull Request (PR) Process

After reviewing changes on a branch and any specific diffs for the changes, a user will typically want to submit a PR to merge the changes in the branch into the main (production) branch.

### Creating a PR

To create a PR, navigate to  *Version Control --> Pull Requests --> + Add*. You may also create the PR directly from the navigation menu: *Version Control --> Pull Requests -->+* if you don't wish to view all the open PRs prior to creating a PR.

Once on the *Add a new pull request* screen, fill out the requested details and click on *Create*

### Reviewing a PR
Ideally, a different user would review the PR prior to merging the changes into to main branch.  



## Reverting Changes

At any point during the process of making changes in a branch, reviewing a PR for the changes in a branch, or trying to revert changes already in the main (production) branch, you may want to revert specific commits or revert commits en masse.  



### Reverting Single Commits

A single commit is a specific change to the database. A commit is generated each time the user clicks on a *Create*, *Delete*, *Update*, or *Merge*.

### Reverting Multiple Commits







