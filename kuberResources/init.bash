cd /home/mmmubnt/Desktop/KarshenasiProject/dbaas

kubectl delete -f ./kuberResources

cd Replica &&   docker build -t dbaas-postgres_sync_replica  .
cd ../Master &&  docker build -t dbaas-postgres_primary  .

kind load docker-image dbaas-postgres_primary  --name pg-replication
kind load docker-image dbaas-postgres_sync_replica  --name pg-replication

cd /home/mmmubnt/Desktop/KarshenasiProject/dbaas

kubectl apply -f ./kuberResources


