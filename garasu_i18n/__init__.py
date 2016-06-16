import logging
from pyramid.httpexceptions import HTTPFound
from pyramid.i18n import TranslationStringFactory, get_localizer
from pyramid.response import Response
from pyramid.view import view_config

from garasu_i18n._version import get_version

__all__ = ('__version__',)
__version__ = get_version()

LOG = logging.getLogger(__name__)

TranslationString = TranslationStringFactory('garasu_i18n')


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
    # LOG.debug(locale_name)
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
    # LOG.debug(locale_name)
    return locale_name


def add_renderer_globals(event):
    request = event.get('request')
    event['_'] = request.translate
    event['localizer'] = request.localizer


def add_localizer(event):
    request = event.request
    localizer = get_localizer(request)

    def auto_translate(*args, **kwargs):
        return localizer.translate(TranslationString(*args, **kwargs))
    request.localizer = localizer
    request.translate = auto_translate


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
    translation_dirs = settings.get('garasu_i18n.translation_dirs')
    config.add_translation_dirs(translation_dirs)
    config.add_subscriber('add_renderer_globals',
                          'pyramid.events.BeforeRender')
    config.add_subscriber('add_localizer',
                          'pyramid.events.NewRequest')

    config.set_locale_negotiator(custom_locale_negotiator)
    config.add_route('locale', '/locale/{language}')

    config.scan(__name__)
