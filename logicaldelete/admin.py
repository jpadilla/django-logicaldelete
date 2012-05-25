from functools import update_wrapper
from django.conf.urls import patterns, url
from django.contrib import admin
from django.contrib.admin import helpers
from django.contrib.admin.util import model_ngettext, unquote
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.template.response import TemplateResponse
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy
from django.utils.translation import ugettext as _


class ModelAdmin(admin.ModelAdmin):
    list_display = ('id', '__unicode__', 'active')
    list_display_filter = ('active',)

    actions = ['undelete_selected']
    undelete_selected_confirmation_template = None
    undelete_confirmation_template = None
    change_form_template = 'admin/change_form_logicaldeleted.html'

    def has_undelete_permission(self, request, obj=None):
        opts = self.opts
        return request.user.has_perm('%s.undelete_%s' %
                                     (opts.app_label, opts.module_name))

    def add_view(self, request, form_url='', extra_context={}):
        extra_context['has_undelete_permission'] = self.has_undelete_permission(request)
        return super(ModelAdmin, self).add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context={}):
        extra_context['has_undelete_permission'] = self.has_undelete_permission(request)
        return super(ModelAdmin, self).change_view(request, object_id, form_url, extra_context)

    def undelete_selected(self, request, queryset):
        """
        Action which undeletes the selected objects.

        This action first displays a confirmation page whichs shows all the
        undeleteable objects, or, if the user has no permission a "permission
        denied" message.

        Next, it undelets all selected objects and redirects back to the
        change list.
        """
        opts = self.model._meta
        app_label = opts.app_label

        # Check that the user has undelete permission for the actual model
        if not self.has_undelete_permission(request):
            raise PermissionDenied

        undeletable_objects = queryset.only_deleted()
        count = undeletable_objects.count()
        if count == 0:
            messages.error(request, _("No objects for undelete."))
            return None

        # The user has already confirmed the undeletion.
        # Do the undeletion and return a None to display the change list view again.
        if request.POST.get('post'):
            for obj in undeletable_objects:
                obj_display = force_unicode(obj)
                self.log_change(request, obj, _("Undeleted %s") % obj_display)
            undeletable_objects.undelete()
            self.message_user(request, _("Successfully undeleted %(count)d %(items)s.") % {
                "count": count, "items": model_ngettext(self.opts, count)
            })
            # Return None to display the change list page again.
            return None

        context = {
            "title": _("Are you sure?"),
            "objects_name": force_unicode(model_ngettext(self.opts, count)),
            "undeletable_objects": [undeletable_objects],
            "queryset": queryset,
            "opts": opts,
            "app_label": app_label,
            'action_checkbox_name': helpers.ACTION_CHECKBOX_NAME,
            }

        # Display the confirmation page
        return TemplateResponse(request, self.undelete_selected_confirmation_template or [
            "admin/%s/%s/undelete_selected_confirmation.html" % (app_label, opts.module_name),
            "admin/%s/undelete_selected_confirmation.html" % app_label,
            "admin/undelete_selected_confirmation.html"
        ], context, current_app=self.admin_site.name)

    undelete_selected.short_description = ugettext_lazy("Undelete selected %(verbose_name_plural)s")

    def undelete_model(self, request, obj):
        obj.undelete()

    def undelete_view(self, request, object_id, extra_context=None):
        "The 'undelete' admin view for this model."
        opts = self.model._meta
        app_label = opts.app_label

        obj = self.get_object(request, unquote(object_id))

        if not self.has_undelete_permission(request, obj):
            raise PermissionDenied

        if obj is None:
            raise Http404(_('%(name)s object with primary key %(key)r does not exist.') % {'name': force_unicode(opts.verbose_name), 'key': escape(object_id)})

        if request.POST: # The user has already confirmed the unsdeletion.
            obj_display = force_unicode(obj)
            self.log_change(request, obj, _("Undeleted %s") % obj_display)
            self.undelete_model(request, obj)

            self.message_user(request, _('The %(name)s "%(obj)s" was undeleted successfully.') % {'name': force_unicode(opts.verbose_name), 'obj': force_unicode(obj_display)})

            if not self.has_change_permission(request, None):
                return HttpResponseRedirect(reverse('admin:index',
                                                    current_app=self.admin_site.name))
            return HttpResponseRedirect(reverse('admin:%s_%s_changelist' %
                                                (opts.app_label, opts.module_name),
                                                current_app=self.admin_site.name))

        object_name = force_unicode(opts.verbose_name)

        context = {
            "title": _("Are you sure?"),
            "object_name": object_name,
            "object": obj,
            "opts": opts,
            "app_label": app_label,
            }
        context.update(extra_context or {})

        return TemplateResponse(request, self.undelete_confirmation_template or [
            "admin/%s/%s/undelete_confirmation.html" % (app_label, opts.object_name.lower()),
            "admin/%s/undelete_confirmation.html" % app_label,
            "admin/undelete_confirmation.html"
        ], context, current_app=self.admin_site.name)

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return update_wrapper(wrapper, view)

        urlpatterns = patterns('',
            url(r'^(.+)/undelete/$', wrap(self.undelete_view),
                name='%s_%s_undelete' % (self.model._meta.app_label,
                self.model._meta.module_name))
        )
        urlpatterns += super(ModelAdmin, self).get_urls()
        return urlpatterns

    def queryset(self, request):
        qs = self.model._default_manager.everything()
        ordering = self.ordering or ()
        if ordering:
            qs = qs.order_by(*ordering)
        return qs
