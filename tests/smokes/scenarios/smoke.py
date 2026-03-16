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
    def example_values(self) -> Path:
        return self.repo_root / "values.yaml.example"

    @property
    def rendering_contract_values(self) -> Path:
        return self.repo_root / "tests" / "smokes" / "fixtures" / "rendering-contract.values.yaml"

    @property
    def invalid_missing_name_values(self) -> Path:
        return self.repo_root / "tests" / "smokes" / "fixtures" / "invalid-missing-name.values.yaml"


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


def check_schema_invalid_missing_name(context: SmokeContext) -> None:
    result = helm.lint(
        context.chart_dir,
        values_file=context.invalid_missing_name_values,
        workdir=context.workdir,
        check=False,
    )
    if result.returncode == 0:
        raise system.TestFailure(
            "helm lint unexpectedly succeeded for invalid values without resource name"
        )

    combined_output = f"{result.stdout}\n{result.stderr}"
    if "name" not in combined_output:
        raise system.TestFailure(
            "helm lint failed for invalid values, but the error does not mention the missing name field"
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
    render.assert_doc_count(documents, 2)

    gateway = render.select_document(documents, kind="Gateway", name="merged-gateway")
    render.assert_path(gateway, "apiVersion", "example.net/v1alpha1")
    render.assert_path(gateway, "metadata.namespace", context.namespace)
    render.assert_path(
        gateway,
        "metadata.labels[app.kubernetes.io/name]",
        "gateway-platform",
    )
    render.assert_path(gateway, "metadata.labels.platform", "gateway-api")
    render.assert_path(gateway, "metadata.labels.component", "gateway")
    render.assert_path(gateway, "metadata.labels.tier", "edge")
    render.assert_path(gateway, "metadata.annotations.team", "platform")
    render.assert_path(gateway, "metadata.annotations.note", "external")
    render.assert_path(gateway, "spec.gatewayClassName", "public-gateway-class")

    gateway_class = render.select_document(
        documents, kind="GatewayClass", name="public-gateway-class"
    )
    render.assert_path(gateway_class, "apiVersion", "gateway.networking.k8s.io/v1beta1")
    render.assert_path_missing(gateway_class, "metadata.namespace")
    render.assert_path(
        gateway_class,
        "metadata.labels[app.kubernetes.io/name]",
        "gateway-platform",
    )
    render.assert_path(gateway_class, "metadata.labels.component", "gateway-class")
    render.assert_path(gateway_class, "metadata.annotations.team", "platform")
    render.assert_path(gateway_class, "metadata.annotations.note", "public")
    render.assert_path(
        gateway_class, "spec.controllerName", "example.net/gateway-controller"
    )


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
    render.assert_doc_count(documents, 9)
    render.assert_kinds(
        documents,
        {
            "BackendTLSPolicy",
            "GatewayClass",
            "Gateway",
            "GRPCRoute",
            "HTTPRoute",
            "ListenerSet",
            "ReferenceGrant",
            "TLSRoute",
        },
    )

    gateway_class = render.select_document(
        documents, kind="GatewayClass", name="public-gateway-class"
    )
    render.assert_path_missing(gateway_class, "metadata.namespace")

    gateway = render.select_document(documents, kind="Gateway", name="edge-gateway")
    render.assert_path(gateway, "metadata.namespace", "edge-ns")
    render.assert_path(gateway, "spec.listeners[0].protocol", "HTTPS")

    backend_tls = render.select_document(
        documents, kind="BackendTLSPolicy", name="backend-tls-with-wellknown"
    )
    render.assert_path(
        backend_tls, "spec.validation.wellKnownCACertificates", "System"
    )

    http_route = render.select_document(documents, kind="HTTPRoute", name="api-http")
    render.assert_path(http_route, "spec.rules[0].filters[4].cors.maxAge", 86400)

    tls_route = render.select_document(documents, kind="TLSRoute", name="passthrough-tls")
    render.assert_path(tls_route, "spec.rules[0].backendRefs[1].port", 8443)


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
    ("schema-invalid-missing-name", check_schema_invalid_missing_name),
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
