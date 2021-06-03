from django.db.models.signals import m2m_changed, pre_delete, post_save

from nautobot_dolt.models import Commit


class AutoDoltCommit(object):
    """
    adapted from `nautobot.extras.context_managers`
    """

    def __init__(self, request):
        self.request = request
        self.commit = False
        # self.id = uuid.uuid4()

    def __enter__(self):
        # Connect our receivers to the post_save and post_delete signals.
        post_save.connect(
            self._handle_changed_object, dispatch_uid="auto_dolt_commit_changed_object"
        )
        m2m_changed.connect(
            self._handle_changed_object, dispatch_uid="auto_dolt_commit_changed_object"
        )
        pre_delete.connect(
            self._handle_deleted_object, dispatch_uid="auto_dolt_commit_deleted_object"
        )

    def __exit__(self, type, value, traceback):
        if self.commit:
            self._commit()

        # Disconnect change logging signals. This is necessary to avoid recording any errant
        # changes during test cleanup.
        post_save.disconnect(
            self._handle_changed_object, dispatch_uid="auto_dolt_commit_changed_object"
        )
        m2m_changed.disconnect(
            self._handle_changed_object, dispatch_uid="auto_dolt_commit_changed_object"
        )
        pre_delete.disconnect(
            self._handle_deleted_object, dispatch_uid="auto_dolt_commit_deleted_object"
        )

    def _handle_changed_object(self, sender, instance, **kwargs):
        """
        Fires when an object is created or updated.
        """
        # Queue the object for processing once the request completes
        # todo: cleanup conditions
        if "created" in kwargs:
            self.commit = True
        elif kwargs.get("action") in ["post_add", "post_remove"] and kwargs["pk_set"]:
            # m2m_changed with objects added or removed
            self.commit = True

    def _handle_deleted_object(self, sender, instance, **kwargs):
        """
        Fires when an object is deleted.
        """
        self.commit = True

    def _commit(self):
        # todo: use ObjectChange to create commit message
        Commit(message="auto dolt commit").save(author=self._get_commit_author())

    def _get_commit_author(self):
        usr = self.request.user
        if usr and usr.username and usr.email:
            return f"{usr.username} <{usr.email}>"
        return None
