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
#####Install from helm
#helm uninstall minio-mvc && \ 
helm install minio-mvc ./helmCharts/minio -f ./helmCharts/minio/values.yaml
#helm uninstall patroni-mvc && \ 
helm install patroni-mvc ./helmCharts/patroni -f ./helmCharts/patroni/values-base.yaml
#helm uninstall pgcat-mvc && \ 
helm install pgcat-mvc ./helmCharts/pgcat -f ./helmCharts/pgcat/values.yaml
