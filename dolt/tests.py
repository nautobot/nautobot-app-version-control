from django.test import override_settings, TestCase, TransactionTestCase

from dolt.models import Branch
from dolt.utils import active_branch
from dolt.constants import DOLT_DEFAULT_BRANCH


@override_settings(DATABASE_ROUTERS=["dolt.routers.GlobalStateRouter"])
class DoltTestCase(TransactionTestCase):
    databases = ["default", "global"]


class TestBranches(DoltTestCase):
    default = DOLT_DEFAULT_BRANCH

    def setUp(self):
        Branch(name="other", starting_branch=self.default).save()

    def tearDown(self):
        Branch.objects.exclude(name=self.default).delete()

    def test_default_branch(self):
        self.assertEqual(Branch.objects.filter(name=self.default).count(), 1)
        self.assertEqual(active_branch(), self.default)

    def test_create_branch(self):
        Branch(name="another", starting_branch=self.default).save()
        self.assertEqual(Branch.objects.all().count(), 3)
