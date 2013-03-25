from django.db import models, router
from django.utils.translation import ugettext as _
from django.utils.timezone import now

from deletion import LogicalDeleteCollector
from base import LogicalDeleteModelBase
from logicaldelete import managers


class LogicalDeleteModel(models.Model):
    __metaclass__ = LogicalDeleteModelBase
    date_removed = models.DateTimeField(null=True, blank=True, editable=False)

    objects = managers.LogicalDeletedManager()

    def active(self):
        return self.date_removed is None
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
    date_created = models.DateTimeField()
    date_modified = models.DateTimeField()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.date_created:
            self.date_created = now()
        self.date_modified = now()
        super(AuditModel, self).save(*args, **kwargs)


class Model(LogicalDeleteModel, AuditModel):
    """
    An abstract class with fields to track creation, modification and
    deletion of the model.
    """
    class Meta:
        abstract = True
