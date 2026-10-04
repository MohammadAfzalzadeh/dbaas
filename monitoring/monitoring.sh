helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

kind load docker-image docker.io/grafana/grafana:12.3.0 quay.io/kiwigrid/k8s-sidecar:1.30.10 quay.io/minio/minio:RELEASE.2024-12-18T13-15-44Z grafana/rollout-operator:v0.32.0 quay.io/minio/mc:RELEASE.2024-11-21T17-21-54Z apache/kafka-native:4.1.0 docker.io/nginxinc/nginx-unprivileged:1.29-alpine grafana/mimir:3.0.0 docker.io/library/busybox:1.31.1  --name dbaas;
kind load docker-image docker.io/grafana/loki:3.5.7 docker.io/kiwigrid/k8s-sidecar:1.30.10 docker.io/grafana/loki-canary:3.5.7 memcached:1.6.39-alpine prom/memcached-exporter:v0.15.3 --name dbaas;
kind load docker-image docker.io/grafana/tempo:2.9.0 registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.17.0 quay.io/prometheus/node-exporter:v1.10.2 docker.io/grafana/alloy:v1.11.3 quay.io/prometheus-operator/prometheus-config-reloader:v0.81.0 --name dbaas
# kind load docker-image ghcr.io/grafana/helm-chart-toolbox-kubectl:0.1.2 --name dbaas

kubectl apply -f ./01-namespace.yaml

helm upgrade --install grafana grafana/grafana --namespace monitoring --version 10.1.5 -f ./02-grafana.yaml

helm upgrade --install mimir grafana/mimir-distributed --namespace monitoring --version 6.0.3 -f ./03-mimir.yaml 

helm upgrade --install loki grafana/loki --namespace monitoring --version 6.46.0 -f ./04-loki.yaml 

helm upgrade --install tempo grafana/tempo-distributed --namespace monitoring --version 1.56.2 -f ./05-tempo.yaml 

helm upgrade --install alloy grafana/k8s-monitoring --namespace monitoring --version 3.6.1 -f ./06-alloy.yaml 

kubectl apply -f ./manifests/remote-ingest/*.yaml

