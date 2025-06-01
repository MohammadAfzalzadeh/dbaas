#####craete kuber cluster
kind delete cluster --name patroni
kind create cluster --config ./kind/kind-config.yaml  --name patroni 
#####build custom docker images
docker build -t patroni ./patroni 
docker build -t wal-g ./wal-g     
docker build -t pgcat-config-watcher ./pgcat  
#####load all docker images into cluster
kind load docker-image patroni --name patroni 
kind load docker-image wal-g --name patroni 
kind load docker-image pgcat-config-watcher --name patroni 
kind load docker-image ghcr.io/postgresml/pgcat --name patroni 
kind load docker-image quay.io/minio/minio  --name patroni
#######add longhorn storageclass####
# kubectl apply -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.1/deploy/longhorn.yaml
# kubectl create -f https://raw.githubusercontent.com/longhorn/longhorn/v1.8.1/examples/storageclass.yaml
#####apply all resources needed
# kubectl delete -f ./kuberResources/patroni_k8s.yaml && 
kubectl apply -f ./kuberResources/patroni_k8s.yaml
kubectl apply -f ./kuberResources/db_services_k8s.yaml
# kubectl delete -f ./kuberResources/proxy.yaml &&
kubectl apply -f ./kuberResources/proxy.yaml
# kubectl delete -f ./kuberResources/minio_k8s.yaml && 
kubectl apply -f ./kuberResources/minio_k8s.yaml