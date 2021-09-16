from django.test import TestCase, TransactionTestCase

from dolt.models import Branch, Commit, PullRequest, PullRequestReview
from dolt.merge import get_conflicts_count_for_merge, get_merge_candidate
from dolt.utils import active_branch, DoltError
from dolt.constants import DOLT_DEFAULT_BRANCH
from django.urls import reverse
from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.users.models import User
from django.db import transaction, connection
from nautobot.dcim.models import Manufacturer


class TestBranches(TransactionTestCase):
    def setUp(self):
        with transaction.atomic():
            try:
                self.user = User.objects.get_or_create(
                    username="branch-test", is_superuser=True
                )[0]
            except:
                pass

    def test_default_branch(self):
        self.assertEqual(Branch.objects.filter(name=DOLT_DEFAULT_BRANCH).count(), 1)
        self.assertEqual(active_branch(), DOLT_DEFAULT_BRANCH)

    def test_delete_with_pull_requests(self):
        Branch(name="todelete", starting_branch=DOLT_DEFAULT_BRANCH).save()
        PullRequest.objects.create(
            title="My Review",
            state=0,
            source_branch="todelete",
            destination_branch=DOLT_DEFAULT_BRANCH,
            description="review1",
            creator=self.user,
        )

        # Try to delete the branch
        try:
            # Need to ensure failed delete doesn't break subsequent queries
            with transaction.atomic():
                Branch.objects.filter(name="todelete").delete()
            self.fail("the branch delete should've failed")
        except:
            pass

        # Delete the pr and try again
        PullRequest.objects.filter(title="My Review").delete()
        Branch.objects.filter(name="todelete").delete()
        self.assertEqual(Branch.objects.filter(name="todelete").count(), 0)

    def test_merge_ff(self):
        Branch(name="ff", starting_branch=DOLT_DEFAULT_BRANCH).save()
        main = Branch.objects.get(name=DOLT_DEFAULT_BRANCH)
        other = Branch.objects.get(name="ff")

        c0 = Commit(message="commit any changes")
        c0.save(user=self.user)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.all().delete()
        Manufacturer.objects.create(name="m1", slug="m-1")
        c1 = Commit(message="added a manufacturer")
        c1.save(user=self.user)

        # Now do a merge
        main.checkout()
        main.merge(other, user=self.user)
        with connection.cursor() as cursor:
            cursor.execute(
                f"SELECT * FROM dolt_log where message='added a manufacturer'"
            )
            self.assertFalse(cursor.fetchone()[0] == None)

        # Verify the the main branch has the data
        self.assertEqual(Manufacturer.objects.filter(name="m1", slug="m-1").count(), 1)

    def test_merge_no_ff(self):
        Branch(name="noff", starting_branch=DOLT_DEFAULT_BRANCH).save()
        main = Branch.objects.get(name=DOLT_DEFAULT_BRANCH)
        other = Branch.objects.get(name="noff")

        # # Create a change on main
        Manufacturer.objects.create(name="m2", slug="m-2")
        c0 = Commit(message="commit m2")
        c0.save(user=self.user)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.create(name="m3", slug="m-3")
        c1 = Commit(message="commit m3")
        c1.save(user=self.user)

        # Now do a merge
        main.checkout()
        main.merge(other, user=self.user)
        with connection.cursor() as cursor:
            cursor.execute(f"SELECT * FROM dolt_log where message='commit m3'")
            self.assertFalse(cursor.fetchone()[0] == None)

        # Verify the the main branch has the data
        self.assertEqual(Manufacturer.objects.filter(name="m2", slug="m-2").count(), 1)
        self.assertEqual(Manufacturer.objects.filter(name="m3", slug="m-3").count(), 1)

    def test_merge_conflicts(self):
        main = Branch.objects.get(name=DOLT_DEFAULT_BRANCH)
        Manufacturer.objects.all().delete()
        Manufacturer.objects.create(name="m2", slug="m-2")
        Commit(message="commit m2 with slug m-2").save(user=self.user)

        Branch(name="conflicts", starting_branch=DOLT_DEFAULT_BRANCH).save()
        other = Branch.objects.get(name="conflicts")

        # # Create a change on main
        Manufacturer.objects.filter(name="m2", slug="m-2").update(slug="m-15")
        Commit(message="commit m2 with slug m-15").save(user=self.user)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.filter(name="m2", slug="m-2").update(slug="m-16")
        Commit(message="commit m2 with slug m-16").save(user=self.user)

        # Now do a merge
        main.checkout()
        try:
            main.merge(other, user=self.user)
            self.fail("this should error for conflicts")
        except:
            pass

        self.assertEquals(get_conflicts_count_for_merge(other, main), 1)
        main.checkout()  # need this because of post truncate action with TransactionTests


class TestApp(APITestCase):  # pylint: disable=too-many-ancestors
    def test_root(self):
        url = reverse("plugins-api:dolt-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class TestBranchesApi(APITestCase, APIViewTestCases):
    model = Branch
    brief_fields = ["name", "starting_branch"]
    create_data = [
        {"name": "b4", "starting_branch": "b1"},
        {"name": "b5", "starting_branch": "b2"},
        {"name": "b6", "starting_branch": "b3"},
    ]

    @classmethod
    def setUpTestData(cls):
        Branch.objects.create(name="b1", starting_branch=DOLT_DEFAULT_BRANCH)
        Branch.objects.create(name="b2", starting_branch=DOLT_DEFAULT_BRANCH)
        Branch.objects.create(name="b3", starting_branch=DOLT_DEFAULT_BRANCH)

    # The ApiViewTestCase mixin handles get,create, etc. thoroughly but it's a useful exercise for readers to understand
    # what is happening in the background
    def test_get(self):
        url = reverse("plugins-api:dolt-api:branch-list")
        self.add_permissions(
            f"{self.model._meta.app_label}.view_{self.model._meta.model_name}"
        )
        response = self.client.get("{}?format=json".format(url), **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["count"] > 0)


class TestPullRequestApi(APITestCase, APIViewTestCases):
    model = PullRequest
    brief_fields = [
        "title",
        "state",
        "source_branch",
        "destination_branch",
        "description",
        "creator",
        "created_at",
    ]
    create_data = [
        {
            "title": "Review 4",
            "state": 0,
            "source_branch": "b1",
            "destination_branch": "b2",
            "description": "",
            "creator": User.objects.get(username="pr-reviewer"),
        },
        {
            "title": "Review 5",
            "state": 1,
            "source_branch": "b1",
            "destination_branch": "b3",
            "description": "",
            "creator": User.objects.get(username="pr-reviewer"),
        },
    ]

    @classmethod
    def setUpTestData(cls):
        User.objects.create(username="pr-reviewer", is_superuser=True)
        PullRequest.objects.create(
            title="Review 1",
            state=0,
            source_branch="b1",
            destination_branch="b2",
            description="review1",
            creator=User.objects.get(username="pr-reviewer"),
        )
        PullRequest.objects.create(
            title="Review 2",
            state=0,
            source_branch="b2",
            destination_branch="b3",
            description="review 2",
            creator=User.objects.get(username="pr-reviewer"),
        )
        PullRequest.objects.create(
            title="Review 3",
            state=0,
            source_branch="b3",
            destination_branch="b1",
            description="review 3",
            creator=User.objects.get(username="pr-reviewer"),
        )

    def test_get(self):
        url = reverse("plugins-api:dolt-api:pullrequest-list")
        self.add_permissions(
            f"{self.model._meta.app_label}.view_{self.model._meta.model_name}"
        )
        response = self.client.get("{}?format=json".format(url), **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 3)


class TestPullRequestCommentsApi(APITestCase, APIViewTestCases):
    model = PullRequestReview
    brief_fields = ["pull_request", "reviewer", "reviewed_at", "state", "summary"]

    @classmethod
    def setUpTestData(cls):
        # Create the Pull Request Data before the reviews
        TestPullRequestApi.setUpTestData()
        PullRequestReview.objects.create(
            pull_request=PullRequest.objects.get(title="Review 1"),
            reviewer=User.objects.get(username="pr-reviewer"),
            state=1,
            summary="nice job",
        )
        PullRequestReview.objects.create(
            pull_request=PullRequest.objects.get(title="Review 2"),
            reviewer=User.objects.get(username="pr-reviewer"),
            state=0,
            summary="This is a comment",
        )

    def test_get(self):
        url = reverse("plugins-api:dolt-api:pullrequestreview-list")
        self.add_permissions(
            f"{self.model._meta.app_label}.view_{self.model._meta.model_name}"
        )
        response = self.client.get("{}?format=json".format(url), **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 1)


class TestCommitsApi(APITestCase, APIViewTestCases):
    model = Commit

    def test_root(self):
        url = reverse("plugins-api:dolt-api:commit-list")
        self.add_permissions(
            f"{self.model._meta.app_label}.view_{self.model._meta.model_name}"
        )
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)
