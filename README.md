# NUC Istio

Helm chart for rendering Istio networking resources from declarative values.

The chart does not install Istio itself. It only renders `Gateway`, `VirtualService`, and `DestinationRule` objects for clusters where the corresponding Istio CRDs are already present.

## Quick Start

Render a representative configuration:

```bash
helm template nuc-istio . -f tests/smokes/fixtures/example.values.yaml
```

Install the chart:

```bash
helm install nuc-istio . \
  --namespace istio-system \
  --create-namespace \
  -f tests/smokes/fixtures/example.values.yaml
```

Install the local README generator hook:

```bash
pre-commit install
pre-commit install-hooks
```

## Supported Resources

The chart can render these Istio kinds:

- `Gateway`
- `VirtualService`
- `DestinationRule`

Support for individual fields still depends on the Istio CRDs installed in the target cluster.

## Values Model

Each top-level map in [values.yaml](values.yaml) maps to one resource kind:

- `gateways`
- `virtualservices`
- `destinationrules`

Per-resource controls:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | no | Resource name. `Gateway` and `DestinationRule` are passed through `helpers.app.fullname`; `VirtualService` names are rendered through `helpers.tplvalues.render`. |
| `labels` | no | Labels merged on top of the chart's built-in common labels. |
| `annotations` | no | Annotations merged on top of `generic.annotations`. |
| `selector` | Gateway only | Raw Istio gateway selector. |
| `servers` | Gateway only | Raw gateway server list. |
| `hosts` | VirtualService only | Rendered list of hosts. |
| `gateways` | VirtualService only | Referenced gateways. |
| `http` / `tls` / `tcp` | VirtualService only | Raw Istio route sections rendered as-is. |
| `host` | DestinationRule only | Target service host. |
| `trafficPolicy` | DestinationRule only | Raw traffic policy. |
| `subsets` | DestinationRule only | Optional subsets list. |
| `exportTo` | DestinationRule only | Optional export scope. |
| `workloadSelector` | DestinationRule only | Optional workload selector. |

Global controls:

- `nameOverride`
- `generic.labels`
- `generic.annotations`
- `global.apiVersions.istioGateway`
- `global.apiVersions.istioVirtualService`
- `global.apiVersions.istioDestinationRule`

## Helm Values

This section is generated from [values.yaml](values.yaml) by `helm-docs`. Edit [values.yaml](values.yaml) comments or [docs/README.md.gotmpl](docs/README.md.gotmpl), then run `pre-commit run helm-docs --all-files` to refresh it.

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| destinationrules | object | `{}` |  |
| gateways | object | `{}` |  |
| virtualservices | object | `{}` |  |

## Representative Values Files

- [values.yaml](values.yaml): minimal defaults that render no resources
- [tests/smokes/fixtures/example.values.yaml](tests/smokes/fixtures/example.values.yaml): representative fixture covering all supported resource types
- [tests/units/values/example.values.yaml](tests/units/values/example.values.yaml): unit-test fixture for representative resource checks

## Testing

The repository uses three test layers:

- `tests/units/` for `helm-unittest` suites and backward-compatibility checks
- `tests/smokes/` for render-path smoke scenarios
- `tests/e2e/` for local kind-based Helm install checks against real Istio CRDs

Representative local commands:

```bash
helm lint . -f tests/smokes/fixtures/example.values.yaml
helm unittest -f 'tests/units/*_test.yaml' .
sh tests/units/backward_compatibility_test.sh
python3 tests/smokes/run/smoke.py
make test-e2e
```

Detailed test documentation is available in [docs/TESTS.MD](docs/TESTS.MD).

Local setup instructions for the development and test toolchain are available in [docs/DEPENDENCY.md](docs/DEPENDENCY.md).

The `e2e` layer is intentionally kept out of GitLab CI and is expected to be run locally through [Makefile](Makefile) or directly via [tests/e2e/test-e2e.sh](tests/e2e/test-e2e.sh).

## Notes

- Keep the chart API versions aligned with the Istio CRDs installed in the cluster.
- The chart does not install the Istio control plane or any ingress gateway workload.

## Repository Layout

| Path | Purpose |
|------|---------|
| [Chart.yaml](Chart.yaml) | Chart metadata. |
| [values.yaml](values.yaml) | Minimal default values and `helm-docs` source comments. |
| [docs/README.md.gotmpl](docs/README.md.gotmpl) | Template used by `helm-docs` to build `README.md`. |
| [.pre-commit-config.yaml](.pre-commit-config.yaml) | Local hooks, including automatic `helm-docs` generation on commit. |
| [templates/](templates) | Istio resource templates for `Gateway`, `VirtualService`, and `DestinationRule`. |
| [tests/units/](tests/units) | Compact Helm unit suites and backward compatibility checks. |
| [tests/e2e/](tests/e2e) | Local kind-based end-to-end installation checks. |
| [tests/smokes/](tests/smokes) | Smoke scenarios for render validation. |
| [docs/DEPENDENCY.md](docs/DEPENDENCY.md) | Local dependency installation guide for development and tests. |
| [docs/TESTS.MD](docs/TESTS.MD) | Detailed testing documentation. |
