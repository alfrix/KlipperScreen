import logging
import json
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk
from jinja2 import Template
from ks_includes.screen_panel import ScreenPanel


class Panel(ScreenPanel):
    j2_data = None

    def __init__(self, screen, title, items=None):
        super().__init__(screen, title)
        self.menu_callbacks = {}  # Happy Hare
        self.items = items
        self.create_menu_items()
        self.grid = self._gtk.HomogeneousGrid()
        self.scroll = self._gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

    def activate(self):
        self.add_content()

    def add_content(self):
        for child in self.scroll.get_children():
            self.scroll.remove(child)
        if self._screen.vertical_mode:
            self.scroll.add(self.arrangeMenuItems(self.items, 3))
        else:
            self.scroll.add(self.arrangeMenuItems(self.items, 4))
        if not self.content.get_children():
            self.content.add(self.scroll)

    def process_update(self, action, data):
        if action != "notify_status_update":
            return

        # Happy Hare vvv
        unique_cbs = []
        for x in data:
            for i in data[x]:
                if ("printer.%s.%s" % (x, i)) in self.menu_callbacks:
                    for cb in self.menu_callbacks["printer.%s.%s" % (x, i)]:
                        if cb not in unique_cbs:
                            unique_cbs.append(cb)

        # Call specific associated callbacks
        for cb in unique_cbs:
            cb[0](cb[1])
        # Happy Hare ^^^

    def register_callback(self, var, method, arg):  # Happy Hare
        if var in self.menu_callbacks:
            self.menu_callbacks[var].append([method, arg])
        else:
            self.menu_callbacks[var] = [[method, arg]]

    def check_enable(self, i):  # Happy Hare
        item = self.items[i]
        key = list(item.keys())[0]
        enable = self.evaluate_enable(item[key]['enable'])
        self.labels[key].set_sensitive(enable)

    def arrangeMenuItems(self, items, columns, expand_last=False):
        for child in self.grid.get_children():
            self.grid.remove(child)
        length = len(items)
        i = 0
        show_list = []
        for item in items:
            key = list(item)[0]
            if item[key].get('show_disabled', "False").strip().lower() == "true":  # Happy Hare
                show_list.append(key)
                if self.evaluate_enable(item[key]['enable']):
                    self.labels[key].set_sensitive(True)
                else:
                    self.labels[key].set_sensitive(False)
            else:
                if self.evaluate_enable(item[key]['enable']):
                    show_list.append(key)
                    self.labels[key].set_sensitive(True)
                else:
                    # Just don't show the button
                    logging.debug(f"X > {key}")

        length = len(show_list)
        if columns == 4:
            if length <= 4:
                # Arrange 2 x 2
                columns = 2
            elif 4 < length <= 6:
                # Arrange 3 x 2
                columns = 3

        for key in show_list:
            col = i % columns
            row = int(i / columns)

            width = height = 1
            if expand_last is True and i + 1 == length and length % 2 == 1:
                width = 2

            self.grid.attach(self.labels[key], col, row, width, height)
            i += 1
        self.j2_data = None
        return self.grid

    def create_menu_items(self):
        count = 0
        for i in self.items:
            x = i[next(iter(i))]  # Happy Hare 'show_disabled' check to speed up!
            if x.get('show_disabled', "False").strip().lower() == "true" or self.evaluate_enable(x['enable']):
                count += 1
        scale = 1.1 if 12 < count <= 16 else None  # hack to fit a 4th row
        for i in range(len(self.items)):
            key = list(self.items[i])[0]
            item = self.items[i][key]

            printer = self._printer.get_printer_status_data()

            name = self._screen.env.from_string(item['name']).render(printer)
            icon = self._screen.env.from_string(item['icon']).render(printer) if item['icon'] else None
            style = self._screen.env.from_string(item['style']).render(printer) if item['style'] else None

            b = self._gtk.Button(icon, name, style or f"color{i % 4 + 1}", scale=scale)

            if item['panel'] is not None:
                panel = self._screen.env.from_string(item['panel']).render(printer)
                b.connect("clicked", self.menu_item_clicked, item)
            elif item['method'] is not None:
                params = {}

                if item['params'] is not False:
                    try:
                        p = self._screen.env.from_string(item['params']).render(printer)
                        params = json.loads(p)
                    except Exception as e:
                        logging.exception(f"Unable to parse parameters for [{name}]:\n{e}")
                        params = {}

                if item['confirm'] is not None:
                    b.connect("clicked", self._screen._confirm_send_action, item['confirm'], item['method'], params)
                else:
                    # Happy Hare: Need to know if dynamic sensitivity
                    params['show_disabled'] = item.get('show_disabled', "False").strip().lower() == "true"
                    b.connect("clicked", self._screen._send_action, item['method'], params)
            else:
                b.connect("clicked", self._screen._go_to_submenu, key)

            if item['refresh_on'] is not None:  # Happy Hare
                for var in item['refresh_on'].split(', '):
                    self.register_callback(var, self.check_enable, i)

            self.labels[key] = b

    def evaluate_enable(self, enable):
        if enable == "{{ moonraker_connected }}":
            logging.info(f"moonraker connected {self._screen._ws.connected}")
            return self._screen._ws.connected
        self.j2_data = self._printer.get_printer_status_data()
        self.j2_data["klipperscreen"] = {  # Happy Hare: to allow for menu button rather than side bar navigation
            "side_mmu_shortcut": self._config.get_main_config().getboolean("side_mmu_shortcut")
        }
        try:
            j2_temp = Template(enable, autoescape=True)
            result = j2_temp.render(self.j2_data)
            return result == 'True'
        except Exception as e:
            logging.debug(f"Error evaluating enable statement: {enable}\n{e}")
            return False
