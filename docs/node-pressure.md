## Kubernetes Node Pressure Incident Runbook

Use this when you see signs like:
- many pods becoming Evicted
- DiskPressure=True on a node
- events mentioning ephemeral-storage
- monitoring pods restarting or churning
- many Completed, Failed, or ContainerStatusUnknown pods

1. Confirm the incident
   Commands:
  ```shell
 kubectl get nodes
   kubectl describe node <node-name>
   kubectl get events -A --sort-by=.lastTimestamp | tail -n 100
```

   Check for:
   - DiskPressure=True
   - MemoryPressure=True
   - ephemeral-storage warnings
   - repeated pod evictions

2. Isolate the affected node
   - Prevent new workloads from landing on the bad node:
  ```shell
 kubectl cordon <node-name>
```

   Do not uncordon it until the node is stable again.

3. Reduce workload churn
   - Scale down noncritical or noisy workloads that are repeatedly restarting or being recreated:
  ```shell
 kubectl scale deployment <name> -n <namespace> --replicas=0
```

   Typical candidates:
   - test workloads
   - demo apps
   - unstable development services
   - anything causing repeated churn

4. Watch critical platform components
   - Focus on the namespaces that matter first:
```shell
kubectl get pods -n monitoring -w
kubectl get pods -n logging -w
```

   Verify recovery of:
   - Prometheus
   - Grafana
   - Alertmanager
   - Loki
   - storage components

5. Clean up stale pod objects
   - Delete succeeded and failed pod objects:
  ```shell
 kubectl delete pod -A --field-selector=status.phase=Succeeded
   kubectl delete pod -A --field-selector=status.phase=Failed
```

   - Delete evicted pods:
   ```shell
kubectl get pods -A | grep Evicted | awk '{print "kubectl delete pod -n " $1 " " $2}' | sh
```

   - Find unknown-state pods:
   ```shell
kubectl get pods -A | grep ContainerStatusUnknown
```

   - Force-delete only the specific stuck pods you confirm are stale:
   ```shell
kubectl delete pod <pod-name> -n <namespace> --force --grace-period=0
```

6. Inspect node/runtime health
   - Check cluster resource state:
  ```shell
 kubectl top nodes
   kubectl top pods -A
```

   - On Talos, inspect kubelet, containerd, and kernel logs:
  ```shell
 talosctl -n <node-ip> logs kubelet | tail -n 100
   talosctl -n <node-ip> logs containerd | tail -n 100
   talosctl -n <node-ip> dmesg | tail -n 100
```

   Look for:
   - eviction manager activity
   - image garbage collection
   - container runtime errors
   - mount/shim/sandbox failures
   - OOM kills
   - filesystem issues

7. Recover the node
   If the issue is ephemeral-storage pressure:
   - keep the node cordoned
   - allow image/container garbage collection to run
   - remove workload churn
   - verify pressure clears

   If the runtime still looks unstable, reboot the node:
   talosctl -n <node-ip> reboot

8. Recheck node condition
```shell
kubectl describe node <node-name>
   kubectl get nodes
```

   Only continue when:
   - DiskPressure=False
   - MemoryPressure=False
   - the node is stable
   - critical platform workloads are healthy

9. Bring workloads back gradually
   - Resume important workloads one at a time:
 ```shell
  kubectl scale deployment <name> -n <namespace> --replicas=1
```
   If needed, temporarily pin important workloads to a healthy node during recovery.

10. Resume application validation last
    Only return to app debugging after:
    - node pressure is cleared
    - monitoring is healthy
    - stale pods are cleaned up
    - platform services are stable

Quick checklist
1. Check nodes and recent events
2. Identify pressure type (disk, memory, runtime)
3. Cordon affected node
4. Scale down noisy workloads
5. Watch monitoring/logging recover
6. Delete stale Succeeded/Failed/Evicted pods
7. Force-delete only specific unknown-state pods
8. Inspect kubelet/containerd/dmesg
9. Reboot node if runtime remains unstable
10. Bring workloads back gradually
11. Resume app validation last