import string
import platformdirs

APP_DIRS = platformdirs.PlatformDirs(
    appname="theticketbot",
    appauthor="thegamecracks",
    opinion=True,
)


def expand_app_dirs(path: str, *, strict: bool = False) -> str:
    template = string.Template(path)
    paths = {
        "USER_CONFIG_DIR": APP_DIRS.user_config_dir,
        "USER_DATA_DIR": APP_DIRS.user_data_dir,
        "USER_LOG_DIR": APP_DIRS.user_log_dir,
        "USER_RUNTIME_DIR": APP_DIRS.user_runtime_dir,
        "USER_STATE_DIR": APP_DIRS.user_state_dir,
    }

    if strict:
        return template.substitute(paths)

    return template.safe_substitute(paths)
