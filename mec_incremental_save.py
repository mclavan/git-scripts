r"""MEC Incremental Save

Run:
    In Maya, open Windows > General Editors > Script Editor. In a Python tab,
    run:

        import mec_incremental_save
        mec_incremental_save.show_window()

    Use the tool window's Shelf menu to add four buttons to the selected Maya
    shelf.

Reload after editing (Python 3):
    import importlib
    import mec_incremental_save
    importlib.reload(mec_incremental_save)
    mec_incremental_save.show_window()

Shelf buttons: Open tool, Incremental Save, Incremental Save With Note,
and Complete Process.

Use the Starting Point fields for the initial save:
    asset_processNumber_processName_count_optionalNote.ma
Choose a folder, fill in the fields, and click Save Starting Point. Use
Incremental Save With Note when you want to enter a note for that save.
"""

import os
import re

import maya.cmds as cmds


_WINDOW_NAME = "mecIncrementalSaveWindow"
_START_FIELDS = {
    "asset": "mecIncrementalSaveAsset",
    "process_number": "mecIncrementalSaveProcessNumber",
    "process_name": "mecIncrementalSaveProcessName",
    "count": "mecIncrementalSaveCount",
    "directory": "mecIncrementalSaveDirectory",
}
_NAME_PATTERN = re.compile(
    r"^(?P<asset>[A-Za-z0-9-]+)_(?P<process_number>\d+)_"
    r"(?P<process_name>[A-Za-z0-9-]+)_(?P<count>\d+)"
    r"(?:_(?P<note>[A-Za-z0-9-]+))?$"
)


def _parse_scene_name(scene_path):
    if not scene_path:
        return None

    name, extension = os.path.splitext(os.path.basename(scene_path))
    if extension.lower() != ".ma":
        return None

    match = _NAME_PATTERN.match(name)
    if not match:
        return None

    return {
        "asset": match.group("asset"),
        "process_number": int(match.group("process_number")),
        "process_name": match.group("process_name"),
        "count": int(match.group("count")),
        "directory": os.path.dirname(scene_path),
    }


def _prompt_component(title, message):
    result = cmds.promptDialog(
        title=title,
        message=message,
        button=["OK", "Cancel"],
        defaultButton="OK",
        cancelButton="Cancel",
        dismissString="Cancel",
    )
    if result != "OK":
        return None

    value = cmds.promptDialog(query=True, text=True).strip()
    if not value:
        cmds.warning("A value is required.")
        return None
    value = re.sub(r"[^A-Za-z0-9-]+", "-", value).strip("-")
    if not value:
        cmds.warning("Use at least one letter or number.")
        return None
    return value


def _prompt_save_note():
    result = cmds.promptDialog(
        title="Save With Note",
        message="Enter a note to append to this save:",
        button=["Save", "Cancel"],
        defaultButton="Save",
        cancelButton="Cancel",
        dismissString="Cancel",
    )
    if result != "Save":
        return None

    note = cmds.promptDialog(query=True, text=True).strip()
    if not note:
        cmds.warning("Enter a note or cancel the save.")
        return None
    return re.sub(r"[^A-Za-z0-9-]+", "-", note).strip("-")


def _build_filename(asset, process_number, process_name, count, note=""):
    filename = "{}_{:02d}_{}_{:02d}".format(
        asset, process_number, process_name, count
    )
    if note:
        filename += "_" + note
    return filename + ".ma"


def _filename_component(value, label):
    value = value.strip()
    if not re.fullmatch(r"[A-Za-z0-9-]+", value):
        cmds.warning(
            "{} must contain only letters, numbers, and hyphens.".format(label)
        )
        return None
    return value


def _save_as(path):
    if os.path.exists(path):
        cmds.warning("Refusing to overwrite an existing scene: {}".format(path))
        return False

    previous_scene_path = cmds.file(query=True, sceneName=True)
    cmds.file(rename=path)
    try:
        cmds.file(save=True, type="mayaAscii")
    except Exception:
        if previous_scene_path:
            cmds.file(rename=previous_scene_path)
        raise
    return True


def _next_count(data):
    highest_count = data["count"]
    for filename in os.listdir(data["directory"]):
        base_name, extension = os.path.splitext(filename)
        if extension.lower() != ".ma":
            continue
        match = _NAME_PATTERN.match(base_name)
        if match and (
            match.group("asset") == data["asset"]
            and int(match.group("process_number")) == data["process_number"]
            and match.group("process_name") == data["process_name"]
        ):
            highest_count = max(highest_count, int(match.group("count")))
    return highest_count + 1


def _choose_starting_folder(*_):
    current = cmds.textField(_START_FIELDS["directory"], query=True, text=True)
    folder = cmds.fileDialog2(
        fileMode=3,
        caption="Choose a folder for versioned Maya scenes",
        startingDirectory=current or cmds.workspace(query=True, rootDirectory=True),
    )
    if folder:
        cmds.textField(_START_FIELDS["directory"], edit=True, text=folder[0])


def save_starting_point(*_):
    """Save the initial version using the Starting Point fields."""
    asset = _filename_component(
        cmds.textFieldGrp(_START_FIELDS["asset"], query=True, text=True), "Asset"
    )
    process_name = _filename_component(
        cmds.textFieldGrp(
            _START_FIELDS["process_name"], query=True, text=True
        ),
        "Process name",
    )
    if asset is None or process_name is None:
        return

    process_number_text = cmds.textFieldGrp(
        _START_FIELDS["process_number"], query=True, text=True
    ).strip()
    count_text = cmds.textFieldGrp(
        _START_FIELDS["count"], query=True, text=True
    ).strip()
    if not process_number_text.isdigit() or int(process_number_text) < 1:
        cmds.warning("Process number must be a positive whole number.")
        return
    if not count_text.isdigit() or int(count_text) < 1:
        cmds.warning("Count must be a positive whole number.")
        return

    directory = cmds.textField(
        _START_FIELDS["directory"], query=True, text=True
    ).strip()
    if not directory or not os.path.isdir(directory):
        cmds.warning("Choose an existing folder for the versioned scene.")
        return

    target = os.path.join(
        directory,
        _build_filename(
            asset, int(process_number_text), process_name, int(count_text)
        ),
    )
    if _save_as(target):
        cmds.inViewMessage(
            amg="Saved <hl>{}</hl>".format(os.path.basename(target)),
            pos="topCenter",
            fade=True,
        )


def incremental_save(note=""):
    """Save the next count for the current process."""
    scene_path = cmds.file(query=True, sceneName=True)
    data = _parse_scene_name(scene_path)

    if data is None:
        if note:
            cmds.warning(
                "Save a starting point first, then use Incremental Save With Note."
            )
            return
        save_starting_point()
        return

    asset = data["asset"]
    process_number = data["process_number"]
    process_name = data["process_name"]
    count = _next_count(data)
    directory = data["directory"]
    target = os.path.join(
        directory,
        _build_filename(asset, process_number, process_name, count, note),
    )
    if _save_as(target):
        cmds.inViewMessage(
            amg="Saved <hl>{}</hl>".format(os.path.basename(target)),
            pos="topCenter",
            fade=True,
        )


def incremental_save_with_note(*_):
    """Prompt for a note, then save the next count."""
    note = _prompt_save_note()
    if note is None:
        return
    if not note:
        cmds.warning("The note must contain at least one letter or number.")
        return
    incremental_save(note=note)


def complete_process():
    """Start the next process number at count 01."""
    scene_path = cmds.file(query=True, sceneName=True)
    data = _parse_scene_name(scene_path)
    if data is None:
        cmds.warning(
            "Save a scene named asset_processNumber_processName_count.ma "
            "before completing a process."
        )
        return

    next_process_name = _prompt_component(
        "Complete Process",
        "Name for process {:02d}:".format(data["process_number"] + 1),
    )
    if next_process_name is None:
        return
    target = os.path.join(
        data["directory"],
        _build_filename(
            data["asset"],
            data["process_number"] + 1,
            next_process_name,
            1,
        ),
    )
    if _save_as(target):
        cmds.inViewMessage(
            amg="Started process <hl>{}</hl>".format(os.path.basename(target)),
            pos="topCenter",
            fade=True,
        )


def create_shelf_buttons(*_):
    """Add or replace this tool's four buttons on the selected shelf."""
    shelf = cmds.shelfTabLayout("ShelfLayout", query=True, selectTab=True)
    if not shelf or not cmds.shelfLayout(shelf, exists=True):
        cmds.warning("Select a Maya shelf before creating MEC shelf buttons.")
        return

    buttons = [
        (
            "incWin",
            "mecIncrementalSave:open",
            "import mec_incremental_save as mec; mec.show_window()",
        ),
        (
            "save",
            "mecIncrementalSave:increment",
            "import mec_incremental_save as mec; mec.incremental_save()",
        ),
        (
            "saveNote",
            "mecIncrementalSave:incrementWithNote",
            "import mec_incremental_save as mec; mec.incremental_save_with_note()",
        ),
        (
            "process",
            "mecIncrementalSave:completeProcess",
            "import mec_incremental_save as mec; mec.complete_process()",
        ),
    ]
    managed_annotations = {item[1] for item in buttons}
    for child in cmds.shelfLayout(shelf, query=True, childArray=True) or []:
        if cmds.objectTypeUI(child) != "shelfButton":
            continue
        annotation = cmds.shelfButton(child, query=True, annotation=True)
        if annotation in managed_annotations:
            cmds.deleteUI(child)

    for label, annotation, command in buttons:
        cmds.shelfButton(
            parent=shelf,
            label=label,
            imageOverlayLabel=label,
            annotation=annotation,
            image="addCreateGeneric_100.png",
            sourceType="python",
            command=command,
        )


def show_window():
    """Display the incremental-save controls."""
    if cmds.window(_WINDOW_NAME, exists=True):
        cmds.deleteUI(_WINDOW_NAME)

    scene_path = cmds.file(query=True, sceneName=True)
    start_directory = (
        os.path.dirname(scene_path)
        if scene_path
        else cmds.workspace(query=True, rootDirectory=True)
    )
    window = cmds.window(
        _WINDOW_NAME,
        title="MEC Incremental Save",
        sizeable=True,
        menuBar=True,
        widthHeight=(360, 390),
    )
    shelf_menu = cmds.menu(label="Shelf")
    cmds.menuItem(
        label="Add Buttons to Selected Shelf",
        parent=shelf_menu,
        command=create_shelf_buttons,
    )
    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=6,
        columnAttach=("both", 8),
    )
    cmds.frameLayout(label="Starting Point", collapsable=True, marginWidth=6)
    cmds.columnLayout(adjustableColumn=True, rowSpacing=4)
    cmds.textFieldGrp(
        _START_FIELDS["asset"], label="Asset", text="", columnWidth=(1, 110)
    )
    cmds.textFieldGrp(
        _START_FIELDS["process_number"],
        label="Process number",
        text="01",
        columnWidth=(1, 110),
    )
    cmds.textFieldGrp(
        _START_FIELDS["process_name"],
        label="Process name",
        text="setup",
        columnWidth=(1, 110),
    )
    cmds.textFieldGrp(
        _START_FIELDS["count"], label="Count", text="01", columnWidth=(1, 110)
    )
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1, columnWidth2=(245, 90))
    cmds.textField(_START_FIELDS["directory"], text=start_directory)
    cmds.button(label="Browse...", command=_choose_starting_folder)
    cmds.setParent("..")
    cmds.button(
        label="Save Starting Point",
        height=30,
        command=save_starting_point,
    )
    cmds.setParent("..")
    cmds.setParent("..")
    cmds.separator(height=8, style="in")
    cmds.rowLayout(numberOfColumns=2, adjustableColumn=1)
    cmds.button(
        label="Incremental Save",
        height=32,
        command=lambda *_: incremental_save(),
    )
    cmds.button(
        label="Incremental Save With Note...",
        height=32,
        command=incremental_save_with_note,
    )
    cmds.setParent("..")
    cmds.button(
        label="Complete Process",
        height=32,
        command=lambda *_: complete_process(),
    )
    cmds.showWindow(window)


if __name__ == "__main__":
    show_window()