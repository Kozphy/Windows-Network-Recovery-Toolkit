{{- define "erp-platform.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "erp-platform.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{- define "erp-platform.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{- define "erp-platform.labels" -}}
helm.sh/chart: {{ include "erp-platform.chart" . }}
{{ include "erp-platform.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- define "erp-platform.selectorLabels" -}}
app.kubernetes.io/name: {{ include "erp-platform.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{- define "erp-platform.api.labels" -}}
{{ include "erp-platform.labels" . }}
app.kubernetes.io/component: api
{{- end }}

{{- define "erp-platform.api.selectorLabels" -}}
{{ include "erp-platform.selectorLabels" . }}
app.kubernetes.io/component: api
{{- end }}

{{- define "erp-platform.prometheus.labels" -}}
{{ include "erp-platform.labels" . }}
app.kubernetes.io/component: prometheus
{{- end }}

{{- define "erp-platform.prometheus.selectorLabels" -}}
{{ include "erp-platform.selectorLabels" . }}
app.kubernetes.io/component: prometheus
{{- end }}

{{- define "erp-platform.grafana.labels" -}}
{{ include "erp-platform.labels" . }}
app.kubernetes.io/component: grafana
{{- end }}

{{- define "erp-platform.grafana.selectorLabels" -}}
{{ include "erp-platform.selectorLabels" . }}
app.kubernetes.io/component: grafana
{{- end }}

{{- define "erp-platform.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "erp-platform.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}
