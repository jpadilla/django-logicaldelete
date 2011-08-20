from datetime import datetime
from django.db import models


class LogicalDeletedManager(models.Manager):
    def get_query_set(self):
        if self.model:
            return super(LogicalDeletedManager, self).get_query_set().filter(date_removed__isnull=True)

    def everything(self):
        if self.model:
            return super(LogicalDeletedManager, self).get_query_set()

    def only_deleted(self):
        if self.model:
            return super(LogicalDeletedManager, self).get_query_set().filter(date_removed__isnull=False)

    def get(self, *args, **kwargs):
        ''' if a specific record was requested, return it even if it's deleted '''
        return self.everything().get(*args, **kwargs)

    def filter(self, *args, **kwargs):
        ''' if pk was specified as a kwarg, return even if it's deleted '''
        if 'pk' in kwargs:
            return self.everything().filter(*args, **kwargs)
        return self.get_query_set().filter(*args, **kwargs)


class LogicalDeleteModel(models.Model):
    date_removed  = models.DateTimeField(null=True, blank=True)

    objects    = LogicalDeletedManager()
    deleted    = LogicalDeletedManager().only_deleted()
    everything = LogicalDeletedManager().everything()
    
    def active(self):
        return self.date_removed == None
    active.boolean = True

    def delete(self):
        self.date_removed = datetime.now()
        self.save()

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
