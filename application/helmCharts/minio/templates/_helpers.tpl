{{/* Scheduling selectors are supplied by the workload, never by the caller. */}}
{{- define "dbaas.scheduling" -}}
{{- $s := .settings -}}
{{- with $s.nodeSelector }}
nodeSelector: {{ toYaml . | nindent 2 }}
{{- end }}
{{- with $s.tolerations }}
tolerations: {{ toYaml . | nindent 2 }}
{{- end }}
{{- if $s.affinity }}
affinity: {{ toYaml $s.affinity | nindent 2 }}
{{- else if ne $s.antiAffinity "none" }}
{{- if not (has $s.antiAffinity (list "preferred" "required")) }}{{ fail "antiAffinity must be none, preferred or required" }}{{ end }}
affinity:
  podAntiAffinity:
    {{- if eq $s.antiAffinity "required" }}
    requiredDuringSchedulingIgnoredDuringExecution:
    - topologyKey: {{ $s.topologyKey | quote }}
      labelSelector:
        matchLabels: {{ toYaml .labels | nindent 10 }}
    {{- else }}
    preferredDuringSchedulingIgnoredDuringExecution:
    - weight: 100
      podAffinityTerm:
        topologyKey: {{ $s.topologyKey | quote }}
        labelSelector:
          matchLabels: {{ toYaml .labels | nindent 12 }}
    {{- end }}
{{- end }}
{{- if $s.topologySpreadConstraints }}
topologySpreadConstraints:
{{- range $constraint := $s.topologySpreadConstraints }}
- {{ toYaml (omit $constraint "labelSelector" "matchLabelKeys") | nindent 2 | trim }}
  labelSelector:
    matchLabels: {{ toYaml $.labels | nindent 6 }}
{{- end }}
{{- end }}
{{- end }}
