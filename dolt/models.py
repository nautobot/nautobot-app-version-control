from django.core.exceptions import ObjectDoesNotExist
from django.db import models, connection
from django.urls import reverse

from nautobot.users.models import User
from nautobot.utilities.querysets import RestrictedQuerySet

from dolt.versioning import query_on_branch
from dolt.querysets import CommitQuerySet

__all__ = (
    "Branch",
    "Commit",
)


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
    # TODO: expose working hash in Dolt?
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
        # self.user = user
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

    def merge(self, merge_branch):
        # todo: check for existence
        self.checkout_branch()
        with connection.cursor() as cursor:
            cursor.execute(f"""SELECT dolt_merge('{merge_branch}') FROM dual;""")
        Commit(message=f"merged {merge_branch} into {self.name}").save()

    def save(self, *args, **kwargs):
        with connection.cursor() as cursor:
            # TODO: ok to use `connection` (for now) because `dolt_branches` is global
            cursor.execute(
                f"INSERT INTO dolt_branches (name,hash) VALUES ('{self.name}',hashof('{self.starting_branch}'));"
            )


class BranchMeta(models.Model):
    branch = models.TextField(primary_key=True)
    source_branch = models.TextField()
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    class Meta:
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
        q = "SELECT * FROM dolt_log WHERE commit_hash = DOLT_MERGE_BASE(%s, %s)"
        return Commit.objects.raw(q, [left, right])[0]

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

    def save(self, *args, author=None, **kwargs):
        if not author:
            author = "nautobot <nautobot@ntc.com>"

        with connection.cursor() as cursor:
            # todo(andy): remove '--allow-empty', check for contents
            # TODO: zach says no (branch param + specific connection)
            cursor.execute(
                f"""
            SELECT dolt_commit(
                '--all', 
                '--force',
                '--allow-empty',
                '--message', '{self.message}',
                '--author', '{author}')
            FROM dual
            ;"""
            )
            commit_hash = cursor.fetchone()[0]

        commit = Commit.objects.get(pk=commit_hash)
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
