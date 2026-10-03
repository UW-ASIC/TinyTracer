"""
LibreLane plugin: power the IHP scene SRAM macro from the tile's Metal4 stripes.

The Tiny Tapeout SG13CMOS5L tile has a Metal4-only PDN, and the SRAM blocks
Metal2-Metal4 over its footprint, so pdngen's stripes stop at the macro and
never reach its Metal4 supply columns (VDD!, VDDARRAY!, VSS!). The
Project.ExtendPowerStripes step runs odb_stripes.py after GeneratePDN, which
redraws the stripes through the macro on its own supply columns.

LibreLane imports every module on the Python path whose name starts with
``librelane_plugin_``. Both the Tiny Tapeout GDS action and a local
``tt_tool.py --harden`` run LibreLane from the repository root, so this file
is found without installing anything. src/config.json inserts the step with:

    "meta": { "substituting_steps": { "+OpenROAD.GeneratePDN": "Project.ExtendPowerStripes" } }

Adapted from kdp1965/ihp-um-janestreet-prism (librelane_plugin_prism_pdn.py)
and WilliamZhang20/protocol-emulator (librelane_plugin_sram_pdn.py), both
Apache-2.0.
"""
import json as _json
import os
import re as _re
import types as _types
from decimal import Decimal
from typing import Optional

import librelane.steps.netgen as _netgen
from librelane.config import Variable
from librelane.steps import Step
from librelane.steps.odb import OdbpyStep

HERE = os.path.dirname(os.path.abspath(__file__))


@Step.factory.register()
class ExtendPowerStripes(OdbpyStep):
    id = "Project.ExtendPowerStripes"
    name = "Extend Power Stripes Over the SRAM"

    def get_script_path(self):
        return os.path.join(HERE, "odb_stripes.py")

    config_vars = [
        Variable("EXTEND_STRIPES_LAYER", str, "The tile's vertical single-layer PDN layer.", default="Metal4"),
        Variable("EXTEND_STRIPES_SRAM_LAYER", Optional[str], "Layer of the SRAM power columns when it differs from the stripe layer.", default=None),
        Variable("EXTEND_STRIPES_CLEARANCE", Decimal, "Spacing kept between a drawn stripe and the other net's macro rails or tile pins.", units="µm", default=Decimal("0.24")),
        Variable("EXTEND_STRIPES_STACK_PITCH", Decimal, "Spacing of the via stacks along an SRAM power column.", units="µm", default=Decimal("10")),
        Variable("EXTEND_STRIPES_PIN_FACE_MARGIN", Decimal, "No rail via stack within this distance of a macro edge that carries pins.", units="µm", default=Decimal("3")),
        Variable("EXTEND_STRIPES_SRAM_ALL_COLUMNS", bool, "Put a stripe on every legal supply column of the SRAM.", default=False),
        Variable("EXTEND_STRIPES_SRAM_ARRAY_EVERY_OTHER", bool, "Add a VPWR/VGND pair on every other pair position of each bit-cell array.", default=False),
    ]

    def get_command(self):
        cmd = super().get_command() + [
            "--layer", self.config["EXTEND_STRIPES_LAYER"],
            "--clearance", str(self.config["EXTEND_STRIPES_CLEARANCE"]),
            "--stack-pitch", str(self.config["EXTEND_STRIPES_STACK_PITCH"]),
            "--pin-face-margin", str(self.config["EXTEND_STRIPES_PIN_FACE_MARGIN"]),
        ]
        if self.config.get("EXTEND_STRIPES_SRAM_LAYER"):
            cmd += ["--sram-layer", self.config["EXTEND_STRIPES_SRAM_LAYER"]]
        cmd += ["--sram-all-columns" if self.config["EXTEND_STRIPES_SRAM_ALL_COLUMNS"] else "--sram-grid-columns"]
        if self.config["EXTEND_STRIPES_SRAM_ARRAY_EVERY_OTHER"]:
            cmd += ["--sram-array-every-other"]
        return cmd


# netgen writes the SRAM's power pin names (VDD!, VSS!, VDDARRAY!) into its
# LVS JSON with a stray backslash ("\VDD!"), which is not a valid JSON escape,
# so librelane.steps.netgen.LVS dies in json.loads before the LVS checker runs.
_BAD_ESCAPE = _re.compile(r'\\(\\|[^"\\/bfnrtu])')


def _repair_escapes(s):
    return _BAD_ESCAPE.sub(
        lambda m: '\\\\' if m.group(1) == '\\' else '\\\\' + m.group(1), s
    )


def _loads_repairing_escapes(s, *args, **kwargs):
    try:
        return _json.loads(s, *args, **kwargs)
    except _json.JSONDecodeError:
        return _json.loads(_repair_escapes(s), *args, **kwargs)


_netgen.json = _types.SimpleNamespace(
    loads=_loads_repairing_escapes,
    load=_json.load,
    dumps=_json.dumps,
    dump=_json.dump,
    JSONDecodeError=_json.JSONDecodeError,
)
