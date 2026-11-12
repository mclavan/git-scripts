"""
Pull Windows - Maya utility

Run from the Maya Script Editor (Python tab):

    import sys
    import importlib

    script_folder = r"D:\OneDrive - Full Sail University\CGA-3312\rigging_tools\git-scripts"
    if script_folder not in sys.path:
        sys.path.insert(0, script_folder)

    import dinnerTime
    importlib.reload(dinnerTime)
    dinnerTime.show()

After editing this file, run the commands again to reload the tool.
Use "Pull Windows to This Position" to align visible Maya windows with
this tool window, or "Move Windows to This Screen's Top-Left" to align
them with the top-left corner of the screen containing this tool.
"""

try:
    from PySide6 import QtCore, QtWidgets
    import shiboken6 as shiboken
except ImportError:
    from PySide2 import QtCore, QtWidgets
    import shiboken2 as shiboken

import maya.OpenMayaUI as omui


def _maya_main_window_pointer():
    pointer = omui.MQtUtil.mainWindow()
    if not pointer:
        raise RuntimeError("Could not find Maya's main window.")
    return int(pointer)


def _maya_main_window():
    return shiboken.wrapInstance(
        _maya_main_window_pointer(),
        QtWidgets.QWidget,
    )


class PullWindowsDialog(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setWindowTitle("Pull Windows")
        self.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)

        layout = QtWidgets.QVBoxLayout(self)

        windows_header = QtWidgets.QHBoxLayout()
        windows_header.addWidget(QtWidgets.QLabel("Currently open windows"))
        refresh_button = QtWidgets.QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_windows)
        windows_header.addWidget(refresh_button)
        layout.addLayout(windows_header)

        self.windows_list = QtWidgets.QListWidget()
        self.windows_list.setMinimumHeight(120)
        self.windows_list.itemDoubleClicked.connect(self.pull_selected_window)
        layout.addWidget(self.windows_list)

        pull_button = QtWidgets.QPushButton("Pull Windows to This Position")
        pull_button.clicked.connect(self.pull_windows)
        layout.addWidget(pull_button)

        top_left_button = QtWidgets.QPushButton(
            "Move Windows to This Screen's Top-Left"
        )
        top_left_button.clicked.connect(self.move_windows_to_screen_top_left)
        layout.addWidget(top_left_button)

        self.refresh_windows()

    def _windows_to_move(self):
        main_window_pointer = _maya_main_window_pointer()
        tool_window_pointer = shiboken.getCppPointer(self)[0]
        app = QtWidgets.QApplication.instance()

        if app is None:
            raise RuntimeError("Could not find Maya's Qt application.")

        return [
            window
            for window in app.topLevelWidgets()
            if shiboken.getCppPointer(window)[0]
            not in (main_window_pointer, tool_window_pointer)
            and window.isVisible()
        ]

    def refresh_windows(self):
        self.windows_list.clear()
        self._listed_windows = self._windows_to_move()
        for window in self._listed_windows:
            title = window.windowTitle().strip()
            self.windows_list.addItem(title or window.objectName() or "Untitled window")

    def pull_windows(self):
        self._move_windows_to(self.frameGeometry().topLeft())

    def pull_selected_window(self, item):
        """Move the window represented by a double-clicked list item."""
        row = self.windows_list.row(item)
        if row < 0 or row >= len(self._listed_windows):
            self.refresh_windows()
            return

        window = self._listed_windows[row]
        try:
            if not window.isVisible():
                self.refresh_windows()
                return
            delta = self.frameGeometry().topLeft() - window.frameGeometry().topLeft()
            window.move(window.pos() + delta)
        except RuntimeError:
            # The selected window may have closed since the last refresh.
            self.refresh_windows()

    def move_windows_to_screen_top_left(self):
        screen = self.screen()
        if screen is None:
            raise RuntimeError("Could not determine which screen contains this tool.")
        self._move_windows_to(screen.geometry().topLeft())

    def _move_windows_to(self, target):
        for window in self._windows_to_move():
            delta = target - window.frameGeometry().topLeft()
            window.move(window.pos() + delta)


_tool_window = None


def show():
    global _tool_window

    if _tool_window is None:
        _tool_window = PullWindowsDialog(_maya_main_window())

    _tool_window.show()
    _tool_window.raise_()
    _tool_window.activateWindow()
    _tool_window.refresh_windows()
