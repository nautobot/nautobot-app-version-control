"""tests.py contains unittests for the nautobot version control plugin."""


from django.test import override_settings, TransactionTestCase
from django.urls import reverse
from django.db import connection

from nautobot.utilities.testing import APITestCase, APIViewTestCases
from nautobot.users.models import User
from nautobot.dcim.models import Manufacturer

from nautobot_version_control.models import Branch, Commit, PullRequest, PullRequestReview
from nautobot_version_control.merge import get_conflicts_count_for_merge
from nautobot_version_control.utils import active_branch
from nautobot_version_control.constants import DOLT_DEFAULT_BRANCH


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class DoltTestCase(TransactionTestCase):
    """DoltTestCase wraps test cases with the subsequent router setting."""

    databases = ["default", "global"]


class TestBranches(DoltTestCase):
    """TestBranch Tests the creation and deletion of branches."""

    default = DOLT_DEFAULT_BRANCH

    def setUp(self):
        """setUp is ran before every testcase."""
        self.user, _ = User.objects.get_or_create(
            username="branch-test", email="branch-test@example.com", is_superuser=True
        )
        self.user_no_email, _ = User.objects.get_or_create(username="branch-test-no-email", is_superuser=True)

    def tearDown(self):
        """tearDown is ran after every testcase."""
        Branch.objects.exclude(name=self.default).delete()

    def test_default_branch(self):
        """test_default_branch asserts that the main branch exists and is preinitialized as the active branch."""
        self.assertEqual(Branch.objects.filter(name=self.default).count(), 1)
        self.assertEqual(active_branch(), self.default)

    def test_create_branch(self):
        """test_create_branch tests the creation of a new branch."""
        Branch(name="another", starting_branch=self.default).save()
        self.assertEqual(Branch.objects.filter(name="another").count(), 1)

    def test_delete_with_pull_requests(self):
        """test_delete_with_pull_requests tests that deleting a branch cannot happen unless you delete a branch first."""
        Branch(name="todelete", starting_branch=self.default).save()
        PullRequest.objects.create(
            title="My Review",
            state=0,
            source_branch="todelete",
            destination_branch=self.default,
            description="review1",
            creator=self.user,
        )

        # Try to delete the branch
        try:
            Branch.objects.filter(name="todelete").delete()
            self.fail("the branch delete should've failed")
        except:  # nosec pylint: disable=W0702 # noqa
            pass

        # Delete the pr and try again
        PullRequest.objects.filter(title="My Review").delete()
        Branch.objects.filter(name="todelete").delete()
        self.assertEqual(Branch.objects.filter(name="todelete").count(), 0)

    def test_merge_ff(self):
        """test_merge_ff tests whether a ff merge works."""
        Branch(name="ff", starting_branch=self.default).save()
        main = Branch.objects.get(name=self.default)
        other = Branch.objects.get(name="ff")

        Commit(message="commit any changes").save(user=self.user)

        # Commit().save() doesn't update the PK correctly, it appears - .refresh_from_db() fails with
        # "Commit matching query does not exist". So we need to load it fresh from the DB instead:
        commit = Commit.objects.order_by("date").last()
        self.assertEqual(commit.committer, self.user.username)
        self.assertEqual(commit.email, self.user.email)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.all().delete()
        Manufacturer.objects.create(name="m1", slug="m-1")
        Commit(message="added a manufacturer").save(user=self.user_no_email)

        commit = Commit.objects.order_by("date").last()
        self.assertEqual(commit.committer, self.user_no_email.username)
        self.assertEqual(commit.email, f"{self.user_no_email.username}@nautobot.invalid")

        # Now do a merge
        main.checkout()
        main.merge(other, user=self.user)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM dolt_log where message=%s", ["added a manufacturer"])
            self.assertFalse(cursor.fetchone()[0] is None)

        # Verify the the main branch has the data
        self.assertEqual(Manufacturer.objects.filter(name="m1", slug="m-1").count(), 1)

    def test_merge_no_ff(self):
        """test_merge_no_ff tests whether a non-ff merge works."""
        Branch(name="noff", starting_branch=self.default).save()
        main = Branch.objects.get(name=self.default)
        other = Branch.objects.get(name="noff")

        # # Create a change on main
        Manufacturer.objects.create(name="m2", slug="m-2")
        Commit(message="commit m2").save(user=self.user)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.create(name="m3", slug="m-3")
        Commit(message="commit m3").save(user=self.user_no_email)

        # Now do a merge
        main.checkout()
        main.merge(other, user=self.user)
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM dolt_log where message=%s", ["commit m3"])
            self.assertFalse(cursor.fetchone()[0] is None)

        # Verify the the main branch has the data
        self.assertEqual(Manufacturer.objects.filter(name="m2", slug="m-2").count(), 1)
        self.assertEqual(Manufacturer.objects.filter(name="m3", slug="m-3").count(), 1)

    def test_merge_conflicts(self):
        """test_merge_conflicts tests whether a merge with conflicts is detected and errors."""
        main = Branch.objects.get(name=self.default)
        Manufacturer.objects.all().delete()
        Manufacturer.objects.create(name="m2", slug="m-2")
        Commit(message="commit m2 with slug m-2").save(user=self.user)

        Branch(name="conflicts", starting_branch=self.default).save()
        other = Branch.objects.get(name="conflicts")

        # # Create a change on main
        Manufacturer.objects.filter(name="m2", slug="m-2").update(slug="m-15")
        Commit(message="commit m2 with slug m-15").save(user=self.user)

        # Checkout to the other branch and make a change
        other.checkout()
        Manufacturer.objects.filter(name="m2", slug="m-2").update(slug="m-16")
        Commit(message="commit m2 with slug m-16").save(user=self.user)

        # Now do a merge. It should throw an exception due to conflicts
        main.checkout()
        try:
            main.merge(other, user=self.user)
            self.fail("this should error for conflicts")
        except:  # nosec # pylint: disable=W0702 # noqa
            pass

        # Validate that any potential conflicts actually exist
        self.assertEqual(get_conflicts_count_for_merge(other, main), 1)
        main.checkout()  # need this because of post truncate action with TransactionTests


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class TestApp(APITestCase):
    """TestApp tests the availability of the root api endpoint."""

    databases = ["default", "global"]

    def test_root(self):
        """test_root tests getting the api root."""
        url = reverse("plugins-api:nautobot_version_control-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class TestBranchesApi(APITestCase, APIViewTestCases):
    """TestBranchesApi tests the get,create,delete,etc. of the Branches api."""

    databases = ["default", "global"]
    model = Branch
    brief_fields = ["name", "starting_branch"]
    create_data = [
        {"name": "b4", "starting_branch": "b1"},
        {"name": "b5", "starting_branch": "b2"},
        {"name": "b6", "starting_branch": "b3"},
    ]

    @classmethod
    def setUpTestData(cls):
        """creates some test data for test suite."""
        Branch.objects.create(name="b1", starting_branch=DOLT_DEFAULT_BRANCH)
        Branch.objects.create(name="b2", starting_branch=DOLT_DEFAULT_BRANCH)
        Branch.objects.create(name="b3", starting_branch=DOLT_DEFAULT_BRANCH)

    # The ApiViewTestCase mixin handles get, create, etc. thoroughly but it's a useful exercise for readers to understand
    # what is happening in the background
    def test_get(self):
        """test_get tets the get method of the API."""
        url = reverse("plugins-api:nautobot_version_control-api:branch-list")
        self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
        response = self.client.get(f"{url}?format=json", **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertTrue(data["count"] > 0)


class TestPullRequestApi(APITestCase, APIViewTestCases):
    """TestPullRequestApi tests the PullRequest api."""

    databases = ["default", "global"]
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

    @classmethod
    def setUpTestData(cls):
        """setUpTestData setups test data."""
        User.objects.get_or_create(username="pr-reviewer", is_superuser=True)
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
        """test_get tests the pull-request get api."""
        url = reverse("plugins-api:nautobot_version_control-api:pullrequest-list")
        self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
        response = self.client.get(f"{url}?format=json", **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 3)


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class TestPullRequests(DoltTestCase):
    """TestPullRequests tests the functionality of the PullRequest model."""

    default = DOLT_DEFAULT_BRANCH

    def setUp(self):
        """setUp runs before every test case."""
        self.user = User.objects.get_or_create(username="branch-test", is_superuser=True)[0]
        self.main = Branch.objects.get(name=self.default)

    def tearDown(self):
        """tearDown runs after every test case."""
        PullRequest.objects.all().delete()
        Branch.objects.exclude(name=self.default).delete()

    def test_pull_requests_write_to_main(self):
        """test_pull_requests_write_to_main asserts that pull request objects hit the global db."""
        Branch(name="test", starting_branch=self.default).save()
        Branch(name="test2", starting_branch=self.default).save()
        test_branch = Branch.objects.get(name="test")

        # Create a PR from the test branch
        test_branch.checkout()
        PullRequest.objects.create(
            title="MyPr",
            state=0,
            source_branch=test_branch.name,
            destination_branch=self.default,
            description="Can I get a review",
            creator=self.user,
        )
        Commit(message="commit any changes").save(user=self.user)

        # Checkout to the main branch and verify that the pull request exists
        self.main.checkout()
        self.assertEqual(
            1,
            PullRequest.objects.filter(source_branch=test_branch.name, destination_branch=self.default).count(),
        )


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class TestPullRequestReviewsApi(APITestCase, APIViewTestCases):
    """TestPullRequestReviewsApi tests whether the PullRequestReview model api."""

    databases = ["default", "global"]
    model = PullRequestReview
    brief_fields = ["pull_request", "reviewer", "reviewed_at", "state", "summary"]

    @classmethod
    def setUpTestData(cls):
        """setupTestData create test data for the suite."""
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
        """test_get tests the PullRequestReview get_api."""
        url = reverse("plugins-api:nautobot_version_control-api:pullrequestreview-list")
        self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
        response = self.client.get(f"{url}?format=json", **self.header)

        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["count"], 2)


@override_settings(DATABASE_ROUTERS=["nautobot_version_control.routers.GlobalStateRouter"])
class TestCommitsApi(APITestCase, APIViewTestCases):
    """TestCommitsApi tests the Commit model Api."""

    databases = ["default", "global"]
    model = Commit

    def test_root(self):
        """test commits."""
        url = reverse("plugins-api:nautobot_version_control-api:commit-list")
        self.add_permissions(f"{self.model._meta.app_label}.view_{self.model._meta.model_name}")
        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertEqual(response.status_code, 200)
