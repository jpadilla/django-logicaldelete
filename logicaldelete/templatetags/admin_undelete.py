# -*- coding: utf-8; -*-
from django.contrib.admin.templatetags.admin_modify import submit_row
from django import template

register = template.Library()

@register.inclusion_tag('admin/submit_line_undelete.html', takes_context=True)
def submit_row_undelete(context):
    result = submit_row(context)
    change = context['change']
    active = context['original'].active() if change else True
    is_popup = context['is_popup']

    result.update({
        'show_delete_link': (active and result['show_delete_link']),
        'show_undelete_link': (not is_popup and context['has_undelete_permission']
                             and change and not active),
    })
    return result
