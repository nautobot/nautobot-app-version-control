from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection, connections
from django.db.models.deletion import CASCADE, SET_NULL
from django.urls import reverse
from django.utils.safestring import mark_safe

from nautobot.core.models import BaseModel
from nautobot.extras.utils import extras_features
from nautobot.users.models import User
from nautobot.utilities.querysets import RestrictedQuerySet


from dolt.versioning import db_for_commit, query_on_main_branch
from dolt.utils import author_from_user, DoltError


class DoltSystemTable(models.Model):

    objects = RestrictedQuerySet.as_manager()

    class Meta:
        abstract = True
        managed = False

    def validated_save(self):
        """
        Perform model validation during instance save.
        """
        self.full_clean()
        self.save()


#
# Branches
#


class Branch(DoltSystemTable):
    """
    Branch
    """

    name = models.TextField(primary_key=True)
    hash = models.TextField()
    latest_committer = models.TextField()
    latest_committer_email = models.TextField()
    latest_commit_date = models.DateTimeField()
    latest_commit_message = models.TextField()

    class Meta:
        managed = False
        db_table = "dolt_branches"
        verbose_name_plural = "branches"

    def __init__(self, *args, starting_branch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.starting_branch = starting_branch

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("plugins:dolt:branch", args=[self.name])

    @property
    def present_in_database(self):
        # determines `editing` flag in forms
        return Branch.objects.filter(name=self.name).exists()

    @staticmethod
    def active_branch():
        # query must have a primary key in result schema
        q = "SELECT name FROM dolt_branches WHERE name = active_branch();"
        return Branch.objects.raw(q)[0].name

    @property
    def active(self):
        return self.name == self.active_branch()

    @property
    def ahead_behind(self):
        merge_base = Commit.merge_base(self.name, "main")
        merge_base_commit = Commit.objects.get(commit_hash=merge_base)
        main_hash = Branch.objects.get(name="main").hash

        ahead = (
            Commit.objects.filter(date__gt=merge_base_commit.date)
            .using(db_for_commit(self.hash))
            .count()
        )
        behind = (
            Commit.objects.filter(date__gt=merge_base_commit.date)
            .using(db_for_commit(main_hash))
            .count()
        )

        return f"{ahead} ahead / {behind} behind"

    @property
    def created_by(self):
        m = self._branch_meta()
        return m.author if m else None

    @property
    def created_at(self):
        m = self._branch_meta()
        return m.created if m else None

    @property
    def source_branch(self):
        m = self._branch_meta()
        return m.source_branch if m else None

    def _branch_meta(self):
        try:
            return BranchMeta.objects.get(branch=self.name)
        except ObjectDoesNotExist:
            return None

    def head(self):
        return Commit.objects.get(commit_hash=self.hash)

    def merge(self, merge_branch, user=None):
        author = author_from_user(user)
        with connection.cursor() as cursor:
            cursor.execute("SET dolt_force_transaction_commit = 1;")
            cursor.execute(f"""SELECT dolt_checkout("{self.name}") FROM dual;""")
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
                cursor.execute(f"SELECT dolt_merge('--abort') FROM dual;")
                raise DoltError(
                    mark_safe(
                        f"""Merging <strong>{merge_branch}</strong> into <strong>{self}</strong> 
                            created merge conflicts. Resolve merge conflicts to reattempt the merge."""
                    )
                )

    def save(self, *args, **kwargs):
        with connection.cursor() as cursor:
            cursor.execute(
                f"INSERT INTO dolt_branches (name,hash) VALUES ('{self.name}',hashof('{self.starting_branch}'));"
            )


class BranchMeta(models.Model):
    branch = models.TextField(primary_key=True)
    source_branch = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
        # table name cannot start with "dolt"
        db_table = "plugin_dolt_branchmeta"


#
# Commits
#


class Commit(DoltSystemTable):
    """
    Commit
    """

    commit_hash = models.TextField(primary_key=True)
    committer = models.TextField()
    email = models.TextField()
    date = models.DateTimeField()
    message = models.TextField()

    class Meta:
        managed = False
        db_table = "dolt_log"
        verbose_name_plural = "commits"

    def __str__(self):
        return self.commit_hash

    def get_absolute_url(self):
        return reverse("plugins:dolt:commit", args=[self.commit_hash])

    @staticmethod
    def merge_base(left, right):
        with connection.cursor() as c:
            # author credentials not set
            c.execute(f"SELECT DOLT_MERGE_BASE('{left}', '{right}') FROM dual;")
            return c.fetchone()[0]

    @staticmethod
    def revert(commits, user):
        args = ", ".join([f"'{c}'" for c in commits])
        author = author_from_user(user)
        args += f", '--author', '{author}'"
        with connection.cursor() as c:
            c.execute(f"SELECT DOLT_REVERT({args}) FROM dual;")
            return c.fetchone()[0]

    @property
    def short_message(self):
        return self.message.split(";")[0]

    @property
    def present_in_database(self):
        # determines `editing` flag in forms
        return Commit.objects.filter(commit_hash=self.commit_hash).exists()

    @property
    def parent_commits(self):
        return CommitAncestor.objects.filter(commit_hash=self.commit_hash).values_list(
            "parent_hash", flat=True
        )

    def save(self, *args, using="default", branch=None, user=None, **kwargs):
        """"""
        if not branch:
            raise DoltError("must specify branch to create commit")
        self.message = self.message.replace('"', "")
        author = author_from_user(user)
        conn = connections[using]
        with conn.cursor() as cursor:
            cursor.execute(f"""SELECT dolt_checkout("{branch}") FROM dual;""")
            cursor.execute(
                f"""
            SELECT dolt_commit(
                '--all', 
                '--allow-empty',
                '--message', "{self.message}",
                '--author', "{author}")
            FROM dual;"""
            )
            hash = cursor.fetchone()[0]
        commit = Commit.objects.get(pk=hash)
        self.commit_hash = commit.commit_hash
        self.committer = commit.committer
        self.email = commit.email
        self.date = commit.date
        self.message = commit.message


class CommitAncestor(DoltSystemTable):
    """
    Commit Ancestor
    """

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
        # todo(andy): throw exception?
        pass


#
# Conflicts
#


class Conflicts(DoltSystemTable):
    """
    Conflicts
    """

    table = models.TextField(primary_key=True)
    num_conflicts = models.IntegerField()

    class Meta:
        managed = False
        db_table = "dolt_conflicts"
        verbose_name_plural = "conflicts"

    def __str__(self):
        return f"{self.table} ({self.num_conflicts})"


class ConstraintViolations(DoltSystemTable):
    """
    Foreign Key and Unique Key Constraint Violations
    """

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
        db_table = "plugin_dolt_pull_request"
        verbose_name_plural = "pull requests"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("plugins:dolt:pull_request", args=[self.id])

    def get_src_dest_branches(self):
        src = Branch.objects.get(name=self.source_branch)
        dest = Branch.objects.get(name=self.destination_branch)
        return src, dest

    @property
    def open(self):
        return self.state == PullRequest.OPEN

    @property
    def status(self):
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
        decision = (
            pr_reviews.exclude(state=PullRequestReview.COMMENTED)
            .order_by("-reviewed_at")
            .first()
        )
        if not decision:
            # all PRs are "comments"
            return "in-review"
        if decision.state == PullRequestReview.APPROVED:
            return "approved"
        if decision.state == PullRequestReview.BLOCKED:
            return "blocked"
        return "unknown"  # unreachable

    @property
    def commits(self):
        merge_base = Commit.objects.get(
            commit_hash=Commit.merge_base(self.source_branch, self.destination_branch)
        )
        db = db_for_commit(Branch.objects.get(name=self.source_branch).hash)
        return Commit.objects.filter(date__gt=merge_base.date).using(db)

    @property
    def num_commits(self):
        return self.commits.count()

    @property
    def num_reviews(self):
        return PullRequestReview.objects.filter(pull_request=self.pk).count()

    @property
    def summary_description(self):
        return f"""Merging {self.num_commits} commits from "{self.source_branch}" into "{self.destination_branch}" """

    def get_merge_candidate(self):
        pass

    def merge(self, user=None):
        try:
            src = Branch.objects.get(name=self.source_branch)
            dest = Branch.objects.get(name=self.destination_branch)
            dest.merge(src, user=user)
        except ObjectDoesNotExist as e:
            raise DoltError(f"error merging Pull Request {self}: {e}")
        self.state = PullRequest.MERGED
        self.save()


class PullRequestReview(BaseModel):
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
        db_table = "plugin_dolt_pull_request_review"
        verbose_name_plural = "pull request reviews"

    def __str__(self):
        return f""""{self.pull_request}" reviewed by {self.reviewer}"""

    def get_absolute_url(self):
        return reverse("plugins:dolt:pull_request", args=[self.pull_request.id])
