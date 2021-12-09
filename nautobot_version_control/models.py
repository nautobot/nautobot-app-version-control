"""models.py exposes Dolt primitives such as branches and commits as Django models."""


from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection, connections
from django.db.models import Q
from django.db.models.deletion import CASCADE
from django.urls import reverse
from django.utils.html import mark_safe, format_html
from django.dispatch import receiver
from django.db.models.signals import pre_delete

from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features
from nautobot.users.models import User
from nautobot.utilities.querysets import RestrictedQuerySet

from nautobot_version_control.utils import author_from_user, DoltError, db_for_commit, active_branch
from nautobot_version_control.constants import DOLT_DEFAULT_BRANCH


class DoltSystemTable(models.Model):
    """DoltSystemTable represents an abstraction over Dolt builtin system tables."""

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        """Meta links to a _meta table."""

        abstract = True
        managed = False

    def validated_save(self):
        """Perform model validation during instance save."""
        self.full_clean()
        self.save()


#
# Branches
#


class Branch(DoltSystemTable):
    """Branch represents a model over the dolt_branches system table."""

    name = models.TextField(primary_key=True)
    hash = models.TextField()
    latest_committer = models.TextField()
    latest_committer_email = models.TextField()
    latest_commit_date = models.DateTimeField()
    latest_commit_message = models.TextField()

    class Meta:
        """Meta class."""

        managed = False
        db_table = "dolt_branches"
        verbose_name_plural = "branches"

    def __init__(self, *args, starting_branch=None, creator=None, **kwargs):
        """Init the class."""
        super().__init__(*args, **kwargs)
        self.starting_branch = starting_branch
        self.creator = creator

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        """get_absolute_urls provide a url to access this branch's view."""
        return reverse("plugins:nautobot_version_control:branch", args=[self.name])

    @property
    def present_in_database(self):
        """present_in_database returns whether the branch exists in the database."""
        # determines `editing` flag in forms
        return Branch.objects.filter(name=self.name).exists()

    @property
    def active(self):
        """Returns true if the branch is the active branch."""
        return self.name == active_branch()

    @property
    def ahead_behind(self):
        """
        ahead_behind computes the ahead/behind. Ahead represents the number of commits since the ancestor of main and this
        branch. Behind represents how many commits are on main that have diverged passed this branch.
        :return: ahead/behind string.
        """
        merge_base = Commit.merge_base(self.name, DOLT_DEFAULT_BRANCH)
        merge_base_commit = Commit.objects.using(db_for_commit(self.hash)).get(commit_hash=merge_base)
        main_hash = Branch.objects.get(name=DOLT_DEFAULT_BRANCH).hash

        ahead = Commit.objects.filter(date__gt=merge_base_commit.date).using(db_for_commit(self.hash)).count()
        behind = Commit.objects.filter(date__gt=merge_base_commit.date).using(db_for_commit(main_hash)).count()

        return f"{ahead} ahead / {behind} behind"

    @property
    def created_by(self):
        """created_by returns the branch author."""
        m = self._branch_meta()
        return m.author if m else None

    @property
    def created_at(self):
        """created_at returns the datetime the branch was created."""
        m = self._branch_meta()
        return m.created if m else None

    @property
    def source_branch(self):
        """source_branch returns the name of the branch that this branch was originally checked out on."""
        m = self._branch_meta()
        return m.source_branch if m else None

    def checkout(self):
        """Checkout performs a checkout operation to this branch making it the active_branch."""
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT dolt_checkout("{self.name}") FROM dual;""")

    def _branch_meta(self):
        try:
            return BranchMeta.objects.get(branch=self.name)
        except ObjectDoesNotExist:
            return None

    def head(self):
        """Head returns the most recent commit for this branch as an object."""
        return Commit.objects.get(commit_hash=self.hash)

    def merge(self, merge_branch, user=None, squash=False):
        """
        Merge performs a merge operation between this branch and the merge_branch
        :param merge_branch: The branch to merge with
        :param user: The User object to associate the merge with
        :param squash: Whether or not to squash the merge thereby making it one commit
        :return:
        """
        author = author_from_user(user)
        self.checkout()
        with connection.cursor() as cursor:
            cursor.execute("SET dolt_force_transaction_commit = 1;")
            if squash:
                cursor.execute(
                    f"""SELECT dolt_merge(
                        '--squash',
                        '{merge_branch}'
                    ) FROM dual;"""
                )
            else:
                cursor.execute(
                    f"""SELECT dolt_merge(
                        '--no-ff',
                        '{merge_branch}'
                    ) FROM dual;"""
                )
            success = cursor.fetchone()[0] == 1
            if success:
                # only commit merged data on success
                msg = f"""merged "{merge_branch}" into "{self.name}"."""
                cursor.execute(
                    f"""SELECT dolt_commit(
                        '--all',
                        '--allow-empty',
                        '--message', '{msg}',
                        '--author', '{author}'
                    ) FROM dual;"""
                )
            else:
                cursor.execute("SELECT dolt_merge('--abort') FROM dual;")  # nosec
                raise DoltError(
                    format_html(
                        "{}",
                        mark_safe(
                            f"""Merging <strong>{merge_branch}</strong> into <strong>{self}</strong> created merge conflicts. Resolve merge conflicts to reattempt the merge."""
                        ),
                    )
                )

    def save(self, *args, **kwargs):
        """Save overrides the model save method."""
        with connection.cursor() as cursor:
            cursor.execute(
                f"""INSERT INTO dolt_branches (name,hash) VALUES ('{self.name}',hashof('{self.starting_branch}'));"""  # nosec
            )


@receiver(pre_delete, sender=Branch)
def delete_branch_pre_hook(sender, instance, using, **kwargs):  # pylint: disable=W0613
    """
    delete_branch_pre_hook intercepts the pre_delete signal for a branch. It returns an error if a branch that is about
    to be delete has pull requests that have not been deleted before.
    """
    # search the pull requests models for the same branch
    prs = PullRequest.objects.filter(Q(source_branch=instance.name) | Q(destination_branch=instance.name))

    if len(prs) > 0:
        pr_list = ",".join([f'"{pr}"' for pr in prs])
        raise DoltError(f"Must delete existing pull request(s): [{pr_list}] before deleting branch {instance.name}")


class BranchMeta(models.Model):
    """
    BranchMeta class has a 1:1 relation with a Branch. It represents internal of a branch that can't be represented in
    the dolt_branches system table.
    """

    branch = models.TextField(primary_key=True)
    source_branch = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        """Meta class."""

        # table name cannot start with "dolt"
        db_table = "nautobot_version_control_branchmeta"


#
# Commits
#


class Commit(DoltSystemTable):
    """Commit represents a Dolt Commit primitive."""

    commit_hash = models.TextField(primary_key=True)
    committer = models.TextField()
    email = models.TextField()
    date = models.DateTimeField()
    message = models.TextField()

    class Meta:
        """Meta class."""

        managed = False
        db_table = "dolt_log"
        verbose_name_plural = "commits"

    def __str__(self):
        return self.commit_hash

    def get_absolute_url(self):
        """get_absolute_url returns a link to a view that displays the commit's info."""
        return reverse("plugins:nautobot_version_control:commit", args=[self.commit_hash])

    @staticmethod
    def merge_base(left, right):
        """merge_base returns the ancestor commit between two commits."""
        with connection.cursor() as c:
            # author credentials not set
            c.execute(f"SELECT DOLT_MERGE_BASE('{left}', '{right}') FROM dual;")
            return c.fetchone()[0]

    @staticmethod
    def revert(commits, user):
        """revert executes a revert command on a commit which undoes it from the commit log."""
        args = ", ".join([f"'{c}'" for c in commits])
        author = author_from_user(user)
        args += f", '--author', '{author}'"
        with connection.cursor() as c:
            c.execute(f"SELECT DOLT_REVERT({args}) FROM dual;")
            return c.fetchone()[0]

    @property
    def short_message(self):
        """short_message truncates a commit message."""
        split = self.message.split(";")
        return split[0] + f". Total number of changes: {len(split)}"

    @property
    def present_in_database(self):
        """present_in_database returns whether a commit object exists in the Dolt database."""
        # determines `editing` flag in forms
        return Commit.objects.filter(commit_hash=self.commit_hash).exists()

    @property
    def parent_commits(self):
        """parent_commits returns the hashes of the commit ancestor."""
        return CommitAncestor.objects.filter(commit_hash=self.commit_hash).values_list("parent_hash", flat=True)

    def save(self, *args, using="default", user=None, **kwargs):  # pylint: disable=W0221
        """save overrides the Django model save behavior and perform a commit on the database."""
        msg = self.message.replace('"', "")
        author = author_from_user(user)
        conn = connections[using]
        with conn.cursor() as cursor:
            cursor.execute(
                f"""
            SELECT dolt_commit(
                '--all',
                '--allow-empty',
                '--message', "{msg}",
                '--author', "{author}")
            FROM dual;"""
            )


class CommitAncestor(DoltSystemTable):
    """CommitAncestor models the set of ancestors or parents that precede a Commit."""

    commit_hash = models.TextField(primary_key=True)
    parent_hash = models.TextField()  # primary_key=True
    parent_index = models.IntegerField()  # primary_key=True

    class Meta:
        managed = False
        db_table = "dolt_commit_ancestors"
        verbose_name_plural = "commit_ancestors"

    def __str__(self):
        return f"{self.commit_hash} ancestor[{self.parent_index}]: {self.parent_hash}"

    def save(self, *args, **kwargs):
        """We override and prevent save as the dolt_commit_ancestors system table should not be modified."""
        # todo(andy): throw exception?
        return


#
# Conflicts
#


class Conflicts(DoltSystemTable):
    """Conflicts represents the dolt_conflicts system table and the conflicts from a merge it contains."""

    table = models.TextField(primary_key=True)
    num_conflicts = models.IntegerField()

    class Meta:
        managed = False
        db_table = "dolt_conflicts"
        verbose_name_plural = "conflicts"

    def __str__(self):
        return f"{self.table} ({self.num_conflicts})"


class ConstraintViolations(DoltSystemTable):
    """Foreign Key and Unique Key Constraint Violations."""

    table = models.TextField(primary_key=True)
    num_violations = models.IntegerField()

    class Meta:
        managed = False
        db_table = "dolt_constraint_violations"
        verbose_name_plural = "constraint violations"

    def __str__(self):
        return f"{self.table} ({self.num_violations})"


#
# Pull Requests
#


@extras_features(
    "webhooks",
)
class PullRequest(BaseModel):
    """PullRequest models a pull request between two branches."""

    OPEN = 0
    MERGED = 1
    CLOSED = 2
    PR_STATE_CHOICES = [
        (OPEN, "Open"),
        (MERGED, "Merged"),
        (CLOSED, "Closed"),
    ]

    title = models.CharField(max_length=240)
    state = models.IntegerField(choices=PR_STATE_CHOICES, default=OPEN)
    # can't create Foreign Key to dolt_branches table :(
    source_branch = models.TextField()
    destination_branch = models.TextField()
    description = models.TextField(blank=True, null=True)
    creator = models.ForeignKey(User, on_delete=CASCADE)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        # table name cannot start with "dolt"
        db_table = "nautobot_version_control_pull_request"
        verbose_name_plural = "pull requests"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        """get_absolute_url returns a url to render a view of the pull request."""
        return reverse("plugins:nautobot_version_control:pull_request", args=[self.id])

    def get_src_dest_branches(self):
        """get_src_dest_branches returns a tuple of the src and destination branches."""
        src = Branch.objects.get(name=self.source_branch)
        dest = Branch.objects.get(name=self.destination_branch)
        return src, dest

    @property
    def open(self):
        """opens returns whether a pull request is open."""
        return self.state == PullRequest.OPEN

    @property
    def status(self):  # pylint: disable=R0911
        """
        The status of a PullRequest is determined by considering
        both the PullRequest and its PullRequestReviews.
        PRs in a closed or merged state have the corresponding status.
        An open PR's state is determined by the last non-comment review.
        """
        if self.state == PullRequest.CLOSED:
            return "closed"
        if self.state == PullRequest.MERGED:
            return "merged"

        pr_reviews = PullRequestReview.objects.filter(pull_request=self.pk)
        if not pr_reviews:
            return "open"

        # get the most recent review that approved or blocked
        decision = pr_reviews.order_by("-reviewed_at").first()
        if not decision or (decision and decision.state == PullRequestReview.COMMENTED):
            # all PRs are "comments"
            return "in-review"
        if decision.state == PullRequestReview.APPROVED:
            return "approved"
        if decision.state == PullRequestReview.BLOCKED:
            return "blocked"
        return "unknown"  # unreachable

    @property
    def commits(self):
        """commits returns a queryset of Commit objects that come after the ancestor between the src and des branch."""
        merge_base = Commit.objects.get(commit_hash=Commit.merge_base(self.source_branch, self.destination_branch))
        db = db_for_commit(Branch.objects.get(name=self.source_branch).hash)
        return Commit.objects.filter(date__gt=merge_base.date).using(db)

    @property
    def num_commits(self):
        """num_commits returns the number of commits that are considered in the pull requests."""
        return self.commits.count()

    @property
    def num_reviews(self):
        """num_reviews returns the number of PullRRequestReview(s) created on top of the PR."""
        return PullRequestReview.objects.filter(pull_request=self.pk).count()

    @property
    def summary_description(self):
        """summary_description returns a small summary of the pull request action."""
        return f"""Merging {self.num_commits} commits from "{self.source_branch}" into "{self.destination_branch}" """

    def merge(self, user=None, squash=False):
        """merge executes a merge between a destination and src branch."""
        try:
            src = Branch.objects.get(name=self.source_branch)
            dest = Branch.objects.get(name=self.destination_branch)
            dest.merge(src, user=user, squash=squash)
        except ObjectDoesNotExist as e:
            raise DoltError(f"error merging Pull Request {self}: {e}") from e
        self.state = PullRequest.MERGED
        self.save()


@extras_features(
    "webhooks",
)
class PullRequestReview(BaseModel):
    """PullRequestReview represents a comments, approval, or block on a pull request."""

    COMMENTED = 0
    APPROVED = 1
    BLOCKED = 2
    REVIEW_STATE_CHOICES = [
        (COMMENTED, "Commented"),
        (APPROVED, "Approved"),
        (BLOCKED, "Blocked"),
    ]

    pull_request = models.ForeignKey(PullRequest, on_delete=CASCADE)
    reviewer = models.ForeignKey(User, on_delete=CASCADE)
    reviewed_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)
    state = models.IntegerField(choices=REVIEW_STATE_CHOICES, null=True)
    summary = models.TextField(blank=True, null=True)

    class Meta:
        # table name cannot start with "dolt"
        db_table = "nautobot_version_control_pull_request_review"
        verbose_name_plural = "pull request reviews"

    def __str__(self):
        return f""""{self.pull_request}" reviewed by {self.reviewer}"""

    def get_absolute_url(self):
        """get_absolute_url returns a link to a view of a pull request review."""
        return reverse("plugins:nautobot_version_control:pull_request", args=[self.pull_request.id])
