from django.contrib.auth import get_user_model
from django.db import connection, models
from django.test import TransactionTestCase

from .models import OwnedModel


class OwnedNote(OwnedModel):
    """Test-only ownable model so US-03 proves isolation without real domain models."""

    title = models.CharField(max_length=100)

    class Meta:
        app_label = "core"


class OwnedScopingTests(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with connection.schema_editor() as editor:
            editor.create_model(OwnedNote)

    @classmethod
    def tearDownClass(cls):
        with connection.schema_editor() as editor:
            editor.delete_model(OwnedNote)
        super().tearDownClass()

    def test_for_user_returns_only_own_rows(self):
        alice = get_user_model().objects.create_user("alice")
        bob = get_user_model().objects.create_user("bob")
        OwnedNote.objects.create(owner=alice, title="a1")
        OwnedNote.objects.create(owner=bob, title="b1")

        self.assertQuerySetEqual(
            OwnedNote.objects.for_user(alice), ["a1"], transform=lambda n: n.title
        )
        self.assertQuerySetEqual(
            OwnedNote.objects.for_user(bob), ["b1"], transform=lambda n: n.title
        )

    def test_for_user_with_no_rows_returns_empty(self):
        carol = get_user_model().objects.create_user("carol")
        self.assertQuerySetEqual(OwnedNote.objects.for_user(carol), [])
