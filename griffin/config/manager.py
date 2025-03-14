# -*- coding: utf-8 -*-
#

# 
# (see griffin/__init__.py for details)

"""
Configuration manager providing access to user/site/project configuration.
"""

# Standard library imports
import logging
import os
import os.path as osp
import sys
import traceback
from typing import Any, Dict, List, Optional, Set, Tuple
import weakref

# Third-party imports
import keyring
from keyring.errors import NoKeyringError

# Local imports
from griffin.api.utils import PrefixedTuple
from griffin.config.base import (
    _, get_conf_paths, get_conf_path, get_home_dir, reset_config_files)
from griffin.config.main import CONF_VERSION, DEFAULTS, NAME_MAP
from griffin.config.types import ConfigurationKey, ConfigurationObserver
from griffin.config.user import UserConfig, MultiUserConfig, NoDefault, cp
from griffin.plugins.shortcuts.utils import SHORTCUTS_FOR_WIDGETS_DATA
from griffin.utils.programs import check_version


logger = logging.getLogger(__name__)

EXTRA_VALID_SHORTCUT_CONTEXTS = ['_', 'find_replace']


class ConfigurationManager(object):
    """
    Configuration manager to provide access to user/site/project config.
    """

    def __init__(self, parent=None, active_project_callback=None,
                 conf_path=None):
        """
        Configuration manager to provide access to user/site/project config.
        """
        path = conf_path if conf_path else self.get_user_config_path()
        if not osp.isdir(path):
            os.makedirs(path)

        # Site configuration defines the system defaults if a file
        # is found in the site location
        conf_paths = get_conf_paths()
        site_defaults = DEFAULTS
        for conf_path in reversed(conf_paths):
            conf_fpath = os.path.join(conf_path, 'griffin.ini')
            if os.path.isfile(conf_fpath):
                site_config = UserConfig(
                    'griffin',
                    path=conf_path,
                    defaults=site_defaults,
                    load=False,
                    version=CONF_VERSION,
                    backup=False,
                    raw_mode=True,
                    remove_obsolete=False,
                )
                site_defaults = site_config.to_list()

        self._parent = parent
        self._active_project_callback = active_project_callback
        self._user_config = MultiUserConfig(
            NAME_MAP,
            path=path,
            defaults=site_defaults,
            load=True,
            version=CONF_VERSION,
            backup=True,
            raw_mode=True,
            remove_obsolete=False,
        )

        # This is useful to know in order to execute certain operations when
        # bumping CONF_VERSION
        self.old_griffin_version = (
            self._user_config._configs_map['griffin']._old_version)

        # Store plugin configurations when CONF_FILE = True
        self._plugin_configs = {}

        # TODO: To be implemented in following PR
        self._project_configs = {}  # Cache project configurations

        # Object observer map
        # This dict maps from a configuration key (str/tuple) to a set
        # of objects that should be notified on changes to the corresponding
        # subscription key per section. The observer objects must be hashable.
        self._observers: Dict[
            ConfigurationKey, Dict[str, Set[ConfigurationObserver]]
        ] = {}

        # Set of suscription keys per observer object
        # This dict maps from a observer object to the set of configuration
        # keys that the object is subscribed to per section.
        self._observer_map_keys: Dict[
            ConfigurationObserver, Dict[str, Set[ConfigurationKey]]
        ] = weakref.WeakKeyDictionary()

        # List of options with disabled notifications.
        # This holds a list of (section, option) options that won't be notified
        # to observers. It can be used to temporarily disable notifications for
        # some options.
        self._disabled_options: List[Tuple(str, ConfigurationKey)] = []

        # Mapping for shortcuts that need to be notified
        self._shortcuts_to_notify: Dict[(str, str), Optional[str]] = {}

        # Setup
        self.remove_deprecated_config_locations()

    def unregister_plugin(self, plugin_instance):
        conf_section = plugin_instance.CONF_SECTION
        if conf_section in self._plugin_configs:
            self._plugin_configs.pop(conf_section, None)

    def register_plugin(self, plugin_class):
        """Register plugin configuration."""
        conf_section = plugin_class.CONF_SECTION
        if plugin_class.CONF_FILE and conf_section:
            path = self.get_plugin_config_path(conf_section)
            version = plugin_class.CONF_VERSION
            version = version if version else '0.0.0'
            name_map = plugin_class._CONF_NAME_MAP
            name_map = name_map if name_map else {'griffin': []}
            defaults = plugin_class.CONF_DEFAULTS

            if conf_section in self._plugin_configs:
                raise RuntimeError('A plugin with section "{}" already '
                                   'exists!'.format(conf_section))

            plugin_config = MultiUserConfig(
                name_map,
                path=path,
                defaults=defaults,
                load=True,
                version=version,
                backup=True,
                raw_mode=True,
                remove_obsolete=False,
                external_plugin=True
            )

            # Recreate external plugin configs to deal with part two
            # (the shortcut conflicts) of griffin-ide/griffin#11132
            if check_version(self.old_griffin_version, '54.0.0', '<'):
                # Remove all previous .ini files
                try:
                    plugin_config.cleanup()
                except EnvironmentError:
                    pass

                # Recreate config
                plugin_config = MultiUserConfig(
                    name_map,
                    path=path,
                    defaults=defaults,
                    load=True,
                    version=version,
                    backup=True,
                    raw_mode=True,
                    remove_obsolete=False,
                    external_plugin=True
                )

            self._plugin_configs[conf_section] = (plugin_class, plugin_config)

    def remove_deprecated_config_locations(self):
        """Removing old .griffin.ini location."""
        old_location = osp.join(get_home_dir(), '.griffin.ini')
        if osp.isfile(old_location):
            os.remove(old_location)

    def get_active_conf(self, section=None):
        """
        Return the active user or project configuration for plugin.
        """
        # Add a check for shortcuts!
        if section is None:
            config = self._user_config
        elif section in self._plugin_configs:
            _, config = self._plugin_configs[section]
        else:
            # TODO: implement project configuration on the following PR
            config = self._user_config

        return config

    def get_user_config_path(self):
        """Return the user configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'config')
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    def get_plugin_config_path(self, plugin_folder):
        """Return the plugin configuration path."""
        base_path = get_conf_path()
        path = osp.join(base_path, 'plugins')
        if plugin_folder is None:
            raise RuntimeError('Plugin needs to define `CONF_SECTION`!')
        path = osp.join(base_path, 'plugins', plugin_folder)
        if not osp.isdir(path):
            os.makedirs(path)

        return path

    # --- Observer pattern
    # ------------------------------------------------------------------------
    def observe_configuration(self,
                              observer: ConfigurationObserver,
                              section: str,
                              option: Optional[ConfigurationKey] = None):
        """
        Register an `observer` object to listen for changes in the option
        `option` on the configuration `section`.

        Parameters
        ----------
        observer: ConfigurationObserver
            Object that conforms to the `ConfigurationObserver` protocol.
        section: str
            Name of the configuration section that contains the option
            :param:`option`
        option: Optional[ConfigurationKey]
            Name of the option on the configuration section :param:`section`
            that the object is going to suscribe to. If None, the observer
            will observe any changes on any of the options of the configuration
            section.
        """
        section_sets = self._observers.get(section, {})
        option = option if option is not None else '__section'

        option_set = section_sets.get(option, weakref.WeakSet())
        option_set |= {observer}

        section_sets[option] = option_set
        self._observers[section] = section_sets

        observer_section_sets = self._observer_map_keys.get(observer, {})
        section_set = observer_section_sets.get(section, set({}))
        section_set |= {option}

        observer_section_sets[section] = section_set
        self._observer_map_keys[observer] = observer_section_sets

    def unobserve_configuration(self,
                                observer: ConfigurationObserver,
                                section: Optional[str] = None,
                                option: Optional[ConfigurationKey] = None):
        """
        Remove an observer to prevent it to receive further changes
        on the values of the option `option` of the configuration section
        `section`.

        Parameters
        ----------
        observer: ConfigurationObserver
            Object that conforms to the `ConfigurationObserver` protocol.
        section: Optional[str]
            Name of the configuration section that contains the option
            :param:`option`. If None, the observer is unregistered from all
            options for all sections that it has registered to.
        option: Optional[ConfigurationKey]
            Name of the configuration option on the configuration
            :param:`section` that the observer is going to be unsubscribed
            from. If None, the observer is unregistered from all the options of
            the section `section`.
        """
        if observer not in self._observer_map_keys:
            return

        observer_sections = self._observer_map_keys[observer]
        if section is not None:
            section_options = observer_sections[section]
            section_observers = self._observers[section]
            if option is None:
                for option in section_options:
                    option_observers = section_observers[option]
                    option_observers.remove(observer)
                observer_sections.pop(section)
            else:
                option_observers = section_observers[option]
                option_observers.remove(observer)
        else:
            for section in observer_sections:
                section_options = observer_sections[section]
                section_observers = self._observers[section]
                for option in section_options:
                    option_observers = section_observers[option]
                    option_observers.remove(observer)
            self._observer_map_keys.pop(observer)

    def notify_all_observers(self):
        """
        Notify all the observers subscribed to all the sections and options.
        """
        for section in self._observers:
            self.notify_section_all_observers(section)

    def notify_observers(
        self,
        section: str,
        option: ConfigurationKey,
        recursive_notification: bool = True,
        secure: bool = False,
    ):
        """
        Notify observers of a change in the option `option` of configuration
        section `section`.

        Parameters
        ----------
        section: str
            Name of the configuration section whose option did changed.
        option: ConfigurationKey
            Name/Path to the option that did changed.
        recursive_notification: bool
            If True, all objects that observe all changes on the
            configuration section and objects that observe partial tuple paths
            are notified. For example if the option `opt` of section `sec`
            changes, then the observers for section `sec` are notified.
            Likewise, if the option `(a, b, c)` changes, then observers for
            `(a, b, c)`, `(a, b)` and a are notified as well.
        secure: bool
            Whether this is a secure option or not.
        """
        if recursive_notification:
            # Notify to section listeners
            self._notify_section(section)

        if isinstance(option, tuple) and recursive_notification:
            # Notify to partial tuple observers
            # e.g., If the option is (a, b, c), observers subscribed to
            # (a, b, c), (a, b) and a are notified
            option_list = list(option)
            while option_list != []:
                tuple_option = tuple(option_list)
                if len(option_list) == 1:
                    tuple_option = tuple_option[0]

                value = self.get(section, tuple_option)
                self._notify_option(section, tuple_option, value)
                option_list.pop(-1)
        else:
            if option == '__section':
                self._notify_section(section)
            else:
                if section == "shortcuts":
                    self._notify_shortcut(option)
                else:
                    value = self.get(section, option, secure=secure)
                    self._notify_option(section, option, value)

    def _notify_option(self, section: str, option: ConfigurationKey,
                       value: Any):
        section_observers = self._observers.get(section, {})
        option_observers = section_observers.get(option, set({}))

        if (section, option) in self._disabled_options:
            logger.debug(
                f"Don't send notification to observers of disabled option "
                f"{option} in configuration section {section}"
            )
            return
        elif len(option_observers) > 0:
            logger.debug(
                f"Sending notification to observers of {option} option in "
                f"configuration section {section}"
            )

        for observer in list(option_observers):
            try:
                observer.on_configuration_change(option, section, value)
            except RuntimeError:
                # Prevent errors when Qt Objects are destroyed
                self.unobserve_configuration(observer)

    def _notify_section(self, section: str):
        section_values = dict(self.items(section) or [])
        self._notify_option(section, '__section', section_values)

    def _notify_shortcut(self, option: str):
        # We need this mapping for two reasons:
        # 1. We don't need to notify changes for all shortcuts, only for
        #    widget shortcuts, which are the ones with associated observers
        #    (see GriffinShortcutsMixin.register_shortcut_for_widget).
        # 2. Besides context and name, we need the plugin_name to correctly get
        #    the shortcut value to notify. That's not saved in our config
        #    system, but it is in SHORTCUTS_FOR_WIDGETS_DATA.
        if not self._shortcuts_to_notify:
            # Populate mapping only once
            self._shortcuts_to_notify = {
                (data.context, data.name): data.plugin_name
                for data in SHORTCUTS_FOR_WIDGETS_DATA
            }

        context, name = option.split("/")
        if (context, name) in self._shortcuts_to_notify:
            plugin_name = self._shortcuts_to_notify[(context, name)]
            value = self.get_shortcut(context, name, plugin_name)
            self._notify_option("shortcuts", option, value)

    def notify_section_all_observers(self, section: str):
        """Notify all the observers subscribed to any option of a section."""
        option_observers = self._observers[section]
        section_prefix = PrefixedTuple()
        # Notify section observers
        CONF.notify_observers(section, '__section')
        for option in option_observers:
            if isinstance(option, tuple):
                section_prefix.add_path(option)
            else:
                try:
                    self.notify_observers(section, option)
                except cp.NoOptionError:
                    # Skip notification if the option/section does not exist.
                    # This prevents unexpected errors in the test suite.
                    pass
        # Notify prefixed observers
        for prefix in section_prefix:
            try:
                self.notify_observers(section, prefix)
            except cp.NoOptionError:
                # See above explanation.
                pass

    def disable_notifications(self, section: str, option: ConfigurationKey):
        """Disable notitications for `option` in `section`."""
        logger.debug(
            f"Disable notifications for option {option} option in section "
            f"{section}"
        )
        self._disabled_options.append((section, option))

    def restore_notifications(self, section: str, option: ConfigurationKey):
        """Restore notitications for disabled `option` in `section`."""
        logger.debug(
            f"Restore notifications for option {option} option in section "
            f"{section}"
        )
        try:
            self._disabled_options.remove((section, option))
        except ValueError:
            pass

    # --- Projects
    # ------------------------------------------------------------------------
    def register_config(self, root_path, config):
        """
        Register configuration with `root_path`.

        Useful for registering project configurations as they are opened.
        """
        if self.is_project_root(root_path):
            if root_path not in self._project_configs:
                self._project_configs[root_path] = config
        else:
            # Validate which are valid site config locations
            self._site_config = config

    def get_active_project(self):
        """Return the `root_path` of the current active project."""
        callback = self._active_project_callback
        if self._active_project_callback:
            return callback()

    def is_project_root(self, root_path):
        """Check if `root_path` corresponds to a valid griffin project."""
        return False

    def get_project_config_path(self, project_root):
        """Return the project configuration path."""
        path = osp.join(project_root, '.spyproj', 'config')
        if not osp.isdir(path):
            os.makedirs(path)

    # MultiUserConf/UserConf interface
    # ------------------------------------------------------------------------
    def items(self, section):
        """Return all the items option/values for the given section."""
        config = self.get_active_conf(section)
        return config.items(section)

    def options(self, section):
        """Return all the options for the given section."""
        config = self.get_active_conf(section)
        return config.options(section)

    def get(self, section, option, default=NoDefault, secure=False):
        """
        Get an `option` on a given `section`.

        If section is None, the `option` is requested from default section.
        """
        config = self.get_active_conf(section)
        if isinstance(option, tuple) and len(option) == 1:
            option = option[0]

        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_conf = config.get(
                section=section, option=base_option, default={})
            next_ptr = base_conf
            for opt in intermediate_options:
                next_ptr = next_ptr.get(opt, {})

            value = next_ptr.get(last_option, None)
            if value is None:
                value = default
                if default is NoDefault:
                    raise cp.NoOptionError(option, section)
        else:
            if secure:
                logger.debug(
                    f"Retrieving option {option} with keyring because it "
                    f"was marked as secure."
                )
                value = keyring.get_password(section, option)

                # This happens when `option` was not actually saved by keyring
                if value is None:
                    value = ""
            else:
                value = config.get(
                    section=section, option=option, default=default
                )

        return value

    def set(self, section, option, value, verbose=False, save=True,
            recursive_notification=True, notification=True, secure=False):
        """
        Set an `option` on a given `section`.

        If section is None, the `option` is added to the default section.
        """
        original_option = option
        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_conf = self.get(section, base_option, {})
            conf_ptr = base_conf
            for opt in intermediate_options:
                next_ptr = conf_ptr.get(opt, {})
                conf_ptr[opt] = next_ptr
                conf_ptr = next_ptr

            conf_ptr[last_option] = value
            value = base_conf
            option = base_option

        config = self.get_active_conf(section)

        if secure:
            logger.debug(
                f"Saving option {option} with keyring because it was marked "
                f"as secure."
            )

            # Catch error when there's no keyring backend available.
            # Fixes griffin-ide/griffin#22623
            try:
                keyring.set_password(section, option, value)
            except NoKeyringError:
                # This file must not have top-level Qt imports. This also
                # prevents possible circular imports.
                from qtpy.QtWidgets import QMessageBox
                from griffin_kernels.utils.pythonenv import is_conda_env

                pkg_manager = "conda" if is_conda_env(sys.prefix) else "pip"
                msg = _(
                    "It was not possible to save a configuration setting "
                    "securely. A possible solution is to install the "
                    "<tt>keyrings.alt</tt> package with {}.<br><br>"
                    "<bb>Note</bb>: That package may have security risks or "
                    "other implications. Hence, it's not advised to use it in "
                    "general production or security-sensitive systems."
                ).format(pkg_manager)

                QMessageBox.critical(
                    None,
                    _("Error"),
                    msg,
                    QMessageBox.Ok,
                )
        else:
            config.set(
                section=section,
                option=option,
                value=value,
                verbose=verbose,
                save=save,
            )

        if notification:
            self.notify_observers(
                section, original_option, recursive_notification, secure
            )

    def get_default(self, section, option):
        """
        Get Default value for a given `section` and `option`.

        This is useful for type checking in `get` method.
        """
        config = self.get_active_conf(section)
        if isinstance(option, tuple):
            base_option = option[0]
            intermediate_options = option[1:-1]
            last_option = option[-1]

            base_default = config.get_default(section, base_option)
            conf_ptr = base_default
            for opt in intermediate_options:
                conf_ptr = conf_ptr[opt]

            return conf_ptr[last_option]

        return config.get_default(section, option)

    def remove_section(self, section):
        """Remove `section` and all options within it."""
        config = self.get_active_conf(section)
        config.remove_section(section)

    def remove_option(self, section, option, secure=False):
        """Remove `option` from `section`."""
        config = self.get_active_conf(section)

        if isinstance(option, tuple):
            # The actual option saved in the config
            base_option = option[0]

            # Keys of the nested dicts where the option to remove is contained
            intermediate_options = option[1:-1]

            # Key of the option to remove
            last_option = option[-1]

            # Get config value (which is a dictionary)
            base_conf = self.get(section, base_option)

            # Get reference to the actual dictionary containing the option
            # that needs to be removed
            conf_ptr = base_conf
            for opt in intermediate_options:
                conf_ptr = conf_ptr[opt]

            # Remove option and set updated config values for the actual option
            # while checking that the option to be removed is actually a value
            # available in the config.
            # See griffin-ide/griffin#21161
            if last_option in conf_ptr:
                conf_ptr.pop(last_option)
                self.set(section, base_option,  base_conf)
                self.notify_observers(section, base_option)
        else:
            if secure:
                logger.debug(
                    f"Deleting option {option} with keyring because it was "
                    f"marked as secure."
                )
                try:
                    keyring.delete_password(section, option)
                except Exception:
                    pass
            else:
                config.remove_option(section, option)

    def reset_to_defaults(self, section=None, notification=True):
        """Reset config to Default values."""
        config = self.get_active_conf(section)
        config.reset_to_defaults(section=section)
        if notification:
            if section is not None:
                self.notify_section_all_observers(section)
            else:
                self.notify_all_observers()

    def reset_manager(self):
        for observer in self._observer_map_keys.copy():
            self.unobserve_configuration(observer)
        self._plugin_configs = {}

    # Shortcut configuration management
    # ------------------------------------------------------------------------
    def _get_shortcut_config(self, context, plugin_name=None):
        """
        Return the shortcut configuration for global or plugin configs.

        Context must be either '_' for global or the name of a plugin.
        """
        context = context.lower()
        config = self._user_config

        if plugin_name in self._plugin_configs:
            plugin_class, config = self._plugin_configs[plugin_name]

            # Check if plugin has a separate file
            if not plugin_class.CONF_FILE:
                config = self._user_config

        elif context in self._plugin_configs:
            plugin_class, config = self._plugin_configs[context]

            # Check if plugin has a separate file
            if not plugin_class.CONF_FILE:
                config = self._user_config

        elif context in (self._user_config.sections()
                         + EXTRA_VALID_SHORTCUT_CONTEXTS):
            config = self._user_config
        else:
            raise ValueError(_("Shortcut context must match '_' or the "
                               "plugin `CONF_SECTION`!"))

        return config

    def get_shortcut(self, context, name, plugin_name=None):
        """
        Get keyboard shortcut (key sequence string).

        Context must be either '_' for global or the name of a plugin.
        """
        config = self._get_shortcut_config(context, plugin_name)
        return config.get('shortcuts', context + '/' + name.lower())

    def set_shortcut(self, context, name, keystr, plugin_name=None):
        """
        Set keyboard shortcut (key sequence string).

        Context must be either '_' for global or the name of a plugin.
        """
        config = self._get_shortcut_config(context, plugin_name)
        option = f"{context}/{name}"
        current_shortcut = config.get("shortcuts", option, default="")

        if current_shortcut != keystr:
            config.set('shortcuts', option, keystr)
            self.notify_observers("shortcuts", option)

    def iter_shortcuts(self):
        """Iterate over keyboard shortcuts."""
        for context_name, keystr in self._user_config.items('shortcuts'):
            if context_name == 'enable':
                continue

            if 'additional_configuration' not in context_name:
                context, name = context_name.split('/', 1)
                yield context, name, keystr

        for __, (__, plugin_config) in self._plugin_configs.items():
            items = plugin_config.items('shortcuts')
            if items:
                for context_name, keystr in items:
                    context, name = context_name.split('/', 1)
                    yield context, name, keystr

    def reset_shortcuts(self):
        """Reset keyboard shortcuts to default values."""
        self._user_config.reset_to_defaults(section='shortcuts')
        for __, (__, plugin_config) in self._plugin_configs.items():
            # TODO: check if the section exists?
            plugin_config.reset_to_defaults(section='shortcuts')

        # This necessary to notify the observers of widget shortcuts
        self.notify_section_all_observers(section="shortcuts")


try:
    CONF = ConfigurationManager()
except Exception:
    from qtpy.QtWidgets import QApplication, QMessageBox

    # Print traceback to show error in the terminal in case it's needed
    print(traceback.format_exc())  # griffin: test-skip

    # Check if there's an app already running
    app = QApplication.instance()

    # Create app, if there's none, in order to display the message below.
    # NOTE: Don't use the functions we have to create a QApplication here
    # because they could import CONF at some point, which would make this
    # fallback fail.
    # See issue griffin-ide/griffin#17889
    if app is None:
        app = QApplication(['Griffin', '--no-sandbox'])
        app.setApplicationName('Griffin')

    reset_reply = QMessageBox.critical(
        None, 'Griffin',
        _("There was an error while loading Griffin configuration options. "
          "You need to reset them for Griffin to be able to launch.\n\n"
          "Do you want to proceed?"),
        QMessageBox.Yes, QMessageBox.No)
    if reset_reply == QMessageBox.Yes:
        reset_config_files()
        QMessageBox.information(
            None, 'Griffin',
            _("Griffin configuration files resetted!"))
    os._exit(0)
