"""
Autonomous FinOps Engine — CLI
Interfaz de línea de comandos para el motor de optimización de costos en GCP.
"""

import os
import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from foundation.config import EngineConfig
from foundation.analyzer import ResourceAnalyzer
from compute.scanner import ComputeScanner
from networking.scanner import NetworkScanner
from storage.scanner import StorageScanner
from remediation.generator import TerraformGenerator

app = typer.Typer(
    name="finops",
    help="🚀 Autonomous FinOps Engine — Detecta y remedia desperdicio de costos en GCP.",
    add_completion=False,
    rich_markup_mode="rich",
)
console = Console()


def _banner() -> None:
    console.print(
        Panel.fit(
            "[bold cyan]🚀 Autonomous FinOps Engine[/bold cyan]\n"
            "[dim]Detecta · Analiza · Remedia costos ociosos en GCP[/dim]",
            border_style="cyan",
        )
    )


def _build_config(
    demo: bool,
    project: Optional[str],
    zone: Optional[str],
    region: Optional[str],
    auto_apply: bool = False,
) -> EngineConfig:
    """Construye la configuración efectiva con overrides de CLI > env vars."""
    overrides: dict = {}
    if demo:
        overrides["DEMO_MODE"] = "true"
    if project:
        overrides["GCP_PROJECT_ID"] = project
    if zone:
        overrides["GCP_ZONE"] = zone
    if region:
        overrides["GCP_REGION"] = region
    if auto_apply:
        overrides["AUTO_APPLY"] = "true"

    for k, v in overrides.items():
        os.environ[k] = v

    return EngineConfig()


def _run_scan(cfg: EngineConfig) -> ResourceAnalyzer:
    """Ejecuta todos los escáneres y retorna el analizador con los recursos encontrados."""
    analyzer = ResourceAnalyzer()

    with console.status("[bold green]Escaneando Compute Engine...[/bold green]"):
        compute = ComputeScanner(cfg.gcp_project_id, cfg.gcp_zone)
        analyzer.add_resources(compute.scan_unattached_disks())
        analyzer.add_resources(compute.scan_stopped_instances())
        analyzer.add_resources(compute.scan_old_snapshots())

    with console.status("[bold green]Escaneando Networking...[/bold green]"):
        network = NetworkScanner(cfg.gcp_project_id, cfg.gcp_region)
        analyzer.add_resources(network.scan_unused_ips())
        analyzer.add_resources(network.scan_overly_permissive_firewalls())

    with console.status("[bold green]Escaneando Cloud Storage...[/bold green]"):
        storage = StorageScanner(cfg.gcp_project_id)
        analyzer.add_resources(storage.scan_empty_buckets())

    return analyzer


def _print_report(analyzer: ResourceAnalyzer) -> None:
    """Imprime el reporte de recursos ociosos con una tabla Rich."""
    summary = analyzer.generate_summary()
    resources = analyzer.generate_report()

    if not resources:
        console.print("[bold green]✅ ¡Excelente! No se detectaron recursos ociosos.[/bold green]")
        return

    # Tabla de recursos
    table = Table(
        title="📋 Recursos Ociosos Detectados",
        box=box.ROUNDED,
        show_lines=True,
        highlight=True,
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Tipo", style="magenta")
    table.add_column("Proyecto", style="blue")
    table.add_column("Ubicación", style="yellow")
    table.add_column("Motivo", style="white")
    table.add_column("Costo/Mes", style="bold red", justify="right")

    for r in resources:
        table.add_row(
            r.resource_id,
            r.resource_type.replace("google_", ""),
            r.project_id,
            r.zone_or_region,
            r.reason,
            f"${r.estimated_monthly_cost_usd:.2f}",
        )

    console.print(table)

    # Panel de resumen financiero
    console.print(
        Panel(
            f"[bold]Total de recursos ociosos:[/bold] {summary['total_idle_resources']}\n"
            f"[bold red]Costo mensual estimado total:[/bold red] "
            f"[bold red]${summary['total_estimated_monthly_cost_usd']:.2f} USD/mes[/bold red]\n"
            f"[bold yellow]Costo anual proyectado:[/bold yellow] "
            f"[bold yellow]${summary['total_estimated_monthly_cost_usd'] * 12:.2f} USD/año[/bold yellow]",
            title="💰 Resumen Financiero",
            border_style="red",
        )
    )


# ─────────────────────────── Comandos CLI ───────────────────────────

@app.command()
def scan(
    demo: bool = typer.Option(False, "--demo", help="Ejecutar en modo demo (sin GCP real)."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="GCP Project ID."),
    zone: Optional[str] = typer.Option(None, "--zone", "-z", help="Zona específica a escanear."),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Región específica a escanear."),
) -> None:
    """[bold cyan]Escanea[/bold cyan] el entorno GCP y muestra el reporte de recursos ociosos."""
    _banner()
    cfg = _build_config(demo, project, zone, region)
    console.print(
        f"[dim]Project: {cfg.gcp_project_id} | "
        f"Demo: {cfg.demo_mode} | "
        f"Zona: {cfg.gcp_zone or 'todas'} | "
        f"Región: {cfg.gcp_region or 'todas'}[/dim]\n"
    )
    analyzer = _run_scan(cfg)
    _print_report(analyzer)


@app.command()
def remediate(
    demo: bool = typer.Option(False, "--demo", help="Ejecutar en modo demo (sin GCP real)."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="GCP Project ID."),
    zone: Optional[str] = typer.Option(None, "--zone", "-z", help="Zona específica."),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Región específica."),
    output_dir: str = typer.Option("tf_output", "--output-dir", "-o", help="Directorio de salida para archivos .tf."),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="⚠️  Ejecutar terraform apply automáticamente."),
) -> None:
    """[bold yellow]Genera[/bold yellow] código Terraform para remediar los recursos ociosos encontrados."""
    _banner()

    if auto_apply and demo:
        console.print("[bold red]❌ No se puede usar --auto-apply en modo DEMO.[/bold red]")
        raise typer.Exit(1)

    if auto_apply:
        console.print(
            Panel(
                "⚠️  [bold red]AUTO-APPLY ACTIVADO[/bold red]\n"
                "Terraform destruirá recursos REALES en GCP.\n"
                "Asegúrate de revisar los archivos .tf antes de continuar.",
                border_style="red",
            )
        )
        confirmed = typer.confirm("¿Confirmas la ejecución autónoma de Terraform?", default=False)
        if not confirmed:
            console.print("[yellow]Operación cancelada por el usuario.[/yellow]")
            raise typer.Exit(0)

    cfg = _build_config(demo, project, zone, region, auto_apply)
    analyzer = _run_scan(cfg)
    _print_report(analyzer)

    idle_resources = analyzer.generate_report()
    if not idle_resources:
        raise typer.Exit(0)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "remediation", "templates")
    resolved_output = os.path.join(base_dir, output_dir)

    generator = TerraformGenerator(template_dir=templates_dir, output_dir=resolved_output)
    generator.generate(idle_resources, auto_apply=auto_apply)

    console.print(
        Panel(
            f"[bold green]✅ Código Terraform generado en:[/bold green] {resolved_output}\n"
            f"Archivos: main.tf, variables.tf, outputs.tf",
            border_style="green",
        )
    )


@app.command()
def run(
    demo: bool = typer.Option(False, "--demo", help="Ejecutar en modo demo (sin GCP real)."),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="GCP Project ID."),
    zone: Optional[str] = typer.Option(None, "--zone", "-z", help="Zona específica."),
    region: Optional[str] = typer.Option(None, "--region", "-r", help="Región específica."),
    output_dir: str = typer.Option("tf_output", "--output-dir", "-o", help="Directorio de salida .tf."),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="⚠️  Ejecutar terraform apply automáticamente."),
    report_json: bool = typer.Option(False, "--json", help="Exportar el reporte de hallazgos como JSON."),
) -> None:
    """[bold green]Pipeline completo[/bold green]: Scan + Report + Remediation (+ Apply opcional)."""
    _banner()

    if auto_apply and demo:
        console.print("[bold red]❌ No se puede usar --auto-apply en modo DEMO.[/bold red]")
        raise typer.Exit(1)

    cfg = _build_config(demo, project, zone, region, auto_apply)
    console.print(
        f"[dim]Project: {cfg.gcp_project_id} | "
        f"Demo: {cfg.demo_mode} | "
        f"Auto-Apply: {cfg.auto_apply}[/dim]\n"
    )

    # Fase 1: Scan
    console.rule("[bold]Fase 1: Escaneo Multi-Pilar[/bold]")
    analyzer = _run_scan(cfg)

    # Fase 2: Análisis
    console.rule("[bold]Fase 2: Análisis y Reporte[/bold]")
    _print_report(analyzer)

    idle_resources = analyzer.generate_report()

    if report_json:
        json_data = [r.model_dump() for r in idle_resources]
        console.print_json(json.dumps(json_data, indent=2))

    if not idle_resources:
        console.print("[bold green]No se requiere remediación. Pipeline finalizado.[/bold green]")
        raise typer.Exit(0)

    # Fase 3: Remediación
    console.rule("[bold]Fase 3: Generación de Remediación (Terraform)[/bold]")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    templates_dir = os.path.join(base_dir, "remediation", "templates")
    resolved_output = os.path.join(base_dir, output_dir)

    generator = TerraformGenerator(template_dir=templates_dir, output_dir=resolved_output)
    generator.generate(idle_resources, auto_apply=cfg.auto_apply)

    console.print(
        Panel(
            f"[bold green]✅ Pipeline Completado[/bold green]\n"
            f"Archivos generados en: [cyan]{resolved_output}[/cyan]",
            border_style="green",
            title="🎯 FinOps Engine",
        )
    )


if __name__ == "__main__":
    app()
