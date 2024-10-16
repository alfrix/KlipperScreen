import datetime
import gi
import logging
import math

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango


class HeaterGraph(Gtk.DrawingArea):
    def __init__(self, printer):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.get_style_context().add_class('heatergraph')
        self.printer = printer
        self.store = {}
        self.max_length = 0
        self.connect('draw', self.draw_graph)
        self.add_events(Gdk.EventMask.TOUCH_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('touch-event', self.event_cb)
        self.connect('button_press_event', self.event_cb)

    def add_object(self, name, type, rgb=[0, 0, 0], dashed=False, fill=False):
        if name not in self.store:
            self.store.update({name: {"show": True}})
        self.store[name].update({type: {
            "dashed": dashed,
            "fill": fill,
            "rgb": rgb
        }})
        self.max_length = max(self.max_length, len(self.printer.get_temp_store(name, type)))

    def event_cb(self, da, ev):
        if ev.get_source_device().get_source() == Gdk.InputSource.MOUSE:
            if ev.type == Gdk.EventType.BUTTON_PRESS:
                x = ev.x
                y = ev.y
                # logging.info("Drawing area clicked: %s %s" % (x, y))

        if ev.get_source_device().get_source() == Gdk.InputSource.TOUCHSCREEN:
            if ev.touch.type == Gdk.EventType.TOUCH_BEGIN:
                x = ev.touch.x
                y = ev.touch.y
                # logging.info("Drawing area clicked: %s %s" % (x, y))


    def get_max_length(self):
        n = []
        for name in self.store:
            if "temperatures" not in self.store[name]:
                continue
            n.append(len(self.printer.get_temp_store(name, "temperatures")))
        return max(n)

    def get_max_num(self, data_points=0):
        mnum = []
        for x in self.store:
            for t in self.store[x]:
                if t == "show":
                    continue
                mnum.append(max(self.printer.get_temp_store(x, t, data_points)))
        return max(mnum)

    def draw_graph(self, da, ctx):
        width = da.get_allocated_width()
        height = da.get_allocated_height()

        g_width_start = 30
        g_width = width - 15
        g_height_start = 15
        g_height = height - 30

        ctx.set_source_rgb(.5, .5, .5)
        ctx.set_line_width(1)
        ctx.set_tolerance(0.1)

        ctx.move_to(g_width_start, g_height_start)
        ctx.line_to(g_width, g_height_start)
        ctx.line_to(g_width, g_height)
        ctx.line_to(g_width_start, g_height)
        ctx.line_to(g_width_start, g_height_start)
        ctx.stroke()

        ctx.set_source_rgb(1, 0, 0)
        ctx.move_to(g_width_start, height)

        gsize = [
            [g_width_start, g_height_start],
            [g_width, g_height]
        ]

        self.max_length = self.get_max_length()
        graph_width = gsize[1][0] - gsize[0][0]
        points_per_pixel = self.max_length / graph_width
        if points_per_pixel > 3:
            points_per_pixel = 3
        data_points = int(round(graph_width * points_per_pixel, 0))
        max_num = math.ceil(self.get_max_num(data_points) * 1.1 / 10) * 10
        d_width = 1 / points_per_pixel


        d_height_scale = self.graph_lines(ctx, gsize, max_num)
        self.graph_time(ctx, gsize, points_per_pixel)

        for name in self.store:
            if not self.store[name]['show']:
                continue
            for type in self.store[name]:
                d = self.printer.get_temp_store(name, type, data_points)
                if d is False:
                    continue
                self.graph_data(ctx, d, gsize, d_height_scale, d_width, self.store[name][type]["rgb"],
                                self.store[name][type]["dashed"], self.store[name][type]["fill"])

    def graph_data(self, ctx, data, gsize, hscale, swidth, rgb, dashed=False, fill=False):
        i = 0
        ctx.set_source_rgba(rgb[0], rgb[1], rgb[2], 1)
        ctx.move_to(gsize[0][0] + 1, gsize[0][1] - 1)
        if dashed:
            ctx.set_dash([10, 5])
        else:
            ctx.set_dash([1, 0])
        d_len = len(data) - 1
        for d in data:
            p_x = i*swidth + gsize[0][0] if i != d_len else gsize[1][0] - 1
            p_y = gsize[1][1] - 1 - (d*hscale)
            if i == 0:
                ctx.move_to(gsize[0][0]+1, p_y)
                i += 1
                continue
            ctx.line_to(p_x, p_y)
            i += 1
        if fill is False:
            ctx.stroke()
            return

        ctx.stroke_preserve()
        ctx.line_to(gsize[1][0] - 1, gsize[1][1] - 1)
        ctx.line_to(gsize[0][0] + 1, gsize[1][1] - 1)
        if fill:
            ctx.set_source_rgba(rgb[0], rgb[1], rgb[2], .1)
            ctx.fill()

    def graph_lines(self, ctx, gsize, max_num):
        if max_num <= 30:
            nscale = 5
        elif max_num <= 60:
            nscale = 10
        elif max_num <= 130:
            nscale = 25
        else:
            nscale = 50
        # nscale = math.floor((max_num / 10) / 4) * 10
        r = int(max_num/nscale) + 1
        hscale = (gsize[1][1] - gsize[0][1]) / (r * nscale)

        for i in range(r):
            ctx.set_source_rgb(.5, .5, .5)
            lheight = gsize[1][1] - nscale*i*hscale
            ctx.move_to(6, lheight + 3)
            ctx.show_text(str(nscale*i).rjust(3, " "))
            ctx.stroke()
            ctx.set_source_rgba(.5, .5, .5, .2)
            ctx.move_to(gsize[0][0], lheight)
            ctx.line_to(gsize[1][0], lheight)
            ctx.stroke()
        return hscale

    def graph_time(self, ctx, gsize, points_per_pixel):
        glen = gsize[1][0] - gsize[0][0]

        now = datetime.datetime.now()
        first = gsize[1][0] - ((now.second + ((now.minute % 2) * 60)) / points_per_pixel)
        steplen = 120 / points_per_pixel  # For 120s
        i = 0
        while True:
            x = first - i*steplen
            if x < gsize[0][0]:
                break
            ctx.set_source_rgba(.5, .5, .5, .2)
            ctx.move_to(x, gsize[0][1])
            ctx.line_to(x, gsize[1][1])
            ctx.stroke()

            ctx.set_source_rgb(.5, .5, .5)
            ctx.move_to(x - 15, gsize[1][1] + 15)

            hour = now.hour
            min = now.minute - (now.minute % 2) - i*2
            if min < 0:
                hour -= 1
                min = 60 + min
                if hour < 0:
                    hour += 24

            ctx.show_text("%02d:%02d" % (hour, min))
            ctx.stroke()
            i += 1

    def is_showing(self, device):
        if device not in self.store:
            return False
        return self.store[device]['show']

    def set_showing(self, device, show=True):
        if device not in self.store:
            return
        self.store[device]['show'] = show
