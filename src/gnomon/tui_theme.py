"""Gnomon brand — Bronze + sundial gold, sundial logo."""
from __future__ import annotations

from harness_tui.theme import Theme
from harness_tui.themes import catppuccin_mocha

GNOMON_LOGO = r"""
                       [bold #FACC15]☀[/]
                      [bold #FACC15]✦[/]
                    [bold #FACC15]✦[/]
                  [bold #FACC15]✦[/]
                [bold #B45309]│[/]
                [bold #B45309]│[/]
                [bold #B45309]│[/]
   ─VI──VII──VIII──[bold #B45309]IX[/]──X──XI──XII─
                [bold #B45309]▼[/]  [dim]shadow at noon[/]

   [bold]GNOMON[/]  [dim]· harness-aware evaluator + evolution[/]
""".strip("\n")


def gnomon_theme() -> Theme:
    return catppuccin_mocha().with_brand(
        name="gnomon",
        primary="#FACC15",
        primary_alt="#B45309",
        accent="#FDE68A",
        ascii_logo=GNOMON_LOGO,
        spinner_frames=("◐", "◓", "◑", "◒"),
    )
