from griffin_remote_services.app import GriffinRemoteServices


__version__ = '1.0.0'


def _jupyter_server_extension_points():
    """
    Returns a list of dictionaries with metadata describing
    where to find the `_load_jupyter_server_extension` function.
    """
    return [{"module": "griffin_remote_services.app", "app": GriffinRemoteServices}]
