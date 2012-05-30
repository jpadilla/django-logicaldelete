# -*- coding: utf-8; -*-
from django.db import models
from logicaldelete.querysets import LogicalDeleteQuerySet


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
