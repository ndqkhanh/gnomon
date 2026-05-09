"""Gnomon project widgets — HIR primitive × framework heatmap.

Each cell colored by failure-attribution density:
    · green     → low (<10% of failures attributed to this primitive)
    · yellow    → mid (10–35%)
    · red       → high (>35%)

Click a cell (Enter on row + → column) drills into the failing trace
sample. For v0 we render a static demo; the real heatmap is fed by the
HAFC store on the daemon.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from rich.console import Group, RenderableType
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widgets import Static


@dataclass
class HIRCell:
    primitive: str
    framework: str
    density: float  # 0.0 .. 1.0
    samples: int = 0


_PRIMITIVES = [
    "agent.loop",
    "tool.call",
    "permission.gate",
    "context.compact",
    "memory.recall",
    "verifier.check",
    "plan.produce",
    "subagent.spawn",
]
_FRAMEWORKS = [
    "claude-code",
    "openclaw",
    "hermes",
    "crush",
    "opencode",
    "goose",
]


def _demo_grid() -> List[HIRCell]:
    seeds = {
        ("permission.gate", "claude-code"): 0.42,
        ("context.compact", "claude-code"): 0.38,
        ("verifier.check", "openclaw"): 0.61,
        ("plan.produce", "hermes"): 0.18,
        ("subagent.spawn", "hermes"): 0.55,
        ("memory.recall", "goose"): 0.27,
        ("tool.call", "crush"): 0.09,
        ("agent.loop", "opencode"): 0.31,
    }
    # Deterministic background density: stable across processes (PYTHONHASHSEED
    # would otherwise randomize hash()). FNV-1a 32-bit on the primitive+framework
    # string keeps the heatmap stable for snapshot tests.
    def _stable(s: str) -> int:
        h = 2166136261
        for ch in s:
            h ^= ord(ch)
            h = (h * 16777619) & 0xFFFFFFFF
        return h

    cells: List[HIRCell] = []
    for p in _PRIMITIVES:
        for f in _FRAMEWORKS:
            density = seeds.get(
                (p, f),
                0.05 + 0.15 * (_stable(f"{p}|{f}") % 100) / 100,
            )
            cells.append(HIRCell(primitive=p, framework=f, density=density))
    return cells


def _color_for(density: float) -> str:
    if density < 0.10:
        return "#1F2937"  # dim graphite — barely seen
    if density < 0.35:
        return "#FACC15"  # yellow — mid
    if density < 0.60:
        return "#FB923C"  # orange — high
    return "#DC2626"      # red — critical


def _glyph_for(density: float) -> str:
    if density < 0.05:
        return "·"
    if density < 0.15:
        return "▒"
    if density < 0.35:
        return "▓"
    return "█"


class HIRHeatmap(Vertical):
    DEFAULT_CSS = """
    HIRHeatmap {
        height: 1fr;
    }
    HIRHeatmap #grid {
        height: 1fr;
        background: $bg;
        padding: 0 1;
    }
    HIRHeatmap #legend {
        height: 6;
        background: $bg_alt;
        padding: 0 1;
        color: $fg_muted;
    }
    """

    def __init__(self, cells: List[HIRCell] | None = None) -> None:
        super().__init__()
        self.cells = cells or _demo_grid()

    def compose(self) -> ComposeResult:
        yield Static(self._render_grid(), id="grid")
        yield Static(self._render_legend(), id="legend")

    def _render_grid(self) -> RenderableType:
        # Build a grid: rows = primitives, columns = frameworks
        index = {(c.primitive, c.framework): c for c in self.cells}
        table = Table(show_header=True, header_style="bold cyan", box=None,
                      padding=(0, 1), expand=False)
        table.add_column("primitive", no_wrap=True, style="dim")
        for fw in _FRAMEWORKS:
            table.add_column(fw[:8], no_wrap=True, justify="center")
        for prim in _PRIMITIVES:
            row: list = [prim]
            for fw in _FRAMEWORKS:
                cell = index.get((prim, fw))
                if not cell:
                    row.append("")
                    continue
                color = _color_for(cell.density)
                glyph = _glyph_for(cell.density)
                row.append(Text(glyph, style=color))
            table.add_row(*row)
        return table

    def _render_legend(self) -> Text:
        legend = Text()
        legend.append("failure-attribution density\n", style="bold")
        for label, hex_, glyph in (
            ("low (<10%)",  "#1F2937", "·"),
            ("mid (10-35%)", "#FACC15", "▓"),
            ("high (35-60%)", "#FB923C", "█"),
            ("critical (≥60%)", "#DC2626", "█"),
        ):
            legend.append(f"  {glyph} ", style=hex_)
            legend.append(f"{label}\n", style="dim")
        return legend
