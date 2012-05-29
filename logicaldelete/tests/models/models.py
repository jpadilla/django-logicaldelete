from django.db import models
from logicaldelete.models import Model


class Related2Model(Model):
    text = models.TextField("text")
    related = models.ForeignKey("RelatedModel", null=True, blank=True)
    related2 = models.ForeignKey("TestModel", null=True, blank=True)


class RelatedModel(models.Model):
    text = models.TextField("text")
    related = models.ForeignKey("TestModel", null=True, blank=True)


class TestModel(Model):
    text = models.TextField("text")
    related = models.ForeignKey("RelatedModel", null=True, blank=True)

    class LogicalDeleteMeta:
        delete_related = True
        safe_deletion = False


class RelatedMany(models.Model):
    text = models.TextField("text")
    related = models.ManyToManyField("TestModel")
