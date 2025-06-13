kubectl delete deploy -n $1 `kubectl get deploy -n $1|awk '{print $1}'|grep -v NAME`
kubectl delete pod -n $1 `kubectl get pod -n $1|awk '{print $1}'|grep -v NAME`
kubectl delete svc -n $1 `kubectl get svc -n $1|awk '{print $1}'|grep -v NAME`

