# -*- coding: utf-8; -*-
from django.db.models import query
from logicaldelete.deletion import LogicalDeleteCollector


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
