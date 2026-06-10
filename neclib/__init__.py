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
# IMPORTANT:
# This must not run in a Python thread inside the importing NECST process.
# Antenna/device nodes may continue importing necst/neclib modules after
# ``import neclib`` has returned, and a background in-process Astropy import can
# still race with those later imports.  That race intermittently produced
# ``ImportError: cannot import name 'Unit' from partially initialized module
# 'astropy.units.core'`` during ROS node startup.
#
# To keep node startup robust while still allowing online IERS/leap-second cache
# refresh, the optional warm-up is now launched in a separate Python process.
# The child process owns all Astropy imports used for the warm-up, so it cannot
# corrupt the parent process' import state.  The parent does not wait for it.
def _start_astropy_iers_preload():
    """Start best-effort Astropy IERS/leap-second preload out-of-process.

    The parent process only starts a detached helper process and never imports
    ``astropy.time`` in a background thread.  This preserves the original
    operational goal--do not block node startup on IERS network/cache work--but
    removes the import-time race seen in Python 3.12.

    Set ``NECLIB_ASTROPY_IERS_PRELOAD=0`` to disable this helper completely.
    """

    import os
    from pathlib import Path
    import subprocess
    import sys
    import time

    logger = _logging.getLogger(__name__)

    if not _env_flag("NECLIB_ASTROPY_IERS_PRELOAD", default=True):
        logger.info("Astropy IERS/leap-second preload helper is disabled.")
        return None

    state_dir = Path(
        os.environ.get("NECLIB_ASTROPY_IERS_PRELOAD_DIR", "~/.necst")
    ).expanduser()
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        logger.warning(
            "Could not create Astropy IERS preload state directory: %s",
            state_dir,
            exc_info=True,
        )
        return None

    lock_path = state_dir / "astropy_iers_preload.lock"
    log_path = state_dir / "astropy_iers_preload.log"

    # Avoid spawning one network/cache refresh process per ROS node when many
    # nodes start at the same time.  A stale lock older than 10 minutes is
    # discarded.  This is only an optimisation; failure to create the lock must
    # never prevent a NECST node from starting.
    try:
        if lock_path.exists():
            age_s = time.time() - lock_path.stat().st_mtime
            if age_s < 600:
                logger.debug(
                    "Astropy IERS preload helper already appears to be running: %s",
                    lock_path,
                )
                return None
            lock_path.unlink(missing_ok=True)
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as lock:
            lock.write(f"parent_pid={os.getpid()}\n")
            lock.write(f"created_unix={time.time():.6f}\n")
    except Exception:
        logger.debug(
            "Could not create Astropy IERS preload lock; skipping helper.",
            exc_info=True,
        )
        return None

    child_code = '\nimport logging\nimport os\nfrom pathlib import Path\nimport warnings\n\nlock_path = os.environ.get("NECLIB_ASTROPY_IERS_PRELOAD_LOCK")\nlog_path = os.environ.get("NECLIB_ASTROPY_IERS_PRELOAD_LOG")\n\nlogger = logging.getLogger("neclib.astropy_iers_preload")\nlogger.setLevel(logging.INFO)\nformatter = logging.Formatter("[%(levelname)s] %(asctime)s %(name)s: %(message)s")\nstream = logging.StreamHandler()\nstream.setLevel(logging.WARNING)\nstream.setFormatter(formatter)\nlogger.addHandler(stream)\nif log_path:\n    try:\n        file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")\n        file_handler.setLevel(logging.INFO)\n        file_handler.setFormatter(formatter)\n        logger.addHandler(file_handler)\n    except Exception:\n        logger.warning("Could not open preload log file: %s", log_path, exc_info=True)\n\n\ndef _env_flag(name, default=False):\n    value = os.environ.get(name)\n    if value is None:\n        return bool(default)\n    return value.strip().lower() in {"1", "true", "yes", "on"}\n\n\ndef _format_download_url(url):\n    try:\n        if hasattr(url, "full_url"):\n            return str(url.full_url)\n        return str(url)\n    except Exception:\n        return "<unknown-url>"\n\n\ndef main():\n    auto_download = _env_flag("NECLIB_ASTROPY_IERS_AUTO_DOWNLOAD", default=True)\n\n    from astropy.utils import iers\n\n    iers.conf.auto_download = auto_download\n    iers.conf.iers_degraded_accuracy = "warn"\n\n    download_notice_urls = set()\n\n    def _notice_download(url):\n        text = _format_download_url(url)\n        if text in download_notice_urls:\n            return\n        download_notice_urls.add(text)\n        logger.warning(\n            "Astropy IERS/leap-second preload is downloading or refreshing "\n            "a remote data file: %s",\n            text,\n        )\n\n    restore_actions = []\n    if auto_download:\n        import urllib.request as _urllib_request\n        import astropy.utils.data as _astropy_data\n\n        original_urlopen = _urllib_request.urlopen\n\n        def urlopen_with_notice(url, *args, **kwargs):\n            _notice_download(url)\n            return original_urlopen(url, *args, **kwargs)\n\n        _urllib_request.urlopen = urlopen_with_notice\n        restore_actions.append(lambda: setattr(_urllib_request, "urlopen", original_urlopen))\n\n        if getattr(_astropy_data, "urlopen", None) is original_urlopen:\n            _astropy_data.urlopen = urlopen_with_notice\n            restore_actions.append(lambda: setattr(_astropy_data, "urlopen", original_urlopen))\n\n        original_download_from_source = getattr(_astropy_data, "_download_file_from_source", None)\n        if callable(original_download_from_source):\n\n            def download_from_source_with_notice(source_url, *args, **kwargs):\n                _notice_download(source_url)\n                return original_download_from_source(source_url, *args, **kwargs)\n\n            _astropy_data._download_file_from_source = download_from_source_with_notice\n            restore_actions.append(\n                lambda: setattr(\n                    _astropy_data,\n                    "_download_file_from_source",\n                    original_download_from_source,\n                )\n            )\n\n    try:\n        from astropy.time import Time\n\n        if auto_download:\n            logger.info(\n                "Astropy IERS/leap-second preload helper started; remote "\n                "download warnings are emitted only if a remote connection is opened."\n            )\n        else:\n            logger.info(\n                "Astropy IERS/leap-second preload helper started with "\n                "auto_download disabled; local/cache/bundled tables only."\n            )\n        with warnings.catch_warnings(record=True) as caught:\n            warnings.simplefilter("always")\n            Time.now().ut1\n        for warning in caught:\n            logger.warning(\n                "Astropy IERS/leap-second preload warning: %s: %s",\n                warning.category.__name__,\n                warning.message,\n            )\n        if download_notice_urls:\n            logger.info("Astropy IERS/leap-second preload helper finished after remote data access.")\n        else:\n            logger.info("Astropy IERS/leap-second preload helper finished without remote data access.")\n    finally:\n        for restore in reversed(restore_actions):\n            try:\n                restore()\n            except Exception:\n                logger.debug("Failed to restore patched downloader", exc_info=True)\n\n\ntry:\n    main()\nexcept Exception:\n    logger.warning(\n        "Astropy IERS/leap-second preload helper failed; NECST parent process "\n        "continues and Astropy will use normal on-demand behaviour.",\n        exc_info=True,\n    )\nfinally:\n    if lock_path:\n        try:\n            Path(lock_path).unlink(missing_ok=True)\n        except Exception:\n            pass\n'

    env = os.environ.copy()
    env["NECLIB_ASTROPY_IERS_PRELOAD_LOCK"] = str(lock_path)
    env["NECLIB_ASTROPY_IERS_PRELOAD_LOG"] = str(log_path)

    try:
        proc = subprocess.Popen(
            [sys.executable, "-c", child_code],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=None,
            stderr=None,
            close_fds=True,
            start_new_session=True,
        )
    except Exception:
        lock_path.unlink(missing_ok=True)
        logger.warning(
            "Failed to start Astropy IERS/leap-second preload helper process.",
            exc_info=True,
        )
        return None

    logger.info(
        "Started Astropy IERS/leap-second preload helper process pid=%s; "
        "log=%s. NECST startup will not wait for it.",
        proc.pid,
        log_path,
    )
    return proc


_astropy_iers_preload_process = _start_astropy_iers_preload()


del _start_astropy_iers_preload, _configure_astropy_iers_policy, _env_flag, _logging
