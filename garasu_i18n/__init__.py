import logging
from pkg_resources import resource_filename
from pyramid.httpexceptions import HTTPFound
from pyramid.i18n import TranslationStringFactory, get_localizer, make_localizer
from pyramid.response import Response
from pyramid.view import view_config
from pyramid.threadlocal import get_current_registry
from pyramid.threadlocal import get_current_request
from pyramid.interfaces import ITranslationDirectories
from pyramid.settings import asbool

try:
    import deform
except ImportError:
    raise ImportError


from garasu_i18n._version import get_version

__all__ = ('__version__',)
__version__ = get_version()

LOG = logging.getLogger(__name__)

tsf = TranslationStringFactory('garasu_i18n')

DEFAULT_LOCALE_NAME = 'en'


def custom_locale_negotiator(request):
    """ The :term:`custom locale negotiator`. Returns a locale name.
    - First, the negotiator looks for the ``_LOCALE_`` attribute of
      the request object (possibly set by a view or a listener for an
      :term:`event`).
    - Then it looks for the ``request.params['_LOCALE_']`` value.
    - Then it looks for the ``request.cookies['_LOCALE_']`` value.
    - Then it looks for the ``Accept-Language`` header value,
      which is set by the user in his/her browser configuration.
    - Finally, if the locale could not be determined via any of
      the previous checks, the negotiator returns the
      :term:`default locale name`.
    """
    settings = request.registry.settings
    locales = settings.get('garasu_i18n.locales', ('en', 'es', 'it', 'id'))
    name = '_LOCALE_'
    locale_name = getattr(request, name, None)
    LOG.debug(locale_name)
    if locale_name is None:
        locale_name = request.params.get(name)
        if locale_name is None:
            locale_name = request.cookies.get(name)
            if locale_name is None:
                locale_name = request.accept_language.best_match(
                    locales, settings.default_locale_name)
                if not request.accept_language:
                    # If browser has no language configuration
                    # the default locale name is returned.
                    locale_name = request.registry.settings.default_locale_name
    LOG.debug(locale_name)
    return locale_name


def add_renderer_globals(event):
    request = event.get('request') or get_current_request()
    event['_'] = request.translate
    event['localizer'] = request.localizer


def add_localizer(event):
    request = event.request
    localizer = get_localizer(request)

    def auto_translate(*args, **kwargs):
        return localizer.translate(tsf(*args, **kwargs))
    request.localizer = localizer
    request.translate = auto_translate


def _get_localizer_for_locale_name(locale_name):
    registry = get_current_registry()
    tdirs = registry.queryUtility(ITranslationDirectories, default=[])
    return make_localizer(locale_name, tdirs)


def translate(*args, **kwargs):
    request = get_current_request()
    if request is None:
        localizer = _get_localizer_for_locale_name(DEFAULT_LOCALE_NAME)
    else:
        localizer = request.localizer
    return localizer.translate(tsf(*args, **kwargs))


@view_config(route_name='locale')
def set_locale_cookie(request):
    if request.matchdict.get('language'):
        language = request.matchdict.get('language', 'en')
        response = Response()
        response.set_cookie('_LOCALE_',
                            value=language,
                            max_age=31536000)  # max_age = year
    location = request.route_url('home')
    return HTTPFound(location=location,
                     headers=response.headers)


def includeme(config):
    """
    Initialize the model for a Pyramid library.

    Activate this setup using ``config.include('garasu_i18n')``.

    """
    settings = config.get_settings()

    config.add_subscriber('.add_renderer_globals',
                          'pyramid.events.BeforeRender')
    config.add_subscriber('.add_localizer',
                          'pyramid.events.NewRequest')

    config.set_locale_negotiator(custom_locale_negotiator)

    # combine deform
    if asbool(settings.get('garasu_i18n.deform', False)):
        deform_template_dir = resource_filename('deform', 'templates/')

        zpt_renderer = deform.ZPTRendererFactory(
            [deform_template_dir], translator=translate)

        deform.Form.set_default_renderer(zpt_renderer)

        config.add_translation_dirs('deform:locale/')
        config.add_translation_dirs('colander:locale/')

    config.add_route('locale', '/locale/{language}')

    translation_dirs = settings.get('garasu_i18n.translation_dirs')
    config.add_translation_dirs(translation_dirs)

    config.scan(__name__)
