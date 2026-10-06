# Requires operator-created Secrets; see docs/security/secrets-management.md.
#####craete kuber cluster
kind delete cluster --name patroni
kind create cluster --image kindest/node:v1.30.0 --config ./kind/kind-config.yaml  --name patroni
#####build custom docker images
docker build -t dbaas/patroni:2.1.0 ./patroni
docker build -t dbaas/wal-g:3.0.7 ./wal-g
docker build -t dbaas/pgcat-config-watcher:1.1.1 ./pgcat
docker build -t dbaas/minio:RELEASE.2025-04-22T22-12-26Z ./minio
docker build -t dbaas/mc:RELEASE.2025-04-16T18-13-26Z -f minio/mc.Dockerfile ./minio
docker build -t dbaas/kubectl:1.30.0 ./tools/kubectl
kind load docker-image dbaas/mc:RELEASE.2025-04-16T18-13-26Z --name patroni
kind load docker-image dbaas/kubectl:1.30.0 --name patroni
#####load all docker images into cluster
kind load docker-image dbaas/patroni:2.1.0 --name patroni
kind load docker-image dbaas/wal-g:3.0.7 --name patroni
kind load docker-image dbaas/pgcat-config-watcher:1.1.1 --name patroni
kind load docker-image ghcr.io/postgresml/pgcat:v1.2.0 --name patroni
kind load docker-image dbaas/minio:RELEASE.2025-04-22T22-12-26Z  --name patroni
#######add longhorn storageclass####
# kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.1/deploy/longhorn.yaml
# kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.1/examples/storageclass.yaml
#####Install from helm
#helm uninstall minio-mvp && \
helm install minio-mvp ./helmCharts/minio -f ./helmCharts/minio/values.yaml
#helm uninstall patroni-mvp && \
helm install patroni-mvp ./helmCharts/patroni -f ./helmCharts/patroni/values-base.yaml
#helm uninstall pgcat-mvp && \
helm install pgcat-mvp ./helmCharts/pgcat -f ./helmCharts/pgcat/values.yaml
