from datetime import datetime
from django.db import models, router
from django.db.models import query
from deletion import LogicalDeleteCollector
from base import LogicalDeleteModelBase


class LogicalDeleteQuerySet(query.QuerySet):

    def everything(self):
        qs = super(LogicalDeleteQuerySet, self).all()
        qs.__class__ = LogicalDeleteQuerySet
        return qs

    def delete(self):
        """
        Mark as deleted the records in the current QuerySet.
        """
        assert self.query.can_filter(),\
        "Cannot use 'limit' or 'offset' with delete."

        del_query = self._clone()

        # The delete is actually 2 queries - one to find related objects,
        # and one to delete. Make sure that the discovery of related
        # objects is performed on the same database as the deletion.
        del_query._for_write = True

        # Disable non-supported fields.
        del_query.query.select_for_update = False
        del_query.query.select_related = False
        del_query.query.clear_ordering()

        collector = LogicalDeleteCollector(using=del_query.db)
        collector.collect(del_query)
        collector.delete()

        # Clear the result cache, in case this QuerySet gets reused.
        self._result_cache = None

    delete.alters_data = True

    def remove(self):
        """
        Deletes the records in the current QuerySet.
        """
        query.QuerySet.delete(self)

    remove.alters_data = True

    def only_deleted(self):
        return self.filter(date_removed__isnull=False)

    def undelete(self, using='default', *args, **kwargs):
        self.update(date_removed=None)

    undelete.alters_data = True


class LogicalDeletedManager(models.Manager):
    use_for_related_fields = True

    def get_query_set(self):
        qs = super(LogicalDeletedManager, self).get_query_set().filter(date_removed__isnull=True)
        qs.__class__ = LogicalDeleteQuerySet
        return qs

    def everything(self):
        qs = super(LogicalDeletedManager, self).get_query_set()
        qs.__class__ = LogicalDeleteQuerySet
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

    def undelete(self):
        self.__class__.objects.filter(pk=self.pk).undelete()

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
