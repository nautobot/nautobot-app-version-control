from dolt.models import Branch, Conflicts, Commit


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
        return {c.table: c.num_conflicts for c in Conflicts.objects.all()}


def merge_candidate_exists(src, dest):
    name = _merge_candidate_name(src, dest)
    try:
        mc = Branch.objects.get(name=name)
        return merge_candidate_is_fresh(mc, src, dest)
    except Branch.DoesNotExist:
        return False


def merge_candidate_is_fresh(mc, src, dest):
    """
    A merge candidate (MC) is considered "fresh" is the
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
    mc = Branch(name=name, starting_branch=dest).save().merge(src)
    return mc


def get_or_make_merge_candidate(src, dest):
    mc = get_merge_candidate(src, dest)
    if not mc:
        mc = make_merge_candidate(src, dest)
    return mc


def _merge_candidate_name(src, dest):
    return f"--merge-candidate--{src}-{dest}--"
