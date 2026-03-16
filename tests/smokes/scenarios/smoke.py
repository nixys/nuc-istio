from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tests.smokes.steps import chart, helm, render, system


@dataclass
class SmokeContext:
    repo_root: Path
    workdir: Path
    chart_dir: Path
    render_dir: Path
    release_name: str
    namespace: str
    kube_version: str
    kubeconform_bin: str
    schema_location: str
    skip_kinds: str

    @property
    def rendering_contract_values(self) -> Path:
        return self.repo_root / "tests" / "smokes" / "fixtures" / "rendering-contract.values.yaml"

    @property
    def example_values(self) -> Path:
        return self.repo_root / "tests" / "smokes" / "fixtures" / "example.values.yaml"


def check_default_empty(context: SmokeContext) -> None:
    helm.lint(context.chart_dir, workdir=context.workdir)
    output_path = context.render_dir / "default-empty.yaml"
    helm.template(
        context.chart_dir,
        release_name=context.release_name,
        namespace=context.namespace,
        output_path=output_path,
        workdir=context.workdir,
    )
    documents = render.load_documents(output_path)
    render.assert_doc_count(documents, 0)


def check_rendering_contract(context: SmokeContext) -> None:
    helm.lint(
        context.chart_dir,
        values_file=context.rendering_contract_values,
        workdir=context.workdir,
    )
    output_path = context.render_dir / "rendering-contract.yaml"
    helm.template(
        context.chart_dir,
        release_name=context.release_name,
        namespace=context.namespace,
        values_file=context.rendering_contract_values,
        output_path=output_path,
        workdir=context.workdir,
    )

    documents = render.load_documents(output_path)
    render.assert_doc_count(documents, 3)

    gateway = render.select_document(
        documents, kind="Gateway", name="istio-platform-edge-gateway"
    )
    render.assert_path(gateway, "apiVersion", "custom.istio.io/v1alpha1")
    render.assert_path(gateway, "metadata.namespace", context.namespace)
    render.assert_path(
        gateway,
        "metadata.labels[app.kubernetes.io/name]",
        "istio-platform",
    )
    render.assert_path(gateway, "metadata.labels[app.kubernetes.io/instance]", context.release_name)
    render.assert_path(gateway, "metadata.labels.platform", "edge")
    render.assert_path(gateway, "metadata.labels.component", "gateway")
    render.assert_path(gateway, "metadata.labels.tier", "edge")
    render.assert_path(gateway, "metadata.annotations.owner", "platform-team")
    render.assert_path(gateway, "metadata.annotations.note", "external")
    render.assert_path(gateway, "spec.selector.istio", "ingressgateway")
    render.assert_path(gateway, "spec.servers[0].hosts[0]", "corp.example.org")

    virtual_service = render.select_document(
        documents, kind="VirtualService", name=f"{context.release_name}-edge"
    )
    render.assert_path(virtual_service, "apiVersion", "custom.istio.io/v1alpha1")
    render.assert_path(virtual_service, "metadata.namespace", context.namespace)
    render.assert_path(virtual_service, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(virtual_service, "metadata.labels.component", "routing")
    render.assert_path(virtual_service, "metadata.annotations.note", "public")
    render.assert_path(virtual_service, "spec.hosts[0]", "corp.example.org")
    render.assert_path(virtual_service, "spec.gateways[0]", "edge-gateway")
    render.assert_path(virtual_service, "spec.http[0].route[0].destination.host", "edge.default.svc.cluster.local")
    render.assert_path(virtual_service, "spec.exportTo[0]", ".")

    destination_rule = render.select_document(
        documents, kind="DestinationRule", name="istio-platform-edge-destination"
    )
    render.assert_path(destination_rule, "apiVersion", "custom.istio.io/v1alpha1")
    render.assert_path(destination_rule, "metadata.namespace", context.namespace)
    render.assert_path(destination_rule, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(destination_rule, "metadata.labels.component", "policy")
    render.assert_path(destination_rule, "metadata.annotations.note", "destination")
    render.assert_path(destination_rule, "spec.host", "edge.default.svc.cluster.local")
    render.assert_path(destination_rule, "spec.subsets[0].name", "stable")
    render.assert_path(destination_rule, "spec.subsets[0].labels.version", "stable")
    render.assert_path(destination_rule, "spec.workloadSelector.matchLabels.app", "edge")


def check_example_render(context: SmokeContext) -> None:
    helm.lint(
        context.chart_dir,
        values_file=context.example_values,
        workdir=context.workdir,
    )
    output_path = context.render_dir / "example-render.yaml"
    helm.template(
        context.chart_dir,
        release_name=context.release_name,
        namespace=context.namespace,
        values_file=context.example_values,
        output_path=output_path,
        workdir=context.workdir,
    )

    documents = render.load_documents(output_path)
    render.assert_doc_count(documents, 3)
    render.assert_kinds(
        documents,
        {
            "Gateway",
            "VirtualService",
            "DestinationRule",
        },
    )

    gateway = render.select_document(
        documents, kind="Gateway", name="istio-platform-public-gateway"
    )
    render.assert_path(gateway, "metadata.namespace", context.namespace)
    render.assert_path(gateway, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(gateway, "spec.servers[0].hosts[0]", "example.org")
    render.assert_path(gateway, "spec.servers[1].tls.credentialName", "public-gateway-tls")

    virtual_service = render.select_document(
        documents, kind="VirtualService", name=f"{context.release_name}-public"
    )
    render.assert_path(virtual_service, "metadata.namespace", context.namespace)
    render.assert_path(virtual_service, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(virtual_service, "spec.hosts[1]", "api.example.org")
    render.assert_path(virtual_service, "spec.gateways[1]", "mesh")
    render.assert_path(virtual_service, "spec.http[0].retries.attempts", 3)
    render.assert_path(virtual_service, "spec.http[0].timeout", "10s")
    render.assert_path(virtual_service, "spec.http[0].rewrite.uri", "/")
    render.assert_path(virtual_service, "spec.http[1].fault.abort.httpStatus", 503)
    render.assert_path(virtual_service, "spec.tls[0].match[0].sniHosts[0]", "secure.example.org")
    render.assert_path(virtual_service, "spec.tcp[0].route[0].destination.host", "mysql.default.svc.cluster.local")

    destination_rule = render.select_document(
        documents, kind="DestinationRule", name="istio-platform-api-destination"
    )
    render.assert_path(destination_rule, "metadata.namespace", context.namespace)
    render.assert_path(destination_rule, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(destination_rule, "spec.trafficPolicy.loadBalancer.simple", "ROUND_ROBIN")
    render.assert_path(destination_rule, "spec.subsets[0].trafficPolicy.loadBalancer.simple", "LEAST_CONN")
    render.assert_path(destination_rule, "spec.exportTo[1]", "observability")
    render.assert_path(destination_rule, "spec.workloadSelector.matchLabels.app", "api")


SCENARIOS: list[tuple[str, Callable[[SmokeContext], None]]] = [
    ("default-empty", check_default_empty),
    ("rendering-contract", check_rendering_contract),
    ("example-render", check_example_render),
]


def run_smoke_suite(args) -> int:
    scenario_map = dict(SCENARIOS)
    requested = args.scenario or ["all"]
    if "all" in requested:
        selected = [name for name, _ in SCENARIOS]
    else:
        selected = requested

    repo_root = Path(args.chart_dir).resolve()
    workdir, chart_dir = chart.stage_chart(repo_root, args.workdir)
    context = SmokeContext(
        repo_root=repo_root,
        workdir=workdir,
        chart_dir=chart_dir,
        render_dir=workdir / "rendered",
        release_name=args.release_name,
        namespace=args.namespace,
        kube_version=args.kube_version,
        kubeconform_bin=args.kubeconform_bin,
        schema_location=args.schema_location,
        skip_kinds=args.skip_kinds,
    )
    context.render_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[str, str]] = []
    try:
        for name in selected:
            system.log(f"=== scenario: {name} ===")
            try:
                scenario_map[name](context)
            except Exception as exc:
                failures.append((name, str(exc)))
                system.log(f"FAILED: {name}: {exc}")
            else:
                system.log(f"PASSED: {name}")
    finally:
        if args.keep_workdir:
            system.log(f"workdir kept at {workdir}")
        else:
            chart.cleanup(workdir)

    if failures:
        system.log("=== summary: failures ===")
        for name, message in failures:
            system.log(f"- {name}: {message}")
        return 1

    system.log("=== summary: all smoke scenarios passed ===")
    return 0
