import json

from django.db import connection

from dolt.models import (
    Branch,
    Conflicts,
    ConstraintViolations,
    Commit,
)
from dolt.utils import author_from_user
from dolt.tables import (
    ConflictsSummaryTable,
    ConflictsTable,
    ConstraintViolationsTable,
)
from dolt.versioning import query_on_branch


def get_conflicts_for_merge(src, dest):
    """
    Gather a merge-candidate for `src` and `dest`,
    then return Conflicts created by the merge

    TODO: currently we return conflicts summary,
        we need granular row-level conflicts and
        constraint violations.
    """
    mc = get_or_make_merge_candidate(src, dest)
    conflicts = Conflicts.objects.all()
    violations = ConstraintViolations.objects.all()
    with query_on_branch(mc):
        if not conflicts_or_violations_exist():
            return {}
        return {
            "summary": make_conflict_summary_table(conflicts, violations),
            "conflicts": make_conflict_table(mc, conflicts),
            "violations": make_constraint_violations_table(mc, violations),
        }


def make_conflict_summary_table(conflicts, violations):
    summary = {
        c.table: {"table": c.table, "num_conflicts": c.num_conflicts} for c in conflicts
    }
    for v in violations:
        if v.table not in summary:
            summary[v.table] = {"table": v.table}
        summary[v.table]["num_violations"] = v.num_violations
    return list(summary.values())


def make_conflict_table(merge_candidate, conflicts):
    rows = []
    for c in conflicts:
        rows.extend(get_rows_level_conflicts(c))
    return ConflictsTable(rows)


def get_rows_level_conflicts(conflict):
    """
    todo
    """

    def dedupe_conflicts(obj):
        if type(obj) is str:
            obj = json.loads(obj)
        obj2 = {}
        for k, v in obj.items():
            pre = "our_"
            if not k.startswith(pre):
                continue
            suf = k[len(pre) :]
            ours = obj[f"our_{suf}"]
            theirs = obj[f"their_{suf}"]
            base = obj[f"base_{suf}"]
            if ours != theirs and ours != base:
                obj2[f"our_{suf}"] = ours
                obj2[f"their_{suf}"] = theirs
                obj2[f"base_{suf}"] = base
        return obj2

    with connection.cursor() as cursor:
        # introspect table schema to query conflict data as json
        cursor.execute(f"DESCRIBE dolt_conflicts_{conflict.table}")
        fields = ",".join([f"'{tup[0]}', {tup[0]}" for tup in cursor.fetchall()])

        cursor.execute(
            f"""SELECT base_id, JSON_OBJECT({fields})
                FROM dolt_conflicts_{conflict.table};"""
        )
        return [
            {
                "table": conflict.table,
                "id": tup[0],
                "conflicts": dedupe_conflicts(tup[1]),
            }
            for tup in cursor.fetchall()
        ]


def make_constraint_violations_table(merge_candidate, violations):
    rows = []
    for v in violations:
        rows.extend(get_rows_level_violations(v))
    return ConstraintViolationsTable(rows)


def get_rows_level_violations(violation):
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT id, violation_type, violation_info
                FROM dolt_constraint_violations_{violation.table};"""
        )
        return [
            {
                "table": violation.table,
                "id": tup[0],
                "violation_type": tup[1],
                "violations": tup[2],
            }
            for tup in cursor.fetchall()
        ]


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
        cursor.execute(f"""SELECT dolt_add("-A") FROM dual;""")
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
