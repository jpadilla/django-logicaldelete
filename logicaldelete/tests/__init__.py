# -*- coding: utf-8; -*-
from django.conf import settings
from django.core.management import call_command
from django.db.models import loading
from django import test
from models.models import TestModel, RelatedModel, Related2Model, RelatedMany


class TestCase(test.TestCase):

    def _pre_setup(self):
        # Add the models to the db.
        self._original_installed_apps = list(settings.INSTALLED_APPS)
        settings.INSTALLED_APPS = list(settings.INSTALLED_APPS)
        settings.DEBUG = True
        for app in self.apps:
            settings.INSTALLED_APPS.append(app)
        loading.cache.loaded = False
        call_command('syncdb', interactive=False, verbosity=0, migrate=False)
        # Call the original method that does the fixtures etc.
        super(TestCase, self)._pre_setup()

    def _post_teardown(self):
        # Call the original method.
        super(TestCase, self)._post_teardown()
        # Restore the settings.
        settings.INSTALLED_APPS = self._original_installed_apps
        loading.cache.loaded = False


class DeleteRelatedAndPlainModelTestCase(TestCase):
    apps = ('logicaldelete.tests.models',)
    fixtures = ['delete_related_and_plain_model.json']

    def test_delete_related_and_safe_true(self):
        """
        When safe_deletion=True we not delete related plain models
        """
        TestModel._logicaldelete_meta.safe_deletion = True
        TestModel._logicaldelete_meta.delete_related = True
        TestModel.objects.get(pk=1).delete()
        self.assertTrue(TestModel.objects.only_deleted().filter(pk=1).exists(),
                        "Object not deleted logicaly")
        self.assertTrue(RelatedModel.objects.filter(pk=1).exists(),
                        "Related plain object was deleted when safe_deletion=True")
        self.assertTrue(Related2Model.objects.only_deleted().filter(pk=1).exists(),
                        "Not delete related logicaldelete model")

    def test_delete_related_true_and_safe_false(self):
        """
        When safe_deletion=False we delete related plain models,
        and all objects that related with plain model
        """
        TestModel._logicaldelete_meta.safe_deletion = False
        TestModel._logicaldelete_meta.delete_related = True
        instance = TestModel.objects.get(pk=1)
        instance.delete()
        self.assertIsNotNone(instance.date_removed, "Instance not updated")
        self.assertTrue(TestModel.objects.only_deleted().filter(pk=1).exists(),
                        "Object not deleted logicaly")
        self.assertFalse(RelatedModel.objects.filter(pk=1).exists(),
                        "Related plain object not deleted when safe_deletion=False")
        self.assertFalse(Related2Model.objects.filter(pk=1).exists(),
            "Related logicaldelete that related with plain object "
            "not deleted when safe_deletion=False")

    def test_delete_related_false(self):
        """
        When delete_related=False we delete logical model only
        """
        TestModel._logicaldelete_meta.delete_related = False
        TestModel._logicaldelete_meta.safe_deletion = False
        TestModel.objects.get(pk=1).delete()
        self.assertTrue(TestModel.objects.only_deleted().filter(pk=1).exists(),
                        "Object not deleted logicaly")
        self.assertTrue(RelatedModel.objects.filter(pk=1).exists(),
                         "Related plain object deleted when delete_related=False")
        self.assertTrue(Related2Model.objects.filter(pk=1).exists(),
                         "Related logicaldelete that related with plain object "
                         "deleted when delete_related=False")


class DeleteRelatedModelTestCase(TestCase):
    apps = ('logicaldelete.tests.models',)
    fixtures = ['delete_related.json']

    def test_delete_related_true_and_safe_false_case2(self):
        """
        When safe_deletion=False we delete related plain models,
        and all objects that related with plain model
        But not delete related logical model objects.
        """
        TestModel._logicaldelete_meta.safe_deletion = False
        TestModel._logicaldelete_meta.delete_related = True
        TestModel.objects.get(pk=1).delete()

        self.assertTrue(TestModel.objects.only_deleted().get(pk=1).active,
                        "Object not deleted logicaly")
        self.assertTrue(Related2Model.objects.only_deleted().filter(pk=1).exists(),
            "Related logicaldelete incorrectly removed when delete_related=True "
            "and safe_deletion=False")

    def test_delete_related_true_and_delete_related_false_on_related(self):
        """
        When safe_deletion=True we not delete related plain and logical
        model objects.
        """
        TestModel._logicaldelete_meta.safe_deletion = False
        TestModel._logicaldelete_meta.delete_related = True
        Related2Model._logicaldelete_meta.delete_related = False
        TestModel.objects.get(pk=1).delete()
        self.assertTrue(TestModel.objects.only_deleted().filter(pk=1).exists(),
                        "Object not deleted logicaly")
        self.assertTrue(Related2Model.objects.only_deleted().filter(pk=1).exists(),
                        "Related logicaldelete incorrectly removed when delete_related=True "
                        "and safe_deletion=False")
        self.assertTrue(RelatedModel.objects.filter(pk=1).exists(),
                        "Check cascade delete_related")


class DeleteBatchesTestCase(TestCase):
    apps = ('logicaldelete.tests.models',)
    fixtures = ['delete_batches.json']

    def test_delete_batches_false_case(self):
        """
        When delete_batches=False we don't delete m2m relations.
        """
        TestModel._logicaldelete_meta.delete_batches = False
        TestModel.objects.get(pk=1).delete()

        self.assertEqual(RelatedMany.objects.get(pk=1).related.only_deleted().count(), 1,
                        "Batches deleted when delete_batches=False")

    def test_delete_batches_true_case(self):
        """
        When delete_batches=False we delete m2m relations.
        """
        TestModel._logicaldelete_meta.delete_batches = True
        TestModel.objects.get(pk=1).delete()

        self.assertEqual(RelatedMany.objects.get(pk=1).related.everything().count(), 0,
                         "Batches NOT deleted when delete_batches=True")
