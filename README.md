# Git in VS Code

## Face modeling toolset

Run this in Maya's **Python** Script Editor, with this repository's folder
on `sys.path` (use your local checkout path):

```python
import sys
import importlib

script_folder = r"D:\path\to\git-scripts"
if script_folder not in sys.path:
    sys.path.insert(0, script_folder)

import sculpt_falloff_switcher
import face_modeling_toolset
importlib.reload(sculpt_falloff_switcher)
importlib.reload(face_modeling_toolset)
face_modeling_toolset.show()
```

The panel provides Grab, Erase, Freeze, Smooth, Relax, and Wax in two rows.
Size and Intensity (Maya's sculpt strength) each have a slider and numeric field.
They read the active sculpt context every 200 ms, including changes made outside
the panel, and edit that context directly. Numeric fields accept values beyond
the initial slider range; the slider expands to include them. Brush controls
are disabled while a non-sculpt tool is active. Opening the panel does not
change the current tool or its settings.

Surface and Volume reuse `sculpt_falloff_switcher.set_falloff`; the original
standalone switcher remains available. Symmetry choices are **Off**, **World X**,
and **Object X**, using Maya's modeling symmetry settings. Selecting a symmetry
choice changes Maya's shared symmetry settings. Opening or closing the panel
does not reset them. If another symmetry axis is selected elsewhere, no X button
is highlighted until you choose one.

Requires Maya with the mesh sculpting tools and its bundled PySide6/shiboken6
or PySide2/shiboken2. No separate pip dependencies are needed.

### Manual verification in Maya

Select a polygon mesh and try each tool button. Change Size and Intensity in
the panel, then in Maya's Tool Settings or with brush shortcuts; confirm the
values follow in both directions. Switch to Move: brush controls should disable.
Test Surface/Volume against the original switcher. Test Off, World X, and
Object X on a rotated mesh to distinguish the two coordinate spaces. Close and
reopen/reload the panel and confirm only one panel remains.

The cloud editing environment does not run these scripts; GUI and sculpting
behavior must be checked in Maya.

---

Let's make some code changes.


Here is the code for Maya to see the new scripts 

import importlib
import sys

script_folder = r"D:\OneDrive - Full Sail University\CGA-3312\rigging_tools\git-scripts"

# I am including an addition variable to input the path for my home computer.
script_folder = r""

if script_folder not in sys.path:
    sys.path.insert(0, script_folder)



I removed a bunch of garbo text here and I am testing to see if the commit and syning system is working.
