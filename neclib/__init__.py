"""Pure Python tools for NECST."""


# Logger configuration
import logging as _logging  # noqa: E402

rootLogger = _logging.getLogger()
# Set minimum log level; not just for stream handler but for any handler attached.
# Stream handler will selectively handle logs of INFO or higher levels, but DEBUG level
# ones are not something you can completely ignore (may be recorded into log file)
rootLogger.setLevel(_logging.DEBUG)
del rootLogger


# Project version
from importlib.metadata import version  # noqa: E402

__version__ = version("neclib")
del version


# Astropy IERS policy for observatory operation
def _env_flag(name, default=False):
    """Return a boolean from common environment-variable spellings."""

    import os

    value = os.environ.get(name)
    if value is None:
        return bool(default)
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_astropy_iers_policy():
    """Configure Astropy IERS behaviour for NECST operation.

    The default is online-friendly: if the network is available, Astropy may
    refresh stale IERS/leap-second data.  If the network is unavailable, NECST
    should continue with local/cache/bundled data and warnings rather than fail
    during node startup.

    For deliberately offline operation, set
    ``NECLIB_ASTROPY_IERS_AUTO_DOWNLOAD=0`` to use only the locally installed
    astropy-iers-data/bundled tables.
    """

    from astropy.utils import iers

    iers.conf.auto_download = _env_flag(
        "NECLIB_ASTROPY_IERS_AUTO_DOWNLOAD", default=True
    )

    # If the available IERS data are stale or extrapolated, continue with
    # warnings rather than aborting node startup.  Accuracy-sensitive code will
    # still emit Astropy warnings at the actual UT1/coordinate conversion site.
    iers.conf.iers_degraded_accuracy = "warn"


_configure_astropy_iers_policy()

# Subpackages
# `devices` isn't included, since they can be OS-dependent hence verbose warnings
from . import controllers  # noqa: F401, E402
from . import coordinates  # noqa: F401, E402
from . import core  # noqa: F401, E402
from . import recorders  # noqa: F401, E402
from . import safety  # noqa: F401, E402
from . import simulators  # noqa: F401, E402
from . import utils  # noqa: F401, E402

# Aliases
from .core import config, configure, get_logger  # noqa: F401, E402
from .core.data_type import *  # noqa: F401, E402, F403
from .core.exceptions import *  # noqa: F401, E402, F403


# Perform time-consuming Astropy IERS/leap-second preparation.
#
# The original implementation started this task at the beginning of
# ``import neclib`` and waited for completion at the end.  That overlapped the
# IERS/leap-second cache preparation with neclib imports, but it also allowed a
# background ``astropy.time`` import to race with main-thread ``astropy.units``
# or ``astropy.coordinates`` imports.  In Python 3.12 this can intermittently
# leave Astropy in a partially initialised state during ROS node startup.
#
# Start the preload only after all neclib subpackages and aliases have been
# imported.  At that point the Astropy import graph used by neclib has already
# been initialised in the main thread, so the previous import-time race is
# removed.  The network/cache work itself is intentionally not awaited: a dead
# or absent network must not delay basic node startup.  Long-running nodes will
# finish this warm-up in the background; short commands simply fall back to
# Astropy's normal on-demand behaviour if they need UT1 immediately.
def _start_astropy_iers_preload():
    """Start best-effort Astropy IERS/leap-second preload in a daemon thread.

    Importing ``astropy.time.Time`` is a hard dependency check and is done
    synchronously.  The potentially slow ``Time.now().ut1`` part runs in the
    background, may use the network when Astropy permits it, and reports
    warnings/failures without preventing NECST commands from starting.
    """

    import importlib
    import threading
    import warnings

    # Complete the Astropy import graph that neclib/necst commonly uses before
    # the background thread starts.  This keeps the thread away from Astropy
    # first-import paths while not touching any remote IERS data yet.
    for module_name in (
        "astropy.units",
        "astropy.constants",
        "astropy.coordinates",
        "astropy.time",
        "astropy.utils.iers",
    ):
        importlib.import_module(module_name)

    from astropy.time import Time
    from astropy.utils import iers

    logger = _logging.getLogger(__name__)
    auto_download = bool(iers.conf.auto_download)

    def _worker():
        download_notice_urls = set()

        def _format_download_url(url):
            try:
                if hasattr(url, "full_url"):
                    return str(url.full_url)
                return str(url)
            except Exception:
                return "<unknown-url>"

        def _notice_download(url):
            text = _format_download_url(url)
            if text in download_notice_urls:
                return
            download_notice_urls.add(text)
            logger.warning(
                "Astropy IERS/leap-second preload is downloading or "
                "refreshing a remote data file: %s",
                text,
            )

        try:
            if auto_download:
                logger.info(
                    "Astropy IERS/leap-second background preload started; "
                    "remote download warnings will be emitted only if Astropy "
                    "actually opens a remote connection. NECST startup will "
                    "not wait for this task."
                )
            else:
                logger.info(
                    "Astropy IERS/leap-second background preload started with "
                    "auto_download disabled; local/cache/bundled tables only. "
                    "NECST startup will not wait for this task."
                )

            # Astropy's IERS/leap-second refresh ultimately opens remote URLs
            # through astropy.utils.data and/or urllib.  Patch only within this
            # background preload so normal NECST code is not changed.  A warning
            # is emitted when a real remote-open path is reached, not merely when
            # Time.now().ut1 starts or when a cached table is used.
            restore_actions = []
            if auto_download:
                import urllib.request as _urllib_request
                import astropy.utils.data as _astropy_data

                original_urlopen = _urllib_request.urlopen

                def urlopen_with_notice(url, *args, **kwargs):
                    _notice_download(url)
                    return original_urlopen(url, *args, **kwargs)

                _urllib_request.urlopen = urlopen_with_notice
                restore_actions.append(
                    lambda: setattr(_urllib_request, "urlopen", original_urlopen)
                )

                if getattr(_astropy_data, "urlopen", None) is original_urlopen:
                    _astropy_data.urlopen = urlopen_with_notice
                    restore_actions.append(
                        lambda: setattr(_astropy_data, "urlopen", original_urlopen)
                    )

                original_download_from_source = getattr(
                    _astropy_data, "_download_file_from_source", None
                )
                if callable(original_download_from_source):

                    def download_from_source_with_notice(source_url, *args, **kwargs):
                        _notice_download(source_url)
                        return original_download_from_source(
                            source_url, *args, **kwargs
                        )

                    _astropy_data._download_file_from_source = (
                        download_from_source_with_notice
                    )
                    restore_actions.append(
                        lambda: setattr(
                            _astropy_data,
                            "_download_file_from_source",
                            original_download_from_source,
                        )
                    )

            try:
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always")
                    Time.now().ut1
            finally:
                for restore in reversed(restore_actions):
                    restore()

            for warning in caught:
                logger.warning(
                    "Astropy IERS/leap-second preload warning: %s: %s",
                    warning.category.__name__,
                    warning.message,
                )
            if download_notice_urls:
                logger.info(
                    "Astropy IERS/leap-second background preload finished "
                    "after remote data access."
                )
            else:
                logger.info(
                    "Astropy IERS/leap-second background preload finished "
                    "without remote data access."
                )
        except Exception:
            # The preload is only a best-effort warm-up.  Keep NECST commands
            # importable in offline observing environments; the actual Time/UT1
            # or coordinate operation will warn/fail where it is required if the
            # local data are too degraded for that operation.
            logger.warning(
                "Astropy IERS/leap-second preload failed in background; "
                "NECST will continue, but UT1/coordinate conversions may warn "
                "or fail when first used.",
                exc_info=True,
            )

    thread = threading.Thread(
        target=_worker,
        name="neclib-astropy-iers-preload",
        daemon=True,
    )
    thread.start()
    return thread


_astropy_iers_preload_thread = _start_astropy_iers_preload()


del _start_astropy_iers_preload, _configure_astropy_iers_policy, _env_flag, _logging
