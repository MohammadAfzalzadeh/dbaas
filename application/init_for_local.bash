kind delete cluster --name dbaas
kind create cluster --name dbaas
kind load docker-image minio/minio:RELEASE.2024-12-18T13-15-44Z minio/mc:RELEASE.2024-11-21T17-21-54Z docker.io/traefik:v3.7.13 debian:bookworm-slim afzalzademohammad/pgcat-config-watcher:2.0.0 --name dbaas

helm upgrade --install traefik traefik/traefik --namespace traefik --create-namespace --wait

kubectl -n traefik port-forward svc/traefik 8080:80