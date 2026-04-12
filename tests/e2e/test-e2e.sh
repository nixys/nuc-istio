#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

ROOT_DIR="$(git rev-parse --show-toplevel)"
SCRIPT_DIR="${ROOT_DIR}/tests/e2e"
CLUSTER_CREATED=false
CLUSTER_NAME="${CLUSTER_NAME:-$(mktemp -u "nuc-istio-e2e-XXXXXXXXXX" | tr "[:upper:]" "[:lower:]")}" 
K8S_VERSION="${K8S_VERSION:-v1.35.0}"
ISTIO_HELM_REPO="${ISTIO_HELM_REPO:-https://istio-release.storage.googleapis.com/charts}"
E2E_NAMESPACE="nuc-istio-e2e"
RELEASE_NAME="nuc-istio-e2e"
VALUES_FILE="tests/e2e/values/install.values.yaml"

RED='\033[0;31m'
YELLOW='\033[0;33m'
RESET='\033[0m'

CRDS=(
  authorizationpolicies.security.istio.io
  destinationrules.networking.istio.io
  envoyfilters.networking.istio.io
  gateways.networking.istio.io
  peerauthentications.security.istio.io
  proxyconfigs.networking.istio.io
  requestauthentications.security.istio.io
  serviceentries.networking.istio.io
  sidecars.networking.istio.io
  telemetries.telemetry.istio.io
  virtualservices.networking.istio.io
  wasmplugins.extensions.istio.io
  workloadentries.networking.istio.io
  workloadgroups.networking.istio.io
)

RESOURCES=(
  "authorizationpolicy e2e-public-access"
  "destinationrule e2e-api-destination"
  "envoyfilter e2e-lua"
  "gateway e2e-public-gateway"
  "peerauthentication e2e-strict"
  "proxyconfig e2e-proxy"
  "requestauthentication e2e-jwt"
  "serviceentry e2e-external"
  "sidecar e2e-sidecar"
  "telemetry e2e-telemetry"
  "virtualservice e2e-public-route"
  "wasmplugin e2e-wasm"
  "workloadentry e2e-vm"
  "workloadgroup e2e-group"
)

log_error() { echo -e "${RED}Error:${RESET} $1" >&2; }
log_info() { echo -e "$1"; }
log_warn() { echo -e "${YELLOW}Warning:${RESET} $1" >&2; }

show_help() {
  echo "Usage: $(basename "$0") [helm upgrade/install options]"
  echo ""
  echo "Create a kind cluster, install Istio base CRDs, and run Helm install/upgrade against the root chart."
  echo "Unknown arguments are passed through to 'helm upgrade --install'."
}

verify_prerequisites() {
  for bin in docker git kind kubectl helm; do
    if ! command -v "${bin}" >/dev/null 2>&1; then
      log_error "${bin} is not installed"
      exit 1
    fi
  done
}

cleanup() {
  local exit_code=$?

  if [ "${exit_code}" -ne 0 ] && [ "${CLUSTER_CREATED}" = true ]; then
    dump_cluster_state || true
  fi

  log_info "Cleaning up resources"

  if [ "${CLUSTER_CREATED}" = true ]; then
    log_info "Removing kind cluster ${CLUSTER_NAME}"
    if kind get clusters | grep -q "${CLUSTER_NAME}"; then
      kind delete cluster --name="${CLUSTER_NAME}"
    else
      log_warn "kind cluster ${CLUSTER_NAME} not found"
    fi
  fi

  exit "${exit_code}"
}

dump_cluster_state() {
  log_warn "Dumping Istio custom resources from ${CLUSTER_NAME}"
  kubectl get crd "${CRDS[@]}" || true
  kubectl get authorizationpolicies,destinationrules,envoyfilters,gateways,peerauthentications,proxyconfigs,requestauthentications,serviceentries,sidecars,telemetries,virtualservices,wasmplugins,workloadentries,workloadgroups -A || true
}

create_kind_cluster() {
  log_info "Creating kind cluster ${CLUSTER_NAME}"

  if kind get clusters | grep -q "${CLUSTER_NAME}"; then
    log_error "kind cluster ${CLUSTER_NAME} already exists"
    exit 1
  fi

  kind create cluster \
    --name="${CLUSTER_NAME}" \
    --config="${SCRIPT_DIR}/kind.yaml" \
    --image="kindest/node:${K8S_VERSION}" \
    --wait=60s

  CLUSTER_CREATED=true
  echo
}

install_istio_base_crds() {
  log_info "Installing Istio base CRDs from Helm repo ${ISTIO_HELM_REPO}"
  helm repo add istio "${ISTIO_HELM_REPO}" >/dev/null 2>&1 || helm repo add istio "${ISTIO_HELM_REPO}" --force-update >/dev/null
  helm repo update >/dev/null
  helm upgrade --install istio-base istio/base \
    --namespace istio-system \
    --create-namespace \
    --wait

  for crd in "${CRDS[@]}"; do
    kubectl wait --for=condition=Established --timeout=120s "crd/${crd}"
  done

  echo
}

ensure_namespace() {
  log_info "Ensuring namespace ${E2E_NAMESPACE} exists"
  kubectl get namespace "${E2E_NAMESPACE}" >/dev/null 2>&1 || kubectl create namespace "${E2E_NAMESPACE}"
  echo
}

install_chart() {
  local helm_args=(
    upgrade
    --install
    "${RELEASE_NAME}"
    "${ROOT_DIR}"
    --namespace "${E2E_NAMESPACE}"
    -f "${ROOT_DIR}/${VALUES_FILE}"
    --wait
    --timeout 300s
  )

  if [ "$#" -gt 0 ]; then
    helm_args+=("$@")
  fi

  log_info "Installing chart with Helm"
  helm "${helm_args[@]}"
  echo
}

verify_release_resources() {
  log_info "Verifying installed Istio resources"
  for item in "${RESOURCES[@]}"; do
    kubectl -n "${E2E_NAMESPACE}" get ${item}
  done
  echo
}

parse_args() {
  for arg in "$@"; do
    case "${arg}" in
      -h|--help)
        show_help
        exit 0
        ;;
    esac
  done
}

main() {
  parse_args "$@"
  verify_prerequisites

  trap cleanup EXIT

  create_kind_cluster
  install_istio_base_crds
  ensure_namespace
  install_chart "$@"
  verify_release_resources

  log_info "End-to-end checks completed successfully"
}

main "$@"
