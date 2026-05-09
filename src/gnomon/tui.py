"""Gnomon TUI — harness-aware evaluator + closed evolution loop."""
from __future__ import annotations

import os
from typing import Optional

import click
from harness_tui import HarnessApp, ProjectConfig
from harness_tui.commands.registry import register_command
from harness_tui.transport import HTTPTransport, MockTransport

from .tui_theme import gnomon_theme
from .widgets import HIRHeatmap


@register_command(name="hir", description="Scan a framework's HIR coverage",
                  category="Gnomon")
async def cmd_hir(app, args: str) -> None:  # type: ignore[no-untyped-def]
    if args.startswith("scan "):
        fw = args[5:].strip()
        app.shell.chat_log.write_system(f"HIR scan: {fw!r} → coverage report (mock)")
    else:
        app.shell.chat_log.write_system("usage: /hir scan <framework>")


@register_command(name="patch", description="Propose a reversible patch",
                  category="Gnomon")
async def cmd_patch(app, args: str) -> None:  # type: ignore[no-untyped-def]
    app.shell.chat_log.write_system(
        "patch propose: dispatched (Autogenesis-shaped, gated by mesa-guard)"
    )


@register_command(name="evolve", description="Start a closed-loop evolution run",
                  category="Gnomon")
async def cmd_evolve(app, args: str) -> None:  # type: ignore[no-untyped-def]
    if args.startswith("start"):
        app.shell.chat_log.write_system("evolution run: started (Pass^k tracked)")
    else:
        app.shell.chat_log.write_system("usage: /evolve start")


@register_command(name="bundle", description="Export a portable HIR bundle",
                  category="Gnomon")
async def cmd_bundle(app, args: str) -> None:  # type: ignore[no-untyped-def]
    if args.startswith("export"):
        app.shell.chat_log.write_system("HIR bundle: exported to artifacts/")
    else:
        app.shell.chat_log.write_system("usage: /bundle export")


@click.command()
@click.option("--url", default=None)
@click.option("--mock", is_flag=True)
@click.option("--serve", is_flag=True,
              help="Run the TUI in a browser via textual-serve.")
@click.option("--port", type=int, default=8011,
              help="Web mode port (with --serve).")
@click.option("--host", default="127.0.0.1",
              help="Web mode host (with --serve).")
def main(url: Optional[str], mock: bool, serve: bool, port: int, host: str) -> None:
    """Open the Gnomon TUI."""
    if serve:
        from harness_tui.serve import serve_app, make_module_command

        flags = []
        if mock:
            flags.append("--mock")
        if url:
            flags.append(f"--url {url}")
        serve_app(
            command=make_module_command("gnomon.tui", " ".join(flags)),
            host=host, port=port,
            title="gnomon",
        )
        return
    if mock:
        transport = MockTransport()
    else:
        backend = url or os.environ.get("GNOMON_BACKEND") or "http://localhost:8011"
        transport = HTTPTransport(
            backend,
            endpoints={"run": "/v1/attribute"},
            payload_builder=lambda t, m: {"trace_id": t},
            text_field="report",
        )
    cfg = ProjectConfig(
        name="gnomon",
        description="Harness-aware evaluator + evolution loop",
        theme=gnomon_theme(),
        transport=transport,
        model=os.environ.get("GNOMON_MODEL", "auto"),
        sidebar_tabs=[("HIR", HIRHeatmap())],
    )
    app = HarnessApp(cfg)
    app.run()
    summary = getattr(app, "last_exit_summary", None)
    if summary:
        click.echo(summary.render())


if __name__ == "__main__":  # pragma: no cover
    main()
