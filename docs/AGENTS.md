# Agent Guide

This repository contains the standalone `nuc-istio` Helm chart.

The chart renders only Istio networking resources:

- `Gateway`
- `VirtualService`
- `DestinationRule`

It does not manage workloads, Services, or Istio control plane installation.

## Repository Shape

Current repository layout:

```text
.
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── gateway.yml
│   ├── virtualservice.yml
│   └── destinationrule.yml
├── tests/
│   ├── units/
│   ├── e2e/
│   └── smokes/
└── docs/
```

Do not document files that do not exist in this repository. In particular, this chart currently does not ship `values.yaml.example` or `values.schema.json`.

## Dependency Model

Shared helper templates come from the `nuc-common` Helm chart.

For this standalone repository:

- `Chart.yaml` declares `nuc-common` as a local `file://charts/nuc-common` dependency
- GitLab CI clones `nuc-common` into `charts/nuc-common` with `CI_JOB_TOKEN`
- local e2e can clone the same dependency if it is not already present
- smoke tests stage a clean chart copy and inject `nuc-common` from the local workspace

When changing helper usage, keep `Chart.yaml`, CI, smoke staging, and local e2e aligned in the same change.

## Chart Contract

Keep the chart contract small and predictable:

- default `values.yaml` renders no manifests
- supported resources are keyed by map name under `gateways`, `virtualservices`, and `destinationrules`
- `Gateway` and `DestinationRule` names are built with `helpers.app.fullname`
- `VirtualService` names are rendered via `helpers.tplvalues.render`
- global API version overrides come from `global.apiVersions`
- generic labels and annotations come from `generic.labels` and `generic.annotations`

Do not reintroduce Gateway API concepts such as `GatewayClass`, `HTTPRoute`, `GRPCRoute`, `TLSRoute`, or `BackendTLSPolicy` into this chart unless the templates are actually added.

## Test Expectations

The repository uses three test layers:

- `tests/units/` for `helm-unittest`
- `tests/smokes/` for render-path checks without a live cluster
- `tests/e2e/` for local-only install checks against a disposable kind cluster

GitLab CI covers lint, unit tests, backward-compatibility rendering, render validation, and `kubeconform`.

E2E is local-only by design because it needs:

- Docker
- kind
- kubectl
- helm
- git
- outbound access to clone `nuc-common`
- outbound access to the Istio Helm repository

Do not document e2e as a CI job unless a real runner with those capabilities is wired in.

## Documentation Rules

- Keep `docs/TESTS.MD` aligned with the real test suite names, fixtures, and commands.
- Use relative Markdown links only.
- Prefer current behavior over aspirational workflows.
- When changing resource kinds, update docs and tests together.
- Remove stale examples instead of keeping multiple contradictory examples.

## Verification

For repository changes, prefer a compact final pass:

```bash
git diff --check
bash -n tests/e2e/test-e2e.sh
sh -n tests/units/backward_compatibility_test.sh
python3 -m py_compile tests/smokes/helpers/argparser.py tests/smokes/run/smoke.py tests/smokes/scenarios/smoke.py tests/smokes/steps/*.py
helm dependency build .
helm unittest -f 'tests/units/*_test.yaml' .
python3 tests/smokes/run/smoke.py
```

If `charts/nuc-common` is absent locally, fetch it first or run the workflow that prepares it.
