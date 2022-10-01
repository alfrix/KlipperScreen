import gi
import logging
import re
import contextlib

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from ks_includes.KlippyGcodes import KlippyGcodes
from ks_includes.screen_panel import ScreenPanel


def create_panel(*args):
    return FineTunePanel(*args)


class FineTunePanel(ScreenPanel):
    user_selecting = False

    bs = 0
    bs_delta = "0.05"
    bs_deltas = ["0.01", "0.05"]
    percent_delta = 1
    percent_deltas = ['1', '5', '10', '25']
    extrusion = 100
    speed = 100

    def initialize(self, panel_name):

        logging.debug("FineTunePanel")

        print_cfg = self._config.get_printer_config(self._screen.connected_printer)
        if print_cfg is not None:
            bs = print_cfg.get("z_babystep_values", "0.01, 0.05")
            if re.match(r'^[0-9,\.\s]+$', bs):
                bs = [str(i.strip()) for i in bs.split(',')]
                self.bs_deltas = bs if len(bs) <= 2 else [bs[0], bs[-1]]
                self.bs_delta = self.bs_deltas[0]

        # babystepping grid
        bsgrid = Gtk.Grid()
        for j, i in enumerate(self.bs_deltas):
            self.labels[i] = self._gtk.ToggleButton(i)
            self.labels[i].connect("clicked", self.change_bs_delta, i)
            ctx = self.labels[i].get_style_context()
            if j == 0:
                ctx.add_class("distbutton_top")
            elif j == len(self.bs_deltas) - 1:
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == self.bs_delta:
                ctx.add_class("distbutton_active")
            bsgrid.attach(self.labels[i], j, 0, 1, 1)
        # Grid for percentage
        deltgrid = Gtk.Grid()
        for j, i in enumerate(self.percent_deltas):
            self.labels[i] = self._gtk.ToggleButton(f"{i}%")
            self.labels[i].connect("clicked", self.change_percent_delta, i)
            ctx = self.labels[i].get_style_context()
            if j == 0:
                ctx.add_class("distbutton_top")
            elif j == len(self.percent_deltas) - 1:
                ctx.add_class("distbutton_bottom")
            else:
                ctx.add_class("distbutton")
            if i == "1":
                ctx.add_class("distbutton_active")
            deltgrid.attach(self.labels[i], j, 0, 1, 1)
        self.labels["1"].set_active(True)

        grid = self._gtk.HomogeneousGrid()
        grid.set_row_homogeneous(False)
        if self._screen.vertical_mode:
            self.labels['z+'] = self._gtk.ButtonImage("z-farther", _("Z+"), "color1")
            self.labels['z-'] = self._gtk.ButtonImage("z-closer", _("Z-"), "color1")
            self.labels['zoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color1", .6, Gtk.PositionType.LEFT, 1)

            self.labels['speed+'] = self._gtk.ButtonImage("speed+", _("Speed +"), "color3")
            self.labels['speed-'] = self._gtk.ButtonImage("speed-", _("Speed -"), "color3")
            self.labels['speedfactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                               "color3", .6, Gtk.PositionType.LEFT, 1)

            self.labels['extrude+'] = self._gtk.ButtonImage("flow+", _("Extrusion +"), "color4")
            self.labels['extrude-'] = self._gtk.ButtonImage("flow-", _("Extrusion -"), "color4")
            self.labels['extrudefactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                                 "color4", .6, Gtk.PositionType.LEFT, 1)

            grid.attach(self.labels['z+'], 0, 0, 1, 1)
            grid.attach(self.labels['z-'], 1, 0, 1, 1)
            grid.attach(self.labels['zoffset'], 2, 0, 1, 1)
            grid.attach(bsgrid, 0, 1, 3, 1)

            grid.attach(self.labels['speed-'], 0, 2, 1, 1)
            grid.attach(self.labels['speed+'], 1, 2, 1, 1)
            grid.attach(self.labels['speedfactor'], 2, 2, 1, 1)

            grid.attach(self.labels['extrude-'], 0, 3, 1, 1)
            grid.attach(self.labels['extrude+'], 1, 3, 1, 1)
            grid.attach(self.labels['extrudefactor'], 2, 3, 1, 1)
            grid.attach(deltgrid, 0, 4, 3, 1)
        else:
            self.labels['z+'] = self._gtk.ButtonImage("z-farther", _("Z+"), "color1")
            self.labels['zoffset'] = self._gtk.ButtonImage("refresh", "  0.00" + _("mm"),
                                                           "color1", .6, Gtk.PositionType.LEFT, 1)
            self.labels['z-'] = self._gtk.ButtonImage("z-closer", _("Z-"), "color1")

            self.labels['speed+'] = self._gtk.ButtonImage("speed+", _("Speed +"), "color3")
            self.labels['speedfactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                               "color3", .6, Gtk.PositionType.LEFT, 1)
            self.labels['speed-'] = self._gtk.ButtonImage("speed-", _("Speed -"), "color3")

            self.labels['extrude+'] = self._gtk.ButtonImage("flow+", _("Extrusion +"), "color4")
            self.labels['extrudefactor'] = self._gtk.ButtonImage("refresh", "  100%",
                                                                 "color4", .6, Gtk.PositionType.LEFT, 1)
            self.labels['extrude-'] = self._gtk.ButtonImage("flow-", _("Extrusion -"), "color4")
            grid.attach(self.labels['zoffset'], 0, 0, 1, 1)
            grid.attach(self.labels['z+'], 0, 1, 1, 1)
            grid.attach(self.labels['z-'], 0, 2, 1, 1)
            grid.attach(bsgrid, 0, 3, 1, 1)
            grid.attach(self.labels['speedfactor'], 1, 0, 1, 1)
            grid.attach(self.labels['speed+'], 1, 1, 1, 1)
            grid.attach(self.labels['speed-'], 1, 2, 1, 1)
            grid.attach(self.labels['extrudefactor'], 2, 0, 1, 1)
            grid.attach(self.labels['extrude+'], 2, 1, 1, 1)
            grid.attach(self.labels['extrude-'], 2, 2, 1, 1)
            grid.attach(deltgrid, 1, 3, 2, 1)

        self.labels['z+'].connect("clicked", self.change_babystepping, "+")
        self.labels['zoffset'].connect("clicked", self.change_babystepping, "reset")
        self.labels['z-'].connect("clicked", self.change_babystepping, "-")
        self.labels['speed+'].connect("clicked", self.change_speed, "+")
        self.labels['speedfactor'].connect("clicked", self.change_speed, "reset")
        self.labels['speed-'].connect("clicked", self.change_speed, "-")
        self.labels['extrude+'].connect("clicked", self.change_extrusion, "+")
        self.labels['extrudefactor'].connect("clicked", self.change_extrusion, "reset")
        self.labels['extrude-'].connect("clicked", self.change_extrusion, "-")

        self.content.add(grid)

    def process_update(self, action, data):

        if action != "notify_status_update":
            return

        if "gcode_move" in data:
            if "homing_origin" in data["gcode_move"]:
                self.labels['zoffset'].set_label(f'  {data["gcode_move"]["homing_origin"][2]:.2f}mm')
            if "extrude_factor" in data["gcode_move"]:
                self.extrusion = int(round(data["gcode_move"]["extrude_factor"] * 100))
                self.labels['extrudefactor'].set_label(f"  {self.extrusion:3}%")
            if "speed_factor" in data["gcode_move"]:
                self.speed = int(round(data["gcode_move"]["speed_factor"] * 100))
                self.labels['speedfactor'].set_label(f"  {self.speed:3}%")

    def change_babystepping(self, widget, direction):
        if direction == "reset":
            self.labels['zoffset'].set_label('  0.00mm')
            self._screen._ws.klippy.gcode_script("SET_GCODE_OFFSET Z=0 MOVE=1")
        elif direction in ["+", "-"]:
            with contextlib.suppress(KeyError):
                z_offset = float(self._printer.data["gcode_move"]["homing_origin"][2])
                if direction == "+":
                    z_offset += float(self.bs_delta)
                else:
                    z_offset -= float(self.bs_delta)
                self.labels['zoffset'].set_label(f'  {round(z_offset, 2):.2f}mm')
            self._screen._ws.klippy.gcode_script(f"SET_GCODE_OFFSET Z_ADJUST={direction}{self.bs_delta} MOVE=1")


    def change_bs_delta(self, widget, bs):
        if self.bs_delta == bs:
            return
        logging.info(f"### BabyStepping {bs}")

        ctx = self.labels[f"{self.bs_delta}"].get_style_context()
        ctx.remove_class("distbutton_active")

        self.bs_delta = bs
        ctx = self.labels[self.bs_delta].get_style_context()
        ctx.add_class("distbutton_active")
        for i in self.bs_deltas:
            if i == self.bs_delta:
                continue
            self.labels[i].set_active(False)

    def change_extrusion(self, widget, direction):
        if direction == "+":
            self.extrusion += int(self.percent_delta)
        elif direction == "-":
            self.extrusion -= int(self.percent_delta)
        elif direction == "reset":
            self.extrusion = 100

        self.extrusion = max(self.extrusion, 1)
        self.labels['extrudefactor'].set_label(f"  {self.extrusion:3}%")
        self._screen._ws.klippy.gcode_script(KlippyGcodes.set_extrusion_rate(self.extrusion))

    def change_speed(self, widget, direction):
        if direction == "+":
            self.speed += int(self.percent_delta)
        elif direction == "-":
            self.speed -= int(self.percent_delta)
        elif direction == "reset":
            self.speed = 100

        self.speed = max(self.speed, 1)
        self.labels['speedfactor'].set_label(f"  {self.speed:3}%")
        self._screen._ws.klippy.gcode_script(KlippyGcodes.set_speed_rate(self.speed))

    def change_percent_delta(self, widget, delta):
        if self.percent_delta == delta:
            return
        logging.info(f"### Delta {delta}")

        ctx = self.labels[f"{self.percent_delta}"].get_style_context()
        ctx.remove_class("distbutton_active")

        self.percent_delta = delta
        ctx = self.labels[self.percent_delta].get_style_context()
        ctx.add_class("distbutton_active")
        for i in self.percent_deltas:
            if i == self.percent_delta:
                continue
            self.labels[f"{i}"].set_active(False)
