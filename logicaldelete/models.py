from datetime import datetime
from django.db import models, router
from deletion import LogicalDeleteCollector
from base import LogicalDeleteModelBase
from logicaldelete import managers
from django.utils.translation import ugettext as _


class LogicalDeleteModel(models.Model):
    __metaclass__ = LogicalDeleteModelBase
    date_removed = models.DateTimeField(null=True, blank=True, editable=False)

    objects = managers.LogicalDeletedManager()

    def active(self):
        return self.date_removed == None
    active.short_description = _('Active')
    active.boolean = True

    def delete(self, using=None):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)

        collector = LogicalDeleteCollector(using=using)
        collector.collect([self])
        collector.delete()

    delete.alters_data = True

    def undelete(self):
        self.__class__.objects.filter(pk=self.pk).undelete()

    class Meta:
        abstract = True


class AuditModel(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Model(LogicalDeleteModel, AuditModel):
    """
    An abstract class with fields to track creation, modification and
    deletion of the model.
    """
    class Meta:
        abstract = True
