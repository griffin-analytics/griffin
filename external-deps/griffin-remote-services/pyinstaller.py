from pathlib import Path

import PyInstaller.__main__
import jupyterhub


GRIFFIN_REMOTE_SERVER = Path(__file__).parent.absolute() / "griffin_remote_server"
path_to_main = str(GRIFFIN_REMOTE_SERVER / "__main__.py")
# path_to_run_jupyterhub = str(GRIFFIN_REMOTE_SERVER / "run_jupyterhub.py")
# path_to_run_service = str(GRIFFIN_REMOTE_SERVER / "run_service.py")
path_to_jupyterhub_config = str(GRIFFIN_REMOTE_SERVER / "jupyterhub_config.py")

JUPYTERHUB_PATH = Path(jupyterhub.__file__).parent.absolute()
path_to_alembic = str(JUPYTERHUB_PATH / "alembic")
path_to_alembic_ini = str(JUPYTERHUB_PATH / "alembic.ini")

def install():
    PyInstaller.__main__.run([
        path_to_main,
        # '--add-data', f'{path_to_run_jupyterhub}:.',
        # '--add-data', f'{path_to_run_service}:griffin_remote_server',
        '--add-data', f'{path_to_jupyterhub_config}:griffin_remote_server',
        '--add-data', f'{path_to_alembic}:jupyterhub/alembic',
        '--add-data', f'{path_to_alembic_ini}:jupyterhub',
        '--name', 'griffin-remote-server',
        '--onefile',
        '--noconsole',
    ])
