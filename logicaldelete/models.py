from datetime import datetime
from django.db import models, router
from deletion import LogicalDeleteCollector
from base import LogicalDeleteModelBase


class LogicalDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        return super(LogicalDeletedManager, self).get_query_set().filter(date_removed__isnull=True)

    def everything(self):
        qs = super(LogicalDeletedManager, self).get_query_set()
        # for related manager
        if hasattr(self, 'core_filters'):
            return qs.filter(**self.core_filters)
        return qs

    def only_deleted(self):
        return self.everything().filter(date_removed__isnull=False)

    def get(self, *args, **kwargs):
        ''' if a specific record was requested, return it even if it's deleted '''
        return self.everything().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        ''' if pk was specified as a kwarg, return even if it's deleted '''
        if 'pk' in kwargs:
            return self.everything().filter(*args, **kwargs)
        return self.get_query_set().filter(*args, **kwargs)


class LogicalDeleteModel(models.Model):
    __metaclass__ = LogicalDeleteModelBase
    date_removed  = models.DateTimeField(null=True, blank=True, editable=False)

    objects    = LogicalDeletedManager()

    def active(self):
        return self.date_removed == None
    active.boolean = True

    def delete(self, using=None):
        using = using or router.db_for_write(self.__class__, instance=self)
        assert self._get_pk_val() is not None, "%s object can't be deleted because its %s attribute is set to None." % (self._meta.object_name, self._meta.pk.attname)

        collector = LogicalDeleteCollector(using=using)
        collector.collect([self])
        collector.delete()

    delete.alters_data = True

    class Meta:
        abstract = True


class AuditModel(models.Model):
    date_created  = models.DateTimeField(editable=False)
    date_modified = models.DateTimeField(editable=False)

    def save(self, *args, **kwargs):
        if not self.date_created:
            self.date_created = datetime.now()
        self.date_modified = datetime.now()
        super(AuditModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True

class Model(LogicalDeleteModel, AuditModel):
    """
    An abstract class with fields to track creation, modification and
    deletion of the model.
    """
    class Meta:
        abstract = True
