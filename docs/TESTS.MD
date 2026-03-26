# Tests

This repository uses three complementary test layers:

- `tests/units/` for fast `helm-unittest` suites and backward-compatibility rendering
- `tests/smokes/` for render-path validation without a live cluster
- `tests/e2e/` for local-only installation checks against a disposable kind cluster with Istio CRDs installed

GitLab CI runs linting, unit tests, backward-compatibility checks, manifest rendering, and `kubeconform`.

E2E is intentionally local-only because it requires Docker, kind, and outbound access to the Istio Helm repository.

## Unit Tests

Unit tests live under `tests/units/`.

Current layout:

```text
tests/units/
├── backward_compatibility_test.sh
├── example_resources_test.yaml
├── rendering_contract_test.yaml
└── values/
    ├── example.values.yaml
    └── rendering_contract.values.yaml
```

### Covered unit checks

`rendering_contract_test.yaml` verifies chart-owned behavior:

- empty render by default for all four templates
- label and annotation merge behavior
- namespace rendering
- helper-driven naming for `Gateway` and `DestinationRule`
- `global.apiVersions` overrides

`example_resources_test.yaml` verifies representative resources for:

- `Gateway`
- `VirtualService`
- `DestinationRule`
- `AuthorizationPolicy`

`backward_compatibility_test.sh` renders the current chart with `values.yaml` from previous stable git tags and checks that old values still pass `helm lint` and `helm template`.

### Running unit tests

```bash
helm unittest -f 'tests/units/*_test.yaml' .
sh tests/units/backward_compatibility_test.sh
```

Notes:

- values file paths inside the suites are resolved relative to `tests/units/`
- the compatibility script requires git tags to be available locally

## Smoke Tests

Smoke tests live under `tests/smokes/`.

Current layout:

```text
tests/smokes/
├── fixtures/
│   ├── example.values.yaml
│   ├── invalid-list-contract.values.yaml
│   └── rendering-contract.values.yaml
├── helpers/
├── run/
├── scenarios/
└── steps/
```

### Covered smoke scenarios

The smoke suite currently covers:

1. `default-empty`
   Verifies that the chart renders no manifests with default values.

2. `schema-invalid-list-contract`
   Verifies that `values.schema.json` is active and rejects the old list-based contract for top-level resource collections.

3. `rendering-contract`
   Verifies helper-driven naming, label and annotation merge behavior, and API version overrides.

4. `example-render`
   Renders representative Istio resources and checks `Gateway`, `VirtualService`, `DestinationRule`, and `AuthorizationPolicy` output.

5. `example-kubeconform`
   Renders representative Istio resources and validates the resulting manifests with `kubeconform`.

### Prerequisites

- `python3`
- `helm`
- `kubeconform` for the `example-kubeconform` scenario
- `PyYAML`

### Running smoke tests

Install the Python dependency once:

```bash
pip3 install -r tests/smokes/requirements.txt
```

Run the suite:

```bash
python3 tests/smokes/run/smoke.py
```

Equivalent `Makefile` targets:

```bash
make test-smoke
make test-smoke-fast
```

Run a single scenario:

```bash
python3 tests/smokes/run/smoke.py --scenario rendering-contract
```

Smoke tests stage a temporary clean copy of the chart so rendering runs against the same files shipped by the repository. The staged chart includes:

- `Chart.yaml`
- `values.yaml`
- `values.yaml.example`
- `values.schema.json`
- `templates/`

## E2E Tests

End-to-end tests live under `tests/e2e/`.

Current layout:

```text
tests/e2e/
├── kind.yaml
├── test-e2e.sh
└── values/
    └── install.values.yaml
```

This layer validates that the chart can be installed into a real Kubernetes API server once Istio CRDs are present.

### What the e2e runner does

`tests/e2e/test-e2e.sh` performs the following steps:

1. Creates a disposable kind cluster from `tests/e2e/kind.yaml`
2. Installs Istio base CRDs from the official Istio Helm repository
3. Installs the chart with `helm upgrade --install`
4. Verifies the resulting `Gateway`, `VirtualService`, `DestinationRule`, and `AuthorizationPolicy`
5. Deletes the kind cluster on exit

The e2e fixture does not install an Istio control plane or ingress gateway deployment. The purpose here is API-server installability and Helm flow validation, not live traffic tests.

### Running e2e locally

```bash
bash tests/e2e/test-e2e.sh
```

Pass extra arguments through to Helm:

```bash
bash tests/e2e/test-e2e.sh --debug
```

### E2E prerequisites

- `docker`
- `kind`
- `kubectl`
- `helm`
- `git`
- outbound access to `https://istio-release.storage.googleapis.com/charts`

Optional environment overrides:

- `CLUSTER_NAME`
- `K8S_VERSION`
- `ISTIO_HELM_REPO`

### E2E notes

- The runner installs only the Istio base chart because this repository renders Istio CRDs, not control plane deployments.
- Resource existence checks are performed with `kubectl get` against the fixed namespace `nuc-istio-e2e`.
