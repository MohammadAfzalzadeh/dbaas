docker pull k8s-mirror.liara.ir/kube-state-metrics/kube-state-metrics:v2.17.0;
docker pull quay-mirror.liara.ir/prometheus/node-exporter:v1.10.2;
docker pull quay-mirror.liara.ir/prometheus-operator/prometheus-config-reloader:v0.81.0;
docker pull ghcr-mirror.liara.ir/grafana/helm-chart-toolbox-kubectl:0.1.2;

docker pull grafana/tempo:2.9.0;
docker pull grafana/alloy:v1.11.3;


docker tag grafana/tempo:2.9.0 docker.io/grafana/tempo:2.9.0;
docker tag k8s-mirror.liara.ir/kube-state-metrics/kube-state-metrics:v2.17.0 registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.17.0;
docker tag quay-mirror.liara.ir/prometheus/node-exporter:v1.10.2 quay.io/prometheus/node-exporter:v1.10.2;
docker tag grafana/alloy:v1.11.3 docker.io/grafana/alloy:v1.11.3;
docker tag quay-mirror.liara.ir/prometheus-operator/prometheus-config-reloader:v0.81.0 quay.io/prometheus-operator/prometheus-config-reloader:v0.81.0;
docker tag ghcr-mirror.liara.ir/grafana/helm-chart-toolbox-kubectl:0.1.2 ghcr.io/grafana/helm-chart-toolbox-kubectl:0.1.2;

kind load docker-image docker.io/grafana/tempo:2.9.0 registry.k8s.io/kube-state-metrics/kube-state-metrics:v2.17.0 quay.io/prometheus/node-exporter:v1.10.2 docker.io/grafana/alloy:v1.11.3 ghcr.io/grafana/helm-chart-toolbox-kubectl:0.1.2 quay.io/prometheus-operator/prometheus-config-reloader:v0.81.0 --name dbaas