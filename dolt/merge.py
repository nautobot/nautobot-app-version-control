from django.db import connection

from dolt.models import (
    Branch,
    Conflicts,
    ConstraintViolations,
    Commit,
    author_from_user,
)
from dolt.tables import ConflictsTable, ConstraintViolationsTable
from dolt.versioning import query_on_branch


def get_conflicts_for_merge(src, dest):
    """
    Gather a merge-candidate for `src` and `dest`,
    then return Conflicts created by the merge

    TODO: currenly we return conflicts summary,
        we need granular row-level conflicts and
        constraint violations.
    """
    mc = get_or_make_merge_candidate(src, dest)
    with query_on_branch(mc):
        if not conflicts_or_violations_exist():
            return {}
        return {
            "summary": {
                "conflicts": ConflictsTable(Conflicts.objects.all()),
                "violations": ConstraintViolationsTable(
                    ConstraintViolations.objects.all()
                ),
            },
        }


def merge_candidate_exists(src, dest):
    name = _merge_candidate_name(src, dest)
    try:
        mc = Branch.objects.get(name=name)
        return merge_candidate_is_fresh(mc, src, dest)
    except Branch.DoesNotExist:
        return False


def merge_candidate_is_fresh(mc, src, dest):
    """
    A merge candidate (MC) is considered "fresh" if the
    source and destination branches used to create the
    MC are unchanged since the MC was created.
    """
    if not mc:
        return False
    src_stable = Commit.merge_base(mc, src) == src.hash
    dest_stable = Commit.merge_base(mc, dest) == dest.hash
    return src_stable and dest_stable


def get_merge_candidate(src, dest):
    if merge_candidate_exists(src, dest):
        name = _merge_candidate_name(src, dest)
        return Branch.objects.get(name=name)
    return None


def make_merge_candidate(src, dest):
    name = _merge_candidate_name(src, dest)
    Branch(name=name, starting_branch=dest).save()
    with connection.cursor() as cursor:
        cursor.execute("SET @@dolt_force_transaction_commit = 1;")
        cursor.execute(f"""SELECT dolt_checkout("{name}") FROM dual;""")
        cursor.execute(f"""SELECT dolt_merge("{src}") FROM dual;""")
        msg = f"""creating merge candidate with src: "{src}" and dest: "{dest}"."""
        cursor.execute(
            f"""SELECT dolt_commit(
                    '--force',
                    '--all', 
                    '--allow-empty',
                    '--message', '{msg}',
                    '--author', '{author_from_user(None)}') FROM dual;"""
        )
    return Branch.objects.get(name=name)


def get_or_make_merge_candidate(src, dest):
    mc = get_merge_candidate(src, dest)
    if not mc:
        mc = make_merge_candidate(src, dest)
    return mc


def _merge_candidate_name(src, dest):
    return f"xxx-merge-candidate--{src}--{dest}"


def conflicts_or_violations_exist():
    conflicts = Conflicts.objects.count() != 0
    violations = ConstraintViolations.objects.count() != 0
    return conflicts or violations
