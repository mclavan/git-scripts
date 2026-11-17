'''
import sculpt_falloff_switcher
sculpt_falloff_switcher.show()
'''
import maya.cmds as cmds


def set_falloff(value):
    """Set Surface (1) or Volume (2) on the active sculpt context.

    Shared by the original window and the face modeling panel.
    Raises RuntimeError when a sculpt tool is not active.
    """
    if value not in (1, 2):
        raise ValueError("Falloff must be Surface (1) or Volume (2).")
    context = cmds.currentCtx()
    cmds.sculptMeshCacheCtx(context, query=True, falloffType=True)
    cmds.sculptMeshCacheCtx(context, edit=True, falloffType=value)


def show():
    window_name = "sculptFalloffSwitcherWindow"

    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)

    def change_falloff(value):
        try:
            set_falloff(value)

            cmds.text(
                "falloffStatus",
                edit=True,
                label="Current Mode: " +
                ("Surface" if value == 1 else "Volume")
            )

        except RuntimeError:
            cmds.warning(
                "Please activate a Sculpting Tool first."
            )

    cmds.window(
        window_name,
        title="Sculpt Falloff Switcher",
        sizeable=False,
        widthHeight=(230, 85)
    )

    cmds.columnLayout(
        adjustableColumn=True,
        rowSpacing=8,
        columnOffset=("both", 8)
    )

    cmds.rowLayout(
        numberOfColumns=2,
        adjustableColumn=1,
        columnWidth2=(105, 105),
        columnAttach=[(1, "both", 2), (2, "both", 2)]
    )

    cmds.button(
        label="Surface",
        height=35,
        command=lambda *_: change_falloff(1)
    )

    cmds.button(
        label="Volume",
        height=35,
        command=lambda *_: change_falloff(2)
    )

    cmds.setParent("..")

    cmds.text(
        "falloffStatus",
        label="Select a falloff mode",
        height=25
    )

    cmds.showWindow(window_name)
