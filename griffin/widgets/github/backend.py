# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2016 Colin Duquesnoy (QCrash project)
# Copyright (c) 2018- Griffin Project Contributors
#
# 
# (see LICENSE.txt in this directory for details)
# -----------------------------------------------------------------------------

"""
Backend to open issues automatically on Github.

Adapted from qcrash/backends/base.py and qcrash/backends/github.py of the
`QCrash Project <https://github.com/ColinDuquesnoy/QCrash>`_.
"""

import logging
import os
import webbrowser

try:
    # See: griffin-ide/griffin#10221
    if os.environ.get('SSH_CONNECTION') is None:
        import keyring
except Exception:
    pass

import github
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication, QMessageBox


from griffin.config.manager import CONF
from griffin.config.base import _, running_under_pytest
from griffin.widgets.github.gh_login import DlgGitHubLogin


logger = logging.getLogger(__name__)


class BaseBackend(object):
    """
    Base class for implementing a backend.

    Subclass must define ``button_text``, ``button_tooltip``and ``button_icon``
    and implement ``send_report(title, description)``.

    The report's title and body will be formatted automatically by the
    associated :attr:`formatter`.
    """

    def __init__(self, formatter, button_text, button_tooltip,
                 button_icon=None, need_review=True, parent_widget=None):
        """
        :param formatter: the associated formatter (see :meth:`set_formatter`)
        :param button_text: Text of the associated button in the report dialog
        :param button_icon: Icon of the associated button in the report dialog
        :param button_tooltip: Tooltip of the associated button in the report
            dialog
        :param need_review: True to show the review dialog before submitting.
            Some backends (such as the email backend) do not need a review
            dialog as the user can already review it before sending the final
            report
        """
        self.formatter = formatter
        self.button_text = button_text
        self.button_tooltip = button_tooltip
        self.button_icon = button_icon
        self.need_review = need_review
        self.parent_widget = parent_widget

    def set_formatter(self, formatter):
        """
        Sets the formatter associated with the backend.

        The formatter will automatically get called to format the report title
        and body before ``send_report`` is being called.
        """
        self.formatter = formatter

    def send_report(self, title, body, application_log=None):
        """
        Sends the actual bug report.

        :param title: title of the report, already formatted.
        :param body: body of the reporit, already formtatted.
        :param application_log: Content of the application log.
        Default is None.

        :returns: Whether the dialog should be closed.
        """
        raise NotImplementedError


class GithubBackend(BaseBackend):
    """
    This backend sends the crash report on a github issue tracker::

        https://github.com/gh_owner/gh_repo

    Usage::

        github_backend = griffin.widgets.github.backend.GithubBackend(
            'griffin-ide', 'griffin')
    """

    def __init__(self, gh_owner, gh_repo, formatter=None, parent_widget=None):
        """
        :param gh_owner: Name of the owner of the github repository.
        :param gh_repo: Name of the repository on github.
        """
        super(GithubBackend, self).__init__(
            formatter, "Submit on github",
            "Submit the issue on our issue tracker on github", None,
            parent_widget=parent_widget)
        self.gh_owner = gh_owner
        self.gh_repo = gh_repo
        self._show_msgbox = True  # False when running the test suite

    def send_report(self, title, body, application_log=None):
        logger.debug('sending bug report on github\ntitle=%s\nbody=%s',
                     title, body)

        # Credentials
        credentials = self.get_user_credentials()
        token = credentials['token']

        if token is None:
            return False
        logger.debug('got user credentials')

        try:
            auth = github.Auth.Token(token)
        except Exception as exc:
            logger.warning("Invalid token.")
            if self._show_msgbox:
                # Raise error so that GriffinErrorDialog can capture and
                # redirect user to web interface.
                raise exc
            return False

        gh = github.Github(auth=auth)

        # upload log file as a gist
        if application_log:
            url = self.upload_log_file(gh, application_log)
            body += '\nApplication log: %s' % url

        try:
            repo = gh.get_repo(f"{self.gh_owner}/{self.gh_repo}")
            issue = repo.create_issue(title=title, body=body)
        except github.BadCredentialsException as exc:
            logger.warning('Failed to create issue on Github. '
                           'Status=%d: %s', exc.status, exc.data['message'])
            if self._show_msgbox:
                QMessageBox.warning(
                    self.parent_widget, _('Invalid credentials'),
                    _('Failed to create issue on Github, '
                      'invalid credentials...')
                )
                # Raise error so that GriffinErrorDialog can capture and
                # redirect user to web interface.
                raise exc
            return False
        except github.GithubException as exc:
            logger.warning('Failed to create issue on Github. '
                           'Status=%d: %s', exc.status, exc.data['message'])
            if self._show_msgbox:
                QMessageBox.warning(
                    self.parent_widget,
                    _('Failed to create issue'),
                    _('Failed to create issue on Github. Status %d: %s') %
                    (exc.status, exc.data['message'])
                )
                # Raise error so that GriffinErrorDialog can capture and
                # redirect user to web interface.
                raise exc
            return False
        except Exception as exc:
            logger.warning('Failed to create issue on Github.\n%s', exc)
            if self._show_msgbox:
                # Raise error so that GriffinErrorDialog can capture and
                # redirect user to web interface.
                raise exc
            return False
        else:
            if self._show_msgbox:
                ret = QMessageBox.question(
                    self.parent_widget, _('Issue created on Github'),
                    _('Issue successfully created. Would you like to open the '
                      'issue in your web browser?'))
                if ret in [QMessageBox.Yes, QMessageBox.Ok]:
                    webbrowser.open(issue.html_url)
            return True

    def _get_credentials_from_settings(self):
        """Get the stored credentials if any."""
        remember_token = CONF.get('main', 'report_error/remember_token')
        return remember_token

    def _store_token(self, token, remember=False):
        """Store token for future use."""
        if token and remember:
            try:
                keyring.set_password('github', 'token', token)
            except Exception:
                if self._show_msgbox:
                    QMessageBox.warning(self.parent_widget,
                                        _('Failed to store token'),
                                        _('It was not possible to securely '
                                          'save your token. You will be '
                                          'prompted for your Github token '
                                          'next time you want to report '
                                          'an issue.'))
                remember = False
        CONF.set('main', 'report_error/remember_token', remember)

    def get_user_credentials(self):
        """Get user credentials with the login dialog."""
        token = None
        remember_token = self._get_credentials_from_settings()
        if remember_token:
            # Get token from keyring
            try:
                token = keyring.get_password('github', 'token')
            except Exception:
                # No safe keyring backend
                if self._show_msgbox:
                    QMessageBox.warning(self.parent_widget,
                                        _('Failed to retrieve token'),
                                        _('It was not possible to retrieve '
                                          'your token. Please introduce it '
                                          'again.'))

        if not running_under_pytest():
            credentials = DlgGitHubLogin.login(
                self.parent_widget,
                token,
                remember_token)

            if credentials['token']:
                self._store_token(credentials['token'],
                                  credentials['remember_token'])
                CONF.set('main', 'report_error/remember_token',
                         credentials['remember_token'])
        else:
            return dict(token=token,
                        remember_token=remember_token)

        return credentials

    def upload_log_file(self, gh, log_content):
        auth_user = gh.get_user()
        try:
            qApp = QApplication.instance()
            qApp.setOverrideCursor(Qt.WaitCursor)
            gist = auth_user.create_gist(
                description="GriffinIDE log", public=True,
                files={'GriffinIDE.log': github.InputFileContent(log_content)}
            )
            qApp.restoreOverrideCursor()
        except github.GithubException as exc:
            msg = (
                'Failed to upload log report as a gist. Status '
                f'{exc.status}: {exc.data["message"]}'
            )
            logger.warning(msg)
            return msg
        else:
            return gist.html_url
