import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk


class FlowBoxGrid(Gtk.FlowBox):
    """
    A subclass of Gtk.FlowBox that arranges its children in a grid-like layout.
    layout selection is automatic (columns x rows):
    horizontal: 3 x 1, 2 x 2, 3 x 2, 4 x n
    vertical: 1 x 3, 2 x n

    Args:
        length (int): The number of children to be arranged in the FlowBox.
        vertical (bool): If True, the layout will be optimized for a vertical layout.
    """

    def __init__(self, length, vertical=False):
        if vertical and length < 4:
            n = 1
        elif vertical or length in {4, 2}:
            n = 2
        elif length in {3, 5, 6}:
            # Arrange 3 x 2
            n = 3
        else:
            n = 4
        super().__init__(
            hexpand=True, vexpand=True, homogeneous=True,
            selection_mode=Gtk.SelectionMode.NONE, max_children_per_line=n
        )
