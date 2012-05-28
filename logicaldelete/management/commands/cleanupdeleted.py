from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.db import DEFAULT_DB_ALIAS, transaction
from logicaldelete.base import logicaldelete_models_registry

from optparse import make_option

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--database', action='store', dest='database',
                    default=DEFAULT_DB_ALIAS, help='Nominates a specific database to cleanup '
                                                   'deleted from. Defaults to the "default" database.'),
        make_option('-e', '--exclude', dest='exclude', action='append', default=[],
                    help='An appname or appname.ModelName to exclude (use multiple --exclude to exclude multiple apps/models).'),
        make_option('-a', '--all', action='store_true', dest='delete_all', default=False,
                    help="Cleanup all logical deleted items."),
        make_option('--noinput', action='store_false', dest='interactive', default=True,
                    help='Tells Django to NOT prompt the user for input of any kind.'),

        )
    help = ("Remove already marked as deleted items (and all related) from database.")
    args = '[appname appname.ModelName ...]'

    def handle(self, *app_labels, **options):
        from django.db.models import get_app, get_apps, get_model, get_models

        using = options.get('database')
        excludes = options.get('exclude')
        show_traceback = options.get('traceback')
        delete_all = options.get('delete_all')
        verbosity = options.get('verbosity')

        excluded_apps = set()
        excluded_models = set()
        for exclude in excludes:
            if '.' in exclude:
                app_label, model_name = exclude.split('.', 1)
                model_obj = get_model(app_label, model_name)
                if not model_obj:
                    raise CommandError('Unknown model in excludes: %s' % exclude)
                excluded_models.add(model_obj)
            else:
                try:
                    app_obj = get_app(exclude)
                    excluded_apps.add(app_obj)
                except ImproperlyConfigured:
                    raise CommandError('Unknown app in excludes: %s' % exclude)

        model_list = []
        if len(app_labels) == 0:
            if delete_all:
                for app in get_apps():
                    if app not in excluded_apps:
                        model_list.extend([model for model in get_models(app)])
            else:
                raise CommandError("Enter at least one appname or appname.ModelName.")
        else:
            for label in app_labels:
                try:
                    app_label, model_label = label.split('.')
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    if app in excluded_apps:
                        continue
                    model = get_model(app_label, model_label)
                    if model is None:
                        raise CommandError("Unknown model: %s.%s" % (app_label, model_label))

                    if model not in model_list:
                        model_list.append(model)
                except ValueError:
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError("Unknown application: %s" % app_label)
                    if app in excluded_apps:
                        continue
                    model_list.extend([model for model in get_models(app)])

        if options.get('interactive'):
            confirm = raw_input("""
You have requested a remove marked as deleted items.
This will IRREVERSIBLY DELETE all kind of this data (and related records also) in selected apps (models).
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
        else:
            confirm = 'yes'

        if confirm != 'yes':
            return

        for model in model_list:
            if model in excluded_models or \
               model not in logicaldelete_models_registry:
                continue

            try:
                if verbosity=='1':
                    self.stdout.write("Handling model %s.%s\n" %
                                      (model._meta.app_label, model._meta.object_name))
                model._default_manager.only_deleted().using(using).remove()
            except Exception, e:
                if show_traceback:
                    raise
                raise CommandError("Unable to cleanup database: %s" % e)
