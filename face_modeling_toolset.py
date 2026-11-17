"""Face sculpting panel for Maya.

To open the panel, run this in Maya's Python Script Editor (not MEL).
Change script_folder if this repository is in a different location:

    import sys
    import importlib

    script_folder = r"D:\OneDrive - Full Sail University\CGA-3312\rigging_tools\git-scripts"
    if script_folder not in sys.path:
        sys.path.insert(0, script_folder)

    import sculpt_falloff_switcher
    import face_modeling_toolset
    importlib.reload(sculpt_falloff_switcher)
    importlib.reload(face_modeling_toolset)
    face_modeling_toolset.show()

Keep sculpt_falloff_switcher.py in the same folder as this file.
"""

from functools import partial
import math

import maya.cmds as cmds
import maya.OpenMayaUI as omui
import sculpt_falloff_switcher

try:
    from PySide6 import QtCore, QtWidgets
    import shiboken6 as shiboken
except ImportError:
    from PySide2 import QtCore, QtWidgets
    import shiboken2 as shiboken


TOOLS = ("Grab", "Erase", "Freeze", "Smooth", "Relax", "Wax")
_window = None


def _blocked(widget, callback):
    blocker = QtCore.QSignalBlocker(widget)
    callback()
    del blocker


class BrushControl(QtWidgets.QWidget):
    """Slider with an exact numeric field; reading Maya never writes back."""

    changed = QtCore.Signal(float)

    def __init__(self, label, maximum):
        super().__init__()
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        title = QtWidgets.QLabel(label)
        title.setFixedWidth(58)
        layout.addWidget(title)
        self.slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.slider.setRange(0, 1000)
        layout.addWidget(self.slider, 1)
        self.field = QtWidgets.QDoubleSpinBox()
        self.field.setDecimals(4)
        self.field.setRange(0.0, 1000000000.0)
        self.field.setSingleStep(0.01 if label == "Intensity" else 0.1)
        self.field.setKeyboardTracking(False)
        self.field.setFixedWidth(92)
        layout.addWidget(self.field)
        self.maximum = maximum
        self.slider.valueChanged.connect(self._slide)
        self.field.valueChanged.connect(self._type)

    def _slide(self, value):
        value = value * self.maximum / 1000.0
        _blocked(self.field, lambda: self.field.setValue(value))
        self.changed.emit(value)

    def _type(self, value):
        self.set_value(value)
        self.changed.emit(value)

    def set_value(self, value):
        if not math.isfinite(value):
            return
        self.maximum = max(self.maximum, value)
        _blocked(self.slider, lambda: self.slider.setValue(
            round(value / self.maximum * 1000)))
        # Do not interrupt a numeric entry or an ongoing slider drag.
        if not self.field.hasFocus():
            _blocked(self.field, lambda: self.field.setValue(value))

    def busy(self):
        return self.slider.isSliderDown() or self.field.hasFocus()


class FaceModelingPanel(QtWidgets.QDialog):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName("faceModelingToolset")
        self.setWindowTitle("Face Modeling")
        self.setMinimumWidth(360)
        self.setStyleSheet("""
            QDialog { background: #292c31; }
            QLabel { color: #d9dce2; }
            QPushButton { background: #3c4149; color: #e5e9ee;
                border: 1px solid #515761; border-radius: 5px; padding: 8px; }
            QPushButton:checked { background: #3d7077; border-color: #73b6bd; }
            QPushButton:hover { border-color: #9ca8b7; }
            QPushButton:disabled { color: #737982; }
            QGroupBox { color: #b5beca; border: 1px solid #464c55;
                border-radius: 5px; margin-top: 10px; padding-top: 12px; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; }
        """)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(12)
        heading = QtWidgets.QLabel("FACE  /  SCULPT")
        layout.addWidget(heading)
        self.status = QtWidgets.QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        grid = QtWidgets.QGridLayout()
        self.tools = {}
        for index, name in enumerate(TOOLS):
            button = QtWidgets.QPushButton(name)
            button.setMinimumHeight(48)
            button.setCheckable(True)
            button.clicked.connect(partial(self.activate, name))
            grid.addWidget(button, index // 3, index % 3)
            self.tools[name.lower()] = button
        layout.addLayout(grid)
        self.size = BrushControl("Size", 10.0)
        self.intensity = BrushControl("Intensity", 1.0)
        layout.addWidget(self.size)
        layout.addWidget(self.intensity)
        self.size.changed.connect(partial(self.edit_brush, "size"))
        self.intensity.changed.connect(partial(self.edit_brush, "strength"))
        falloff = QtWidgets.QGroupBox("Falloff")
        row = QtWidgets.QHBoxLayout(falloff)
        self.falloff = {}
        # Use the same values and operation as the existing switcher.
        for title, value in (("Surface", 1), ("Volume", 2)):
            button = QtWidgets.QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(partial(self.set_falloff, value))
            row.addWidget(button)
            self.falloff[value] = button
        layout.addWidget(falloff)
        self.mode = QtWidgets.QLabel("Mode: —")
        layout.addWidget(self.mode)
        symmetry = QtWidgets.QGroupBox("Symmetry")
        row = QtWidgets.QHBoxLayout(symmetry)
        self.symmetry = {}
        for title in ("Off", "World X", "Object X"):
            button = QtWidgets.QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(partial(self.set_symmetry, title))
            row.addWidget(button)
            self.symmetry[title] = button
        layout.addWidget(symmetry)
        shape_editor_button = QtWidgets.QPushButton("Open Shape Editor")
        shape_editor_button.clicked.connect(self.open_shape_editor)
        layout.addWidget(shape_editor_button)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.refresh)
        self.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start()
        self.refresh()

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)

    def sculpt_context(self):
        context = cmds.currentCtx()
        # Query only: never create or activate a context during synchronization.
        cmds.sculptMeshCacheCtx(context, query=True, size=True)
        return context

    def activate(self, name, *_):
        try:
            getattr(cmds, "SetMesh{}Tool".format(name))()
        except (RuntimeError, AttributeError) as error:
            cmds.warning("Could not activate {}: {}".format(name, error))
        self.refresh()

    def edit_brush(self, flag, value):
        try:
            context = self.sculpt_context()
            cmds.sculptMeshCacheCtx(context, edit=True, **{flag: value})
        except RuntimeError as error:
            cmds.warning(str(error))
        self.refresh()

    def set_falloff(self, value, *_):
        try:
            sculpt_falloff_switcher.set_falloff(value)
        except RuntimeError as error:
            cmds.warning(str(error))
        self.refresh()

    def set_symmetry(self, title, *_):
        try:
            if title == "Off":
                cmds.symmetricModelling(edit=True, symmetry=False)
            else:
                cmds.symmetricModelling(edit=True, axis="x",
                                        about=title.split()[0].lower(),
                                        symmetry=True)
        except RuntimeError as error:
            cmds.warning(str(error))
        self.refresh()

    def open_shape_editor(self, *_):
        mel.eval('tearOffPanel "Shape Editor" "shapePanel" false;')

    def refresh(self):
        try:
            context = self.sculpt_context()
            mode = cmds.sculptMeshCacheCtx(context, query=True, mode=True)
        except RuntimeError:
            context, mode = None, ""
        for name, button in self.tools.items():
            button.setChecked(str(mode).lower() == name)
        for control, flag in ((self.size, "size"),
                              (self.intensity, "strength")):
            control.setEnabled(context is not None)
            if context and not control.busy():
                try:
                    value = cmds.sculptMeshCacheCtx(context, query=True,
                                                    **{flag: True})
                    control.set_value(float(value))
                except (RuntimeError, TypeError, ValueError):
                    control.setEnabled(False)
        falloff = None
        if context:
            try:
                falloff = cmds.sculptMeshCacheCtx(context, query=True,
                                                 falloffType=True)
            except RuntimeError:
                pass
        for value, button in self.falloff.items():
            button.setEnabled(falloff is not None)
            button.setChecked(value == falloff)
        names = {1: "Surface", 2: "Volume"}
        self.mode.setText("Mode: " + names.get(falloff, "—"))
        try:
            enabled = cmds.symmetricModelling(query=True, symmetry=True)
            axis = cmds.symmetricModelling(query=True, axis=True)
            space = cmds.symmetricModelling(query=True, about=True)
            selected = "Off" if not enabled else (
                space.title() + " X" if axis.lower() == "x" else "")
            for title, button in self.symmetry.items():
                button.setChecked(title == selected)
                button.setEnabled(True)
        except RuntimeError:
            for button in self.symmetry.values():
                button.setChecked(False)
                button.setEnabled(False)
        self.status.setText("Active tool: {}".format(mode) if context else
                            "Select a mesh and choose a sculpt tool.")


def show():
    """Open one panel; safely replace an older instance after module reload."""
    global _window
    pointer = omui.MQtUtil.mainWindow()
    if not pointer:
        raise RuntimeError("Open this panel inside Maya's graphical interface.")
    parent = shiboken.wrapInstance(int(pointer), QtWidgets.QWidget)
    for child in parent.findChildren(QtWidgets.QDialog):
        if child.objectName() == "faceModelingToolset":
            child.close()
            child.deleteLater()
    _window = FaceModelingPanel(parent)
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
