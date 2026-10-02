kind delete cluster --name dbaas
kind create cluster --name dbaas
kind load docker-image afzalzademohammad/patroni:2.0.0 docker.io/traefik:v3.7.13 --name dbaas

helm upgrade --install traefik traefik/traefik \   
  --namespace traefik \
  --create-namespace \
  --wait

kubectl -n traefik port-forward svc/traefik 8080:80