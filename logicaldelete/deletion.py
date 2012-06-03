# -*- coding: utf-8; -*-
from datetime import datetime
from operator import attrgetter
from django.db.models.deletion import Collector, force_managed, sql, signals
from django.db.models.deletion import ProtectedError
from base import LogicalDeleteOptions


class LogicalDeleteCollector(Collector):

    def __init__(self, *args, **kwargs):
        super(LogicalDeleteCollector, self).__init__(*args, **kwargs)
        self.edges = {}  # {from_instance: [to_instances]}
        self.protected = set()
        # key - instance, val: True - logical delete (not delete for plain
        # models), False - delete ordinary
        self.objs_for_delete = {}

    def add_edge(self, source, target):
        self.edges.setdefault(source, []).append(target)

    def collect(self, objs, source_attr=None, **kwargs):
        for obj in objs:
            if source_attr:
                self.add_edge(getattr(obj, source_attr), obj)
            else:
                self.add_edge(None, obj)
        try:
            return super(LogicalDeleteCollector, self).\
            collect(objs, source_attr=source_attr, **kwargs)
        except ProtectedError, e:
            self.protected.update(e.protected_objects)

    def _determine_object_delete_method(self, obj, seen,
                safe_deletion=LogicalDeleteOptions.safe_deletion,
                delete_related=LogicalDeleteOptions.delete_related,
                was_plain_object=False):
        if obj in seen:
            return []
        seen.add(obj)
        model = obj.__class__
        child_safe_deletion = safe_deletion
        if hasattr(model, '_logicaldelete_meta'):
            delete_related = model._logicaldelete_meta.delete_related
            child_safe_deletion = model._logicaldelete_meta.safe_deletion
        else:
            was_plain_object = True

        if delete_related:
            for child in self.edges.get(obj, ()):
                self._determine_object_delete_method(child, seen,
                        child_safe_deletion, delete_related, was_plain_object)

        if hasattr(model, '_logicaldelete_meta') and not was_plain_object:
            self.objs_for_delete[obj] = True
        else:
            self.objs_for_delete[obj] = safe_deletion

    def determine_object_delete_method(self):
        """
        Determine which delete method will be apply for object
        """
        seen = set()
        for root in self.edges.get(None, ()):
            self._determine_object_delete_method(root, seen)

    @force_managed
    def delete(self):
        # sort instance collections
        for model, instances in self.data.items():
            self.data[model] = sorted(instances, key=attrgetter("pk"))

        # if possible, bring the models in an order suitable for databases that
        # don't support transactions or cannot defer constraint checks until
        # the end of a transaction.
        self.sort()
        self.determine_object_delete_method()

        # send pre_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created and obj in self.objs_for_delete:
                signals.pre_delete.send(
                    sender=model, instance=obj, using=self.using
                )

        # reverse instance collections
        for instances in self.data.itervalues():
            instances.reverse()

        # delete batches
        for model, batches in self.batches.iteritems():
            query = sql.DeleteQuery(model)
            for field, instances in batches.iteritems():
                pk_list = []
                for obj in instances:
                    if not obj in self.objs_for_delete:
                        continue
                    if not self.objs_for_delete[obj]:
                        pk_list.append(obj.pk)
                    elif hasattr(obj, '_logicaldelete_meta') and\
                        obj._logicaldelete_meta.delete_batches:
                        pk_list.append(obj.pk)
                query.delete_batch(pk_list, self.using, field)

        date_removed = datetime.now()
        # delete instances, mark as deleted for logicaldelete
        for model, instances in self.data.iteritems():
            query_logical = sql.UpdateQuery(model)
            query = sql.DeleteQuery(model)
            pk_list_logical, pk_list = [], []
            for obj in instances:
                if not obj in self.objs_for_delete:
                    continue
                if self.objs_for_delete[obj] and hasattr(model, '_logicaldelete_meta'):
                    pk_list_logical.append(obj.pk)
                if not self.objs_for_delete[obj]:
                    pk_list.append(obj.pk)

            if pk_list_logical:
                query_logical.update_batch(pk_list_logical,
                            {'date_removed': date_removed}, self.using)

            if pk_list:
                query.delete_batch(pk_list, self.using)

        # send post_delete signals
        for model, obj in self.instances_with_model():
            if not model._meta.auto_created and obj in self.objs_for_delete:
                signals.post_delete.send(
                    sender=model, instance=obj, using=self.using
                )

        # update collected instances
        for model, instances in self.data.iteritems():
            for instance in instances:
                if not instance in self.objs_for_delete:
                    continue
                if self.objs_for_delete[instance]:
                    setattr(instance, 'date_removed', date_removed)
                else:
                    setattr(instance, model._meta.pk.attname, None)
