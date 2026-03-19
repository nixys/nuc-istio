{{- define "nuc-istio.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "nuc-istio.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "nuc-istio.fullname" -}}
{{- if .name -}}
{{- printf "%s-%s" (include "nuc-istio.name" .context) .name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- include "nuc-istio.name" .context -}}
{{- end -}}
{{- end -}}

{{- define "nuc-istio.labels" -}}
app.kubernetes.io/name: {{ include "nuc-istio.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ include "nuc-istio.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
{{- end -}}

{{- define "nuc-istio.tplvalues.render" -}}
{{- if typeIs "string" .value -}}
{{- tpl .value .context -}}
{{- else -}}
{{- tpl (.value | toYaml) .context -}}
{{- end -}}
{{- end -}}

{{- define "nuc-istio.tplContext" -}}
{{- $tplContext := deepCopy . -}}
{{- if .Values.global -}}
{{- $_ := set $tplContext "Values" (mergeOverwrite (deepCopy .Values.global) .Values) -}}
{{- end -}}
{{- $tplContext | toYaml -}}
{{- end -}}

{{- define "nuc-istio.resourceLabels" -}}
{{- $root := .root -}}
{{- $item := .item | default dict -}}
{{- $generic := get $root.Values "generic" | default dict -}}
{{- $labels := mustMergeOverwrite (dict) (include "nuc-istio.labels" $root | fromYaml) (get $generic "labels" | default dict) ($item.labels | default dict) -}}
{{- toYaml $labels -}}
{{- end -}}

{{- define "nuc-istio.resourceAnnotations" -}}
{{- $root := .root -}}
{{- $item := .item | default dict -}}
{{- $generic := get $root.Values "generic" | default dict -}}
{{- $annotations := mustMergeOverwrite (dict) (get $generic "annotations" | default dict) ($item.annotations | default dict) -}}
{{- toYaml $annotations -}}
{{- end -}}

{{- define "nuc-istio.renderMetadata" -}}
{{- $root := .root -}}
{{- $item := .item | default dict -}}
metadata:
  name: {{ .name }}
  namespace: {{ default $root.Release.Namespace $item.namespace | quote }}
  labels:
{{ include "nuc-istio.resourceLabels" (dict "root" $root "item" $item) | nindent 4 }}
  annotations:
{{ include "nuc-istio.resourceAnnotations" (dict "root" $root "item" $item) | nindent 4 }}
{{- end -}}

{{- define "nuc-istio.istiogateway.apiVersion" -}}
{{- $apiVersions := get .Values "apiVersions" | default dict -}}
{{- $global := get .Values "global" | default dict -}}
{{- $globalApiVersions := get $global "apiVersions" | default dict -}}
{{- coalesce (get $apiVersions "istioGateway") (get $globalApiVersions "istioGateway") "networking.istio.io/v1beta1" -}}
{{- end -}}

{{- define "nuc-istio.istiovirtualservice.apiVersion" -}}
{{- $apiVersions := get .Values "apiVersions" | default dict -}}
{{- $global := get .Values "global" | default dict -}}
{{- $globalApiVersions := get $global "apiVersions" | default dict -}}
{{- coalesce (get $apiVersions "istioVirtualService") (get $globalApiVersions "istioVirtualService") "networking.istio.io/v1beta1" -}}
{{- end -}}

{{- define "nuc-istio.istiodestinationrule.apiVersion" -}}
{{- $apiVersions := get .Values "apiVersions" | default dict -}}
{{- $global := get .Values "global" | default dict -}}
{{- $globalApiVersions := get $global "apiVersions" | default dict -}}
{{- coalesce (get $apiVersions "istioDestinationRule") (get $globalApiVersions "istioDestinationRule") "networking.istio.io/v1beta1" -}}
{{- end -}}

{{- define "nuc-istio.renderGatewaySpec" -}}
{{- $tplContext := .tplContext -}}
selector:
{{ include "nuc-istio.tplvalues.render" (dict "value" .item.selector "context" $tplContext) | nindent 2 }}
servers:
{{ include "nuc-istio.tplvalues.render" (dict "value" .item.servers "context" $tplContext) | nindent 2 }}
{{- end -}}

{{- define "nuc-istio.renderGateway" -}}
{{- $root := .root -}}
{{- $name := .name -}}
{{- $item := .item | default dict -}}
{{- $tplContext := include "nuc-istio.tplContext" $root | fromYaml -}}
---
apiVersion: {{ default (include "nuc-istio.istiogateway.apiVersion" $root) $item.apiVersion }}
kind: Gateway
{{ include "nuc-istio.renderMetadata" (dict "root" $root "item" $item "name" (include "nuc-istio.fullname" (dict "name" ($item.name | default $name) "context" $root))) }}
spec:
{{ include "nuc-istio.renderGatewaySpec" (dict "item" $item "tplContext" $tplContext) | nindent 2 }}
{{- end -}}

{{- define "nuc-istio.renderVirtualServiceSpec" -}}
{{- $tplContext := .tplContext -}}
{{- $item := .item -}}
hosts:
  {{- range $host := $item.hosts }}
  - {{ include "nuc-istio.tplvalues.render" (dict "value" $host "context" $tplContext) | quote }}
  {{- end }}
gateways:
  {{- range $gateway := $item.gateways }}
  - {{ include "nuc-istio.tplvalues.render" (dict "value" $gateway "context" $tplContext) | quote }}
  {{- end }}
{{- with $item.http }}
http:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.tls }}
tls:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.tcp }}
tcp:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.exportTo }}
exportTo:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "nuc-istio.renderVirtualService" -}}
{{- $root := .root -}}
{{- $name := .name -}}
{{- $item := .item | default dict -}}
{{- $tplContext := include "nuc-istio.tplContext" $root | fromYaml -}}
---
apiVersion: {{ default (include "nuc-istio.istiovirtualservice.apiVersion" $root) $item.apiVersion }}
kind: VirtualService
{{ include "nuc-istio.renderMetadata" (dict "root" $root "item" $item "name" (include "nuc-istio.tplvalues.render" (dict "value" ($item.name | default $name) "context" $tplContext))) }}
spec:
{{ include "nuc-istio.renderVirtualServiceSpec" (dict "item" $item "tplContext" $tplContext) | nindent 2 }}
{{- end -}}

{{- define "nuc-istio.renderDestinationRuleSpec" -}}
{{- $tplContext := .tplContext -}}
{{- $item := .item -}}
host: {{ include "nuc-istio.tplvalues.render" (dict "value" $item.host "context" $tplContext) | quote }}
{{- with $item.trafficPolicy }}
trafficPolicy:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.subsets }}
subsets:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.exportTo }}
exportTo:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- with $item.workloadSelector }}
workloadSelector:
{{ include "nuc-istio.tplvalues.render" (dict "value" . "context" $tplContext) | nindent 2 }}
{{- end }}
{{- end -}}

{{- define "nuc-istio.renderDestinationRule" -}}
{{- $root := .root -}}
{{- $name := .name -}}
{{- $item := .item | default dict -}}
{{- $tplContext := include "nuc-istio.tplContext" $root | fromYaml -}}
---
apiVersion: {{ default (include "nuc-istio.istiodestinationrule.apiVersion" $root) $item.apiVersion }}
kind: DestinationRule
{{ include "nuc-istio.renderMetadata" (dict "root" $root "item" $item "name" (include "nuc-istio.fullname" (dict "name" ($item.name | default $name) "context" $root))) }}
spec:
{{ include "nuc-istio.renderDestinationRuleSpec" (dict "item" $item "tplContext" $tplContext) | nindent 2 }}
{{- end -}}

{{/* Compatibility aliases for older templates/docs naming. */}}
{{- define "helpers.tplvalues.render" -}}
{{- include "nuc-istio.tplvalues.render" . -}}
{{- end -}}

{{- define "helpers.app.fullname" -}}
{{- include "nuc-istio.fullname" . -}}
{{- end -}}

{{- define "helpers.app.labels" -}}
{{- include "nuc-istio.labels" . -}}
{{- end -}}

{{- define "helpers.app.genericAnnotations" -}}
{{- $generic := get .Values "generic" | default dict -}}
{{- toYaml (get $generic "annotations" | default dict) -}}
{{- end -}}

{{- define "helpers.capabilities.istiogateway.apiVersion" -}}
{{- include "nuc-istio.istiogateway.apiVersion" . -}}
{{- end -}}

{{- define "helpers.capabilities.istiovirtualservice.apiVersion" -}}
{{- include "nuc-istio.istiovirtualservice.apiVersion" . -}}
{{- end -}}

{{- define "helpers.capabilities.istiodestinationrule.apiVersion" -}}
{{- include "nuc-istio.istiodestinationrule.apiVersion" . -}}
{{- end -}}
