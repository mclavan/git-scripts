
import maya.cmds as cmds
import maya.OpenMayaUI as omui

try:
    from PySide6 import QtWidgets, QtCore
    from shiboken6 import wrapInstance
except ImportError:
    from PySide2 import QtWidgets, QtCore
    from shiboken2 import wrapInstance


# ------------------------------------------------------------
# Maya Symmetry Monitor
# ------------------------------------------------------------

def _symMon_maya_window():
    ptr = omui.MQtUtil.mainWindow()
    return wrapInstance(int(ptr), QtWidgets.QWidget)


class _MayaSymmetryMonitor(QtWidgets.QDialog):

    def __init__(self, parent=_symMon_maya_window()):
        super(_MayaSymmetryMonitor, self).__init__(parent)

        self.setObjectName("mayaSymmetryMonitor")
        self.setWindowTitle("Symmetry Monitor")

        # Maya-owned floating window.
        self.setWindowFlags(QtCore.Qt.Tool)

        self.setMinimumWidth(255)
        self.setMaximumWidth(255)

        self._build_ui()
        self._connect_ui()

        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_state)
        self.timer.start(400)

        self.refresh_state()

    # --------------------------------------------------------
    # UI
    # --------------------------------------------------------

    def _build_ui(self):

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        title = QtWidgets.QLabel("CURRENT STATE")
        title.setStyleSheet(
            "color: #999999;"
            "font-size: 10px;"
            "font-weight: bold;"
        )
        main_layout.addWidget(title)

        self.state_label = QtWidgets.QLabel("Checking...")
        self.state_label.setAlignment(QtCore.Qt.AlignCenter)
        self.state_label.setMinimumHeight(55)

        self.state_label.setStyleSheet("""
            QLabel {
                background-color: #353535;
                color: #AAAAAA;
                font-size: 22px;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
        """)

        main_layout.addWidget(self.state_label)
        main_layout.addWidget(self._divider())

        mode_label = QtWidgets.QLabel("CHANGE MODE")
        mode_label.setStyleSheet(
            "color: #999999; font-size: 10px; font-weight: bold;"
        )
        main_layout.addWidget(mode_label)

        mode_layout = QtWidgets.QGridLayout()
        mode_layout.setSpacing(5)

        self.mode_buttons = {}

        modes = [
            ("Off", "off"),
            ("Object", "object"),
            ("World", "world"),
            ("Topology", "topo")
        ]

        for i, (label, mode) in enumerate(modes):

            button = QtWidgets.QPushButton(label)
            button.setCheckable(True)
            button.setMinimumHeight(30)

            mode_layout.addWidget(button, i // 2, i % 2)
            self.mode_buttons[mode] = button

        main_layout.addLayout(mode_layout)
        main_layout.addWidget(self._divider())

        self.axis_label = QtWidgets.QLabel("AXIS")
        self.axis_label.setStyleSheet(
            "color: #999999; font-size: 10px; font-weight: bold;"
        )
        main_layout.addWidget(self.axis_label)

        axis_layout = QtWidgets.QHBoxLayout()
        axis_layout.setSpacing(5)

        self.axis_buttons = {}

        for axis in ["x", "y", "z"]:

            button = QtWidgets.QPushButton(axis.upper())
            button.setCheckable(True)
            button.setMinimumHeight(32)

            axis_layout.addWidget(button)
            self.axis_buttons[axis] = button

        main_layout.addLayout(axis_layout)
        main_layout.addWidget(self._divider())

        # Keep on Top option
        self.top_checkbox = QtWidgets.QCheckBox("Keep on Top")
        self.top_checkbox.setStyleSheet(
            "color: #AAAAAA; font-size: 10px;"
        )

        main_layout.addWidget(self.top_checkbox)

        self.setStyleSheet("""
            QDialog {
                background-color: #292929;
                color: #DDDDDD;
            }

            QPushButton {
                background-color: #454545;
                color: #DDDDDD;
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                font-size: 11px;
            }

            QPushButton:hover {
                background-color: #555555;
            }

            QPushButton:checked {
                background-color: #397B58;
                border: 1px solid #55A879;
                color: white;
            }

            QPushButton:disabled {
                color: #666666;
                background-color: #333333;
            }

            QCheckBox {
                spacing: 6px;
            }
        """)

    # --------------------------------------------------------
    # Connections
    # --------------------------------------------------------

    def _connect_ui(self):

        for mode, button in self.mode_buttons.items():
            button.clicked.connect(
                lambda checked=False, m=mode: self.set_mode(m)
            )

        for axis, button in self.axis_buttons.items():
            button.clicked.connect(
                lambda checked=False, a=axis: self.set_axis(a)
            )

        self.top_checkbox.stateChanged.connect(
            self.toggle_keep_on_top
        )

    # --------------------------------------------------------
    # Helpers
    # --------------------------------------------------------

    def _divider(self):

        line = QtWidgets.QFrame()
        line.setFrameShape(QtWidgets.QFrame.HLine)
        line.setStyleSheet("color: #484848;")
        return line

    # --------------------------------------------------------
    # Keep on Top
    # --------------------------------------------------------

    def toggle_keep_on_top(self, state):

        if state == QtCore.Qt.Checked:

            # Raise above other Maya windows without setting
            # the global WindowStaysOnTopHint.
            self.raise_()
            self.activateWindow()

        else:

            # Return focus to Maya's normal window stacking.
            self.lower()

    # --------------------------------------------------------
    # Read Maya State
    # --------------------------------------------------------

    def get_maya_state(self):

        enabled = cmds.symmetricModelling(
            query=True,
            symmetry=True
        )

        about = cmds.symmetricModelling(
            query=True,
            about=True
        )

        axis = cmds.symmetricModelling(
            query=True,
            axis=True
        )

        if not enabled:
            return "off", axis

        about = str(about).lower()
        axis = str(axis).lower()

        if about in ("topo", "topology"):
            return "topo", axis

        if about == "object":
            return "object", axis

        if about == "world":
            return "world", axis

        return "off", axis

    # --------------------------------------------------------
    # Refresh Display
    # --------------------------------------------------------

    def refresh_state(self):

        try:
            mode, axis = self.get_maya_state()
            self.update_display(mode, axis)

        except Exception:
            self.state_label.setText("UNAVAILABLE")

    def update_display(self, mode, axis):

        if mode == "off":
            display = "OFF"
            color = "#777777"

        elif mode == "topo":
            display = "TOPOLOGY"
            color = "#D49A48"

        else:
            display = "{} {}".format(
                mode.upper(),
                axis.upper()
            )
            color = "#55B982"

        self.state_label.setText(display)

        self.state_label.setStyleSheet("""
            QLabel {
                background-color: #353535;
                color: %s;
                font-size: 22px;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px;
            }
        """ % color)

        for name, button in self.mode_buttons.items():
            button.setChecked(name == mode)

        for name, button in self.axis_buttons.items():
            button.setChecked(name == axis)

        axis_enabled = mode in ("object", "world")

        self.axis_label.setEnabled(axis_enabled)

        for button in self.axis_buttons.values():
            button.setEnabled(axis_enabled)

    # --------------------------------------------------------
    # Change Maya Mode
    # --------------------------------------------------------

    def set_mode(self, mode):

        try:

            if mode == "off":
                cmds.symmetricModelling(symmetry=0)

            elif mode == "topo":
                cmds.symmetricModelling(about="topo")
                cmds.symmetricModelling(symmetry=1)

            elif mode in ("object", "world"):
                cmds.symmetricModelling(about=mode)
                cmds.symmetricModelling(symmetry=1)

            self.refresh_state()

        except Exception as error:
            cmds.warning("Symmetry Monitor: {}".format(error))
            self.refresh_state()

    # --------------------------------------------------------
    # Change Axis
    # --------------------------------------------------------

    def set_axis(self, axis):

        try:
            cmds.symmetricModelling(axis=axis)
            self.refresh_state()

        except Exception as error:
            cmds.warning("Symmetry Monitor: {}".format(error))

    # --------------------------------------------------------
    # Cleanup
    # --------------------------------------------------------

    def closeEvent(self, event):

        self.timer.stop()
        super(_MayaSymmetryMonitor, self).closeEvent(event)


# ------------------------------------------------------------
# Launch Window
# ------------------------------------------------------------

try:
    if _mayaSymmetryMonitorWindow:
        _mayaSymmetryMonitorWindow.close()
        _mayaSymmetryMonitorWindow.deleteLater()
except:
    pass

_mayaSymmetryMonitorWindow = _MayaSymmetryMonitor()
_mayaSymmetryMonitorWindow.show()
_mayaSymmetryMonitorWindow.raise_()
