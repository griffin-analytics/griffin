# -*- coding: utf-8 -*-
#
# Copyright © Griffin Project Contributors
# 
# (see griffin/__init__.py for details)

"""Custom stylesheets used in Griffin."""

# Standard library imports
import copy
import os
import sys

# Third-party imports
import qdarkstyle
from qstylizer.parser import parse as parse_stylesheet
import qstylizer.style

# Local imports
from griffin.api.config.mixins import GriffinConfigurationAccessor
from griffin.api.fonts import GriffinFontType, GriffinFontsMixin
from griffin.api.utils import classproperty
from griffin.config.gui import is_dark_interface
from griffin.utils.palette import GriffinPalette


# =============================================================================
# ---- Constants
# =============================================================================
MAC = sys.platform == 'darwin'
WIN = os.name == 'nt'


class AppStyle(GriffinFontsMixin):
    """Enum with several constants used in the application style."""

    # Size of margins.
    MarginSize = 3  # px

    # Size of find widget line edits (e.g. FinderWidget and FindReplace)
    FindMinWidth = 400  # px
    FindHeight = 26  # px

    # To have it for quick access because it's needed a lot in Mac
    MacScrollBarWidth = 16  # px

    # Icon size in config pages
    ConfigPageIconSize = 20

    # Padding for QPushButton's
    QPushButtonPadding = f'{MarginSize + 1}px {4 * MarginSize}px'

    @classproperty
    def _fs(cls):
        """Interface font size in points."""
        return cls.get_font(GriffinFontType.Interface).pointSize()

    @classproperty
    def ComboBoxMinHeight(cls):
        """Combobox min height in em's."""
        font_size = cls._fs

        if font_size < 10:
            min_height = 1.8
        elif 10 <= font_size < 13:
            min_height = 1.7 if MAC else 1.6
        else:
            min_height = 1.5 if MAC else 1.4

        return min_height

    # Padding for content inside an element of higher hierarchy
    InnerContentPadding = 5 * MarginSize


# =============================================================================
# ---- Base stylesheet class
# =============================================================================
class GriffinStyleSheet:
    """Base class for Griffin stylesheets."""

    SET_STYLESHEET_AT_INIT = True
    """
    Decide if the stylesheet must be set when the class is initialized.

    Notes
    -----
    There are some stylesheets for which this is not possible (e.g. the ones
    that need to access our fonts).
    """

    def __init__(self):
        self._stylesheet = qstylizer.style.StyleSheet()
        if self.SET_STYLESHEET_AT_INIT:
            self.set_stylesheet()

    def get_stylesheet(self):
        return self._stylesheet

    def to_string(self):
        if self._stylesheet.toString() == "":
            self.set_stylesheet()
        return self._stylesheet.toString()

    def get_copy(self):
        """
        Return a copy of the sytlesheet.

        This allows it to be modified for specific widgets.
        """
        if self._stylesheet.toString() == "":
            self.set_stylesheet()
        return copy.deepcopy(self)

    def set_stylesheet(self):
        raise NotImplementedError(
            "Subclasses need to implement this method to set the _stylesheet "
            "attribute as a Qstylizer StyleSheet object."
        )

    def __str__(self):
        """
        Get a string representation of the stylesheet object this class
        holds.
        """
        return self.to_string()


# =============================================================================
# ---- Application stylesheet
# =============================================================================
class AppStylesheet(GriffinStyleSheet, GriffinConfigurationAccessor):
    """
    Class to build and access the stylesheet we use in the entire
    application.
    """

    # Don't create the stylesheet here so that Griffin gets the app font from
    # the system when it starts for the first time. This also allows us to
    # display the splash screen more quickly because the stylesheet is then
    # computed only when it's going to be applied to the app, not when this
    # object is imported.
    SET_STYLESHEET_AT_INIT = False

    def __init__(self):
        super().__init__()
        self._stylesheet_as_string = None

    def to_string(self):
        """Save stylesheet as a string for quick access."""
        if self._stylesheet_as_string is None:
            self.set_stylesheet()
            self._stylesheet_as_string = self._stylesheet.toString()
        return self._stylesheet_as_string

    def set_stylesheet(self):
        """
        This takes the stylesheet from QDarkstyle and applies our
        customizations to it.
        """
        stylesheet = qdarkstyle.load_stylesheet(palette=GriffinPalette)
        self._stylesheet = parse_stylesheet(stylesheet)

        # Add our customizations
        self._customize_stylesheet()

    def _customize_stylesheet(self):
        """Apply our customizations to the stylesheet."""
        css = self._stylesheet

        # App font properties
        font_family = self.get_conf('app_font/family', section='appearance')
        font_size = int(self.get_conf('app_font/size', section='appearance'))

        # Remove padding and border for QStackedWidget (used in Plots
        # and the Variable Explorer)
        css['QStackedWidget'].setValues(
            border='0px',
            padding='0px',
        )

        # Remove margin when pressing buttons
        css["QToolButton:pressed"].setValues(
            margin='0px'
        )

        # Remove border, padding and spacing for main toolbar
        css.QToolBar.setValues(
            borderBottom='0px',
            padding='0px',
            spacing='0px',
        )

        # Remove margins around separators and decrease size a bit
        css['QMainWindow::separator:horizontal'].setValues(
            marginTop='0px',
            marginBottom='0px',
            # This is summed to the separator padding (2px)
            width="3px",
            # Hide image because the default image is not visible at this size
            image="none"
        )

        css['QMainWindow::separator:vertical'].setValues(
            marginLeft='0px',
            marginRight='0px',
            # This is summed to the separator padding (2px)
            height='3px',
            # Hide image because the default image is not visible at this size
            image="none"
        )

        # Increase padding and fix disabled color for QPushButton's
        css.QPushButton.setValues(padding=AppStyle.QPushButtonPadding)

        for state in ['disabled', 'checked', 'checked:disabled']:
            css[f'QPushButton:{state}'].setValues(
                padding=AppStyle.QPushButtonPadding,
            )

            # This is especially necessary in the light theme because the
            # contrast between the background and text colors is too small
            if state in ['disabled', 'checked:disabled']:
                css[f"QPushButton:{state}"].setValues(
                    color=GriffinPalette.COLOR_TEXT_3,
                )

        # Adjust QToolButton style to our needs.
        # This affects not only the pane toolbars but also the
        # find/replace widget, the finder in the Variable Explorer,
        # and all QToolButton's that are not part of the main toolbar.
        for element in ['QToolButton', 'QToolButton:disabled']:
            css[f'{element}'].setValues(
                backgroundColor='transparent'
            )

        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = GriffinPalette.COLOR_BACKGROUND_2
            else:
                color = GriffinPalette.COLOR_BACKGROUND_3
            css[f'QToolButton:{state}'].setValues(
                backgroundColor=color
            )

        # Adjust padding of QPushButton's in QDialog's
        for widget in ["QPushButton", "QPushButton:disabled"]:
            css[f"QDialogButtonBox {widget}"].setValues(
                padding=(
                    AppStyle.QPushButtonPadding
                    if (MAC or WIN)
                    else
                    f"{AppStyle.MarginSize + 1}px {AppStyle.MarginSize}px"
                ),
                # This width comes from QDarkstyle but it's too big on Mac
                minWidth="50px" if WIN else ("60px" if MAC else "80px"),
            )

        css["QDialogButtonBox QPushButton:!default"].setValues(
            padding=(
                AppStyle.QPushButtonPadding
                if (MAC or WIN)
                else
                f"{AppStyle.MarginSize + 1}px {AppStyle.MarginSize}px"
            ),
            # This width comes from QDarkstyle but it's too big on Mac
            minWidth="50px" if WIN else ("60px" if MAC else "80px"),
        )

        # Remove icons in QMessageBoxes
        css["QDialogButtonBox"]["dialogbuttonbox-buttons-have-icons"].setValue(
            "0"
        )

        # Set font for widgets that don't inherit it from the application
        # This is necessary for griffin-ide/griffin#5942.
        for widget in ['QToolTip', 'QDialog', 'QListView', 'QTreeView',
                       'QHeaderView::section', 'QTableView']:
            css[f'{widget}'].setValues(
                fontFamily=font_family,
                fontSize=f'{font_size}pt'
            )

        # Make lineedits have *almost* the same height as our comboboxes. This
        # is not perfect because (oddly enough) Qt doesn't set the same height
        # for both when using the same value, but it's close enough.
        css.QLineEdit.setValues(
            minHeight=f'{AppStyle.ComboBoxMinHeight - 0.25}em'
        )

        # Do the same for spinboxes
        css.QSpinBox.setValues(
            minHeight=f'{AppStyle.ComboBoxMinHeight - 0.25}em'
        )

        # Remove border in QGroupBox to avoid the "boxes within boxes"
        # antipattern. Also, increase its title font in one point to make it
        # more relevant.
        css.QGroupBox.setValues(
            border='0px',
            fontSize=f'{font_size + 1}pt',
        )

        # Increase separation between title and content of QGroupBoxes and fix
        # its alignment.
        css['QGroupBox::title'].setValues(
            paddingTop='-0.3em',
            left='0px',
        )

        # Decrease splitter handle size to be a bit smaller than QMainWindow
        # separators.
        css['QSplitter::handle'].setValues(
            padding="0px",
        )

        css['QSplitter::handle:horizontal'].setValues(
            width="5px",
            image="none"
        )

        css['QSplitter::handle:vertical'].setValues(
            height="5px",
            image="none"
        )

        # Make splitter handle color match the one of QMainWindow separators
        css['QSplitter::handle:hover'].setValues(
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_6,
        )

        # Add padding to tooltips
        css.QToolTip.setValues(
            padding="1px 2px",
        )

        # Add padding to tree widget items to make them look better
        css["QTreeWidget::item"].setValues(
            padding=f"{AppStyle.MarginSize - 1}px 0px",
        )

        css["QTreeView::item"].setValues(
            padding=f"{AppStyle.MarginSize - 1}px 0px",
        )


APP_STYLESHEET = AppStylesheet()

# =============================================================================
# ---- Toolbar stylesheets
# =============================================================================
class ApplicationToolbarStylesheet(GriffinStyleSheet):
    """Stylesheet for application toolbars."""

    BUTTON_WIDTH = '47px'
    BUTTON_HEIGHT = '47px'
    BUTTON_MARGIN_LEFT = '3px'
    BUTTON_MARGIN_RIGHT = '3px'

    def set_stylesheet(self):
        css = self.get_stylesheet()

        # Main background color
        css.QToolBar.setValues(
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_4
        )

        # Adjust QToolButton to follow the main toolbar style.
        css.QToolButton.setValues(
            width=self.BUTTON_WIDTH,
            height=self.BUTTON_HEIGHT,
            marginLeft=self.BUTTON_MARGIN_RIGHT,
            marginRight=self.BUTTON_MARGIN_RIGHT,
            border='0px',
            borderRadius='0px',
            padding='0px',
        )

        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = GriffinPalette.COLOR_BACKGROUND_5
            else:
                color = GriffinPalette.COLOR_BACKGROUND_6
            css[f'QToolBar QToolButton:{state}'].setValues(
                backgroundColor=color
            )

        # Remove indicator for popup mode
        css['QToolBar QToolButton::menu-indicator'].setValues(
            image='none'
        )


class PanesToolbarStyleSheet(GriffinStyleSheet):
    """Stylesheet for pane toolbars."""

    # These values make buttons to be displayed at 44px according to Gammaray
    BUTTON_WIDTH = '37px'
    BUTTON_HEIGHT = '37px'

    def set_stylesheet(self):
        css = self.get_stylesheet()

        css.QToolBar.setValues(
            spacing='4px'
        )

        css.QToolButton.setValues(
            height=self.BUTTON_HEIGHT,
            width=self.BUTTON_WIDTH,
            border='0px',
            borderRadius='0px',
            margin='0px'
        )

        # Remove indicator for popup mode
        css['QToolButton::menu-indicator'].setValues(
            image='none'
        )


APP_TOOLBAR_STYLESHEET = ApplicationToolbarStylesheet()
PANES_TOOLBAR_STYLESHEET = PanesToolbarStyleSheet()


# =============================================================================
# ---- Tabbar stylesheets
# =============================================================================
class BaseTabBarStyleSheet(GriffinStyleSheet):
    """Base style for tabbars."""

    OBJECT_NAME = ''

    # Additional border for scroll buttons
    SCROLL_BUTTONS_BORDER_WIDTH = '0px'

    # Position for the scroll buttons additional border
    SCROLL_BUTTONS_BORDER_POS = ''

    def set_stylesheet(self):
        css = self.get_stylesheet()
        buttons_color = GriffinPalette.COLOR_BACKGROUND_1

        # Set style for scroll buttons
        css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
            background=buttons_color,
            borderRadius='0px',
        )

        if self.SCROLL_BUTTONS_BORDER_POS == 'right':
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                borderRight=(
                    f'{self.SCROLL_BUTTONS_BORDER_WIDTH} solid {buttons_color}'
                )
            )
        else:
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                borderBottom=(
                    f'{self.SCROLL_BUTTONS_BORDER_WIDTH} solid {buttons_color}'
                )
            )

        # Hover and pressed state for scroll buttons
        for state in ['hover', 'pressed', 'checked', 'checked:hover']:
            if state == 'hover':
                color = GriffinPalette.COLOR_BACKGROUND_2
            else:
                color = GriffinPalette.COLOR_BACKGROUND_3
            css[f'QTabBar{self.OBJECT_NAME} QToolButton:{state}'].setValues(
                background=color
            )

        # Set width for scroll buttons
        css['QTabBar::scroller'].setValues(
            width='66px',
        )


class PanesTabBarStyleSheet(PanesToolbarStyleSheet, BaseTabBarStyleSheet):
    """Stylesheet for pane tabbars"""

    TOP_MARGIN = '12px'
    OBJECT_NAME = '#pane-tabbar'
    SCROLL_BUTTONS_BORDER_WIDTH = '5px'
    SCROLL_BUTTONS_BORDER_POS = 'right'

    def set_stylesheet(self):
        # Calling super().set_stylesheet() here doesn't work.
        PanesToolbarStyleSheet.set_stylesheet(self)
        BaseTabBarStyleSheet.set_stylesheet(self)
        css = self.get_stylesheet()

        # This removes a white dot that appears to the left of right corner
        # widgets
        css.QToolBar.setValues(
            marginLeft='-3px' if WIN else '-1px',
        )

        # QTabBar forces the corner widgets to be smaller than they should.
        # be. The added top margin allows the toolbuttons to expand to their
        # normal size.
        # See: griffin-ide/griffin#13600
        css['QTabBar::tab'].setValues(
            marginTop=self.TOP_MARGIN,
            paddingTop='4px',
            paddingBottom='4px',
            paddingLeft='4px' if MAC else '10px',
            paddingRight='10px' if MAC else '4px'
        )

        if MAC:
            # Show tabs left-aligned on Mac and remove spurious
            # pixel to the left.
            css.QTabBar.setValues(
                alignment='left',
                marginLeft='-1px'
            )

            css['QTabWidget::tab-bar'].setValues(
                alignment='left',
            )
        else:
            # Remove spurious pixel to the left
            css.QTabBar.setValues(
                marginLeft='-3px' if WIN else '-1px'
            )

        # Fix minor visual glitch when hovering tabs
        # See griffin-ide/griffin#15398
        css['QTabBar::tab:hover'].setValues(
            paddingTop='3px',
            paddingBottom='3px',
            paddingLeft='3px' if MAC else '9px',
            paddingRight='9px' if MAC else '3px'
        )

        for state in ['selected', 'selected:hover']:
            css[f'QTabBar::tab:{state}'].setValues(
                paddingTop='4px',
                paddingBottom='3px',
                paddingLeft='4px' if MAC else '10px',
                paddingRight='10px' if MAC else '4px'
            )

        # Remove border between selected tab and pane below
        css['QTabWidget::pane'].setValues(
            borderTop='0px',
        )

        # Adjust margins of corner widgets
        css['QTabWidget::left-corner'].setValues(
            top='-1px',
        )

        css['QTabWidget::right-corner'].setValues(
            top='-1px',
            right='-3px' if WIN else '-1px'
        )

        # Make scroll buttons height match the one of tabs
        css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
            marginTop=self.TOP_MARGIN,
        )

        # Make scroll button icons smaller on Windows and Mac
        if WIN or MAC:
            css[f'QTabBar{self.OBJECT_NAME} QToolButton'].setValues(
                padding=f'{5 if WIN else 7}px',
            )


class BaseDockTabBarStyleSheet(BaseTabBarStyleSheet):
    """Base style for dockwidget tabbars."""

    SCROLL_BUTTONS_BORDER_WIDTH = '2px'
    SCROLL_BUTTONS_PADDING = 7 if WIN else 9

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()

        # Center tabs to differentiate them from the regular ones.
        # See griffin-ide/griffin#9763 for details.
        css.QTabBar.setValues(
            alignment='center'
        )

        css['QTabWidget::tab-bar'].setValues(
            alignment='center'
        )

        # Style for selected tabs
        css['QTabBar::tab:selected'].setValues(
            color=(
                GriffinPalette.COLOR_TEXT_1 if is_dark_interface() else
                GriffinPalette.COLOR_BACKGROUND_1
            ),
            backgroundColor=GriffinPalette.SPECIAL_TABS_SELECTED,
        )

        # Make scroll button icons smaller on Windows and Mac
        if WIN or MAC:
            css['QTabBar QToolButton'].setValues(
                padding=f'{self.SCROLL_BUTTONS_PADDING}px',
            )


class SpecialTabBarStyleSheet(BaseDockTabBarStyleSheet):
    """
    Style for special tab bars.

    Notes
    -----
    This is the base class for horizontal tab bars that follow the design
    discussed on issue griffin-ide/ux-improvements#4.
    """

    SCROLL_BUTTONS_BORDER_POS = 'right'

    def set_stylesheet(self):
        super().set_stylesheet()

        # -- Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # -- Basic style
        css['QTabBar::tab'].setValues(
            # Only add margin to the bottom
            margin=f'0px 0px {2 * margin_size}px 0px',
            # Border radius is added for specific tabs (see below)
            borderRadius='0px',
            # Remove a colored border added by QDarkStyle
            borderBottom='0px',
            # Padding for text inside tabs
            padding='4px 10px',
        )

        # -- Style for not selected tabs
        css['QTabBar::tab:!selected'].setValues(
            border='0px',
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_4,
            borderLeft=f'1px solid {GriffinPalette.COLOR_BACKGROUND_4}',
            borderRight=f'1px solid {GriffinPalette.SPECIAL_TABS_SEPARATOR}',
        )

        css['QTabBar::tab:!selected:hover'].setValues(
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5,
            borderLeftColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        # -- Style for the not selected tabs to the right and left of the
        # selected one.
        # Note: For some strange reason, Qt uses the `next-selected` state for
        # the left tab.
        css['QTabBar::tab:next-selected'].setValues(
            borderRightColor=GriffinPalette.COLOR_BACKGROUND_4,
        )

        css['QTabBar::tab:next-selected:hover'].setValues(
            borderRightColor=GriffinPalette.SPECIAL_TABS_SEPARATOR,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        css['QTabBar::tab:previous-selected'].setValues(
            borderLeftColor=GriffinPalette.COLOR_BACKGROUND_4,
        )

        css['QTabBar::tab:previous-selected:hover'].setValues(
            borderLeftColor=GriffinPalette.SPECIAL_TABS_SEPARATOR,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        # -- First and last tabs have rounded borders
        css['QTabBar::tab:first'].setValues(
            borderTopLeftRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            borderBottomLeftRadius=GriffinPalette.SIZE_BORDER_RADIUS,
        )

        css['QTabBar::tab:last'].setValues(
            borderTopRightRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            borderBottomRightRadius=GriffinPalette.SIZE_BORDER_RADIUS,
        )

        # -- Last tab doesn't need to show the separator
        css['QTabBar::tab:last:!selected'].setValues(
            borderRightColor=GriffinPalette.COLOR_BACKGROUND_4
        )

        css['QTabBar::tab:last:!selected:hover'].setValues(
            borderRightColor=GriffinPalette.COLOR_BACKGROUND_5,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        # -- Set bottom margin for scroll buttons.
        css['QTabBar QToolButton'].setValues(
            marginBottom=f'{2 * margin_size}px',
        )


class PreferencesTabBarStyleSheet(SpecialTabBarStyleSheet, GriffinFontsMixin):
    """Style for tab bars in our Preferences dialog."""

    # This is necessary because this class needs to access fonts
    SET_STYLESHEET_AT_INIT = False

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        font = self.get_font(GriffinFontType.Interface, font_size_delta=1)

        # Set font size to be one point bigger than the regular text.
        css.QTabBar.setValues(
            fontSize=f'{font.pointSize()}pt',
        )

        # Make scroll buttons a bit bigger on Windows and Mac (this has no
        # effect on Linux).
        if WIN or MAC:
            css['QTabBar QToolButton'].setValues(
                padding=f'{self.SCROLL_BUTTONS_PADDING - 1}px',
            )

        # Increase padding around text because we're using a larger font.
        css['QTabBar::tab'].setValues(
            padding='6px 10px',
        )

        # Remove border and add padding for content inside tabs
        css['QTabWidget::pane'].setValues(
            border='0px',
            padding=f'{AppStyle.InnerContentPadding}px',
        )


class HorizontalDockTabBarStyleSheet(SpecialTabBarStyleSheet):
    """Style for horizontal dockwidget tab bars."""

    def set_stylesheet(self):
        super().set_stylesheet()

        # Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # Tabs style
        css['QTabBar::tab'].setValues(
            # No margins to left/right but top/bottom to separate tabbar from
            # the dockwidget areas.
            # Notes:
            # * Top margin is half the one at the bottom so that we can show
            #   a bottom margin on dockwidgets that are not tabified.
            # * The other half is added through the _margin_bottom attribute of
            #   PluginMainWidget.
            margin=f'{margin_size}px 0px {2 * margin_size}px 0px',
            # Remove a colored border added by QDarkStyle
            borderTop='0px',
        )

        # Add margin to first and last tabs to avoid them touching the left and
        # right dockwidget areas, respectively.
        css['QTabBar::tab:first'].setValues(
            marginLeft=f'{2 * margin_size}px',
        )

        css['QTabBar::tab:last'].setValues(
            marginRight=f'{2 * margin_size}px',
        )

        # Make top and bottom margins for scroll buttons even.
        # This is necessary since the tabbar top margin is half the one at the
        # bottom (see the notes in the 'QTabBar::tab' style above).
        css['QTabBar QToolButton'].setValues(
            marginTop='0px',
            marginBottom=f'{margin_size}px',
        )


class VerticalDockTabBarStyleSheet(BaseDockTabBarStyleSheet):
    """Style for vertical dockwidget tab bars."""

    SCROLL_BUTTONS_BORDER_POS = 'bottom'

    def set_stylesheet(self):
        super().set_stylesheet()

        # -- Main constants
        css = self.get_stylesheet()
        margin_size = AppStyle.MarginSize

        # -- Basic style
        css['QTabBar::tab'].setValues(
            # No margins to top/bottom but left/right to separate tabbar from
            # the dockwidget areas
            margin=f'0px {2 * margin_size}px',
            # Border radius is added for specific tabs (see below)
            borderRadius='0px',
            # Remove colored borders added by QDarkStyle
            borderLeft='0px',
            borderRight='0px',
            # Padding for text inside tabs
            padding='10px 4px',
        )

        # -- Style for not selected tabs
        css['QTabBar::tab:!selected'].setValues(
            border='0px',
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_4,
            borderTop=f'1px solid {GriffinPalette.COLOR_BACKGROUND_4}',
            borderBottom=f'1px solid {GriffinPalette.SPECIAL_TABS_SEPARATOR}',
        )

        css['QTabBar::tab:!selected:hover'].setValues(
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5,
            borderTopColor=GriffinPalette.COLOR_BACKGROUND_5,
        )

        # -- Style for the not selected tabs above and below the selected one.
        css['QTabBar::tab:next-selected'].setValues(
            borderBottomColor=GriffinPalette.COLOR_BACKGROUND_4,
        )

        css['QTabBar::tab:next-selected:hover'].setValues(
            borderBottomColor=GriffinPalette.SPECIAL_TABS_SEPARATOR,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        css['QTabBar::tab:previous-selected'].setValues(
            borderTopColor=GriffinPalette.COLOR_BACKGROUND_4,
        )

        css['QTabBar::tab:previous-selected:hover'].setValues(
            borderTopColor=GriffinPalette.SPECIAL_TABS_SEPARATOR,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        # -- First and last tabs have rounded borders.
        # Also, add margin to avoid them touch the top and bottom borders,
        # respectively.
        css['QTabBar::tab:first'].setValues(
            borderTopLeftRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            borderTopRightRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            marginTop=f'{2 * margin_size}px',
        )

        css['QTabBar::tab:last'].setValues(
            borderBottomLeftRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            borderBottomRightRadius=GriffinPalette.SIZE_BORDER_RADIUS,
            marginBottom=f'{2 * margin_size}px',
        )

        # -- Last tab doesn't need to show the separator
        css['QTabBar::tab:last:!selected'].setValues(
            borderBottomColor=GriffinPalette.COLOR_BACKGROUND_4
        )

        css['QTabBar::tab:last:!selected:hover'].setValues(
            borderBottomColor=GriffinPalette.COLOR_BACKGROUND_5,
            backgroundColor=GriffinPalette.COLOR_BACKGROUND_5
        )

        # -- Make style for scroll buttons match the horizontal one
        css['QTabBar QToolButton'].setValues(
            marginLeft=f'{margin_size}px',
            marginRight=f'{margin_size}px',
        )


PANES_TABBAR_STYLESHEET = PanesTabBarStyleSheet()
HORIZONTAL_DOCK_TABBAR_STYLESHEET = HorizontalDockTabBarStyleSheet()
VERTICAL_DOCK_TABBAR_STYLESHEET = VerticalDockTabBarStyleSheet()
PREFERENCES_TABBAR_STYLESHEET = PreferencesTabBarStyleSheet()


# =============================================================================
# ---- Style for special dialogs
# =============================================================================
class DialogStyle(GriffinFontsMixin):
    """Style constants for tour and about dialogs."""

    IconScaleFactor = 0.5
    BackgroundColor = GriffinPalette.COLOR_BACKGROUND_2
    BorderColor = GriffinPalette.COLOR_BACKGROUND_5

    @classproperty
    def _fs(cls):
        return cls.get_font(GriffinFontType.Interface).pointSize()

    @classproperty
    def TitleFontSize(cls):
        if WIN:
            return f"{cls._fs + 6}pt"
        elif MAC:
            return f"{cls._fs + 6}pt"
        else:
            return f"{cls._fs + 4}pt"

    @classproperty
    def ContentFontSize(cls):
        if WIN:
            return f"{cls._fs + 4}pt"
        elif MAC:
            return f"{cls._fs + 2}pt"
        else:
            return f"{cls._fs + 2}pt"

    @classproperty
    def ButtonsFontSize(cls):
        if WIN:
            return f"{cls._fs + 5}pt"
        elif MAC:
            return f"{cls._fs + 2}pt"
        else:
            return f"{cls._fs + 3}pt"

    @classproperty
    def ButtonsPadding(cls):
        if WIN:
            return f"{AppStyle.MarginSize + 1}px {5 * AppStyle.MarginSize}px"
        elif MAC:
            return f"{2 * AppStyle.MarginSize}px {4 * AppStyle.MarginSize}px"
        else:
            return f"{AppStyle.MarginSize + 1}px {AppStyle.MarginSize}px"
