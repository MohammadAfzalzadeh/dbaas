kind delete cluster --name patroni

kind create cluster --config ./kind/kind-config.yaml  --name patroni 

docker build -t patroni ./patroni &&  kind load docker-image patroni --name patroni 
docker build -t wal-g ./wal-g     &&  kind load docker-image wal-g --name patroni 

docker build -t pgcat-config-watcher ./pgcat     &&  kind load docker-image pgcat-config-watcher --name patroni 
kind load docker-image ghcr.io/postgresml/pgcat --name patroni 



# kubectl delete -f ./kuberResources/patroni_k8s.yaml && 
kubectl apply -f ./kuberResources/patroni_k8s.yaml

# kubectl delete -f ./kuberResources/proxy.yaml &&
kubectl apply -f ./kuberResources/proxy.yaml

####################MINIO################
kind load docker-image quay.io/minio/minio  --name patroni

# kubectl delete -f ./kuberResources/minio_k8s.yaml && 
kubectl apply -f ./kuberResources/minio_k8s.yaml