from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from tests.smokes.steps import chart, helm, kubeconform, render, system


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

    @property
    def invalid_list_contract_values(self) -> Path:
        return (
            self.repo_root
            / "tests"
            / "smokes"
            / "fixtures"
            / "invalid-list-contract.values.yaml"
        )


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


def check_schema_invalid_list_contract(context: SmokeContext) -> None:
    result = helm.lint(
        context.chart_dir,
        values_file=context.invalid_list_contract_values,
        workdir=context.workdir,
        check=False,
    )
    if result.returncode == 0:
        raise system.TestFailure(
            "helm lint unexpectedly succeeded for invalid list-based values"
        )

    combined_output = f"{result.stdout}\n{result.stderr}"
    if "gateways" not in combined_output or "object" not in combined_output:
        raise system.TestFailure(
            "helm lint failed for invalid values, but the error does not mention the object-based map contract"
        )


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
    render.assert_doc_count(documents, 14)

    gateway = render.select_document(documents, kind="Gateway", name="edge-gateway")
    render.assert_path(gateway, "apiVersion", "custom.networking.io/v1alpha2")
    render.assert_path(gateway, "metadata.namespace", "edge-gateways")
    render.assert_path(gateway, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(gateway, "metadata.labels.team", "platform")
    render.assert_path(gateway, "metadata.labels.platform", "mesh")
    render.assert_path(gateway, "metadata.labels.component", "gateway")
    render.assert_path(gateway, "metadata.labels.tier", "edge")
    render.assert_path(gateway, "metadata.annotations.owner", "common-layer")
    render.assert_path(gateway, "metadata.annotations.note", "external")
    render.assert_path(gateway, "spec.servers[0].hosts[0]", "corp.example.org")

    virtual_service = render.select_document(
        documents, kind="VirtualService", name=f"{context.release_name}-edge"
    )
    render.assert_path(virtual_service, "apiVersion", "custom.networking.io/v1alpha3")
    render.assert_path(virtual_service, "metadata.namespace", "app-routing")
    render.assert_path(virtual_service, "metadata.labels.component", "routing")
    render.assert_path(virtual_service, "metadata.annotations.note", "public")
    render.assert_path(virtual_service, "spec.http[0].redirect.redirectCode", 308)
    render.assert_path(virtual_service, "spec.exportTo[0]", ".")

    destination_rule = render.select_document(
        documents, kind="DestinationRule", name="edge-destination"
    )
    render.assert_path(destination_rule, "apiVersion", "custom.networking.io/v1alpha4")
    render.assert_path(destination_rule, "metadata.namespace", "app-routing")
    render.assert_path(destination_rule, "metadata.labels.component", "policy")
    render.assert_path(destination_rule, "metadata.annotations.note", "destination")
    render.assert_path(destination_rule, "spec.subsets[0].labels.version", "stable")

    authorization_policy = render.select_document(
        documents, kind="AuthorizationPolicy", name="edge-access"
    )
    render.assert_path(authorization_policy, "apiVersion", "custom.security.io/v1alpha1")
    render.assert_path(authorization_policy, "metadata.namespace", "policy-namespace")
    render.assert_path(authorization_policy, "spec.action", "DENY")

    service_entry = render.select_document(documents, kind="ServiceEntry", name="ext-payments")
    render.assert_path(service_entry, "apiVersion", "custom.networking.io/v1alpha2")
    render.assert_path(service_entry, "metadata.annotations.note", "external-service")

    telemetry = render.select_document(documents, kind="Telemetry", name="edge-observability")
    render.assert_path(telemetry, "apiVersion", "custom.telemetry.io/v1alpha1")
    render.assert_path(telemetry, "metadata.namespace", "observability")


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
    render.assert_doc_count(documents, 28)
    render.assert_kinds(
        documents,
        {
            "AuthorizationPolicy",
            "DestinationRule",
            "EnvoyFilter",
            "Gateway",
            "PeerAuthentication",
            "ProxyConfig",
            "RequestAuthentication",
            "ServiceEntry",
            "Sidecar",
            "Telemetry",
            "VirtualService",
            "WasmPlugin",
            "WorkloadEntry",
            "WorkloadGroup",
        },
    )

    gateway = render.select_document(documents, kind="Gateway", name="public-gateway")
    render.assert_path(gateway, "metadata.namespace", context.namespace)
    render.assert_path(gateway, "metadata.labels[app.kubernetes.io/name]", "istio-platform")
    render.assert_path(gateway, "metadata.labels.managed-by-layer", "dependency")
    render.assert_path(gateway, "spec.servers[0].hosts[0]", "example.org")

    virtual_service = render.select_document(documents, kind="VirtualService", name="public-api")
    render.assert_path(virtual_service, "metadata.namespace", context.namespace)
    render.assert_path(virtual_service, "spec.hosts[1]", "api.example.org")
    render.assert_path(virtual_service, "spec.gateways[1]", "mesh")
    render.assert_path(virtual_service, "spec.http[0].route[0].destination.host", "api.default.svc.cluster.local")

    destination_rule = render.select_document(documents, kind="DestinationRule", name="payments-backend")
    render.assert_path(destination_rule, "metadata.namespace", "payments")
    render.assert_path(destination_rule, "spec.exportTo[1]", "observability")

    authorization_policy = render.select_document(documents, kind="AuthorizationPolicy", name="ingress-allow")
    render.assert_path(authorization_policy, "metadata.namespace", "istio-system")
    render.assert_path(authorization_policy, "spec.selector.matchLabels.istio", "ingressgateway")
    render.assert_path(
        authorization_policy,
        "spec.rules[0].from[0].source.remoteIpBlocks[0]",
        "203.0.113.10/32",
    )


def check_example_kubeconform(context: SmokeContext) -> None:
    output_path = context.render_dir / "example-kubeconform.yaml"
    helm.template(
        context.chart_dir,
        release_name=context.release_name,
        namespace=context.namespace,
        values_file=context.example_values,
        output_path=output_path,
        workdir=context.workdir,
    )
    kubeconform.validate(
        manifest_path=output_path,
        kube_version=context.kube_version,
        kubeconform_bin=context.kubeconform_bin,
        schema_location=context.schema_location,
        skip_kinds=context.skip_kinds,
    )


SCENARIOS: list[tuple[str, Callable[[SmokeContext], None]]] = [
    ("default-empty", check_default_empty),
    ("schema-invalid-list-contract", check_schema_invalid_list_contract),
    ("rendering-contract", check_rendering_contract),
    ("example-render", check_example_render),
    ("example-kubeconform", check_example_kubeconform),
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
