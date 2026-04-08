# Cilium Gateway API + LAN Exposure Runbook
## deploy-confidence-service on Talos with Cilium Gateway API, LoadBalancer IPAM, and L2 Announcements

---

## 1. Goal

Expose `deploy-confidence-service` on the LAN over HTTPS using:

- **Cilium Gateway API**
- **Gateway + HTTPRoute**
- **Cilium LoadBalancer IPAM**
- **Cilium L2 Announcements**

Then later place **Cloudflare** in front.

---

## 2. Environment

### Cluster
- Kubernetes: `v1.35.0`
- Talos nodes:
  - `talos-4lc-a3a` → `192.168.0.241`
  - `talos-ri2-xwg` → `192.168.0.242`
  - `talos-ncs-xi5` → `192.168.0.243`
  - `talos-w1` → `192.168.0.33`
  - `talos-w2` → `192.168.0.245`

### LAN
- Subnet: `192.168.0.0/24`
- Router: `192.168.0.1`
- Jumpbox IP: `192.168.0.28`
- Jumpbox NIC: `ens18`
- Talos node LAN NIC: `ens18`
- DHCP range: `192.168.0.20 - 192.168.0.89`

### App
- Namespace: `deploy-confidence`
- Service: `deploy-confidence-service`
- Service port: `8000`

---

## 3. Verify backend service first

```bash
kubectl get svc -n deploy-confidence
kubectl get svc deploy-confidence-service -n deploy-confidence -o yaml
kubectl get pods -n deploy-confidence -o wide
```

Expected service:

- name: `deploy-confidence-service`
- type: `ClusterIP`
- port: `8000`

## 4. Cilium version and Helm state

Check installed release:

```shell
helm ls -n kube-system
helm history cilium -n kube-system
helm get metadata cilium -n kube-system
helm get values cilium -n kube-system
```

Important lesson:

- `cilium-values.yaml` controls configuration
- the Helm command/chart controls the version
- installed chart/app version in this setup: 1.19.2

## 5. Initial Gateway API problem

Symptom

`GatewayClass cilium` stayed unaccepted or controller crashed.

Root cause

`TLSRoute` CRD version mismatch:

- Cilium expected: `TLSRoute v1alpha2`
- installed Gateway API bundle had: TLSRoute v1

This caused logs like:

```shell
failed to setup field indexer ... no matches for kind "TLSRoute" in version "gateway.networking.k8s.io/v1alpha2"
```
## 6. Remove Gateway API downgrade protection policy

The cluster had a policy blocking installation of Gateway API versions older than v1.5.0.

Delete it so the compatible Gateway API version can be installed:

```shell
kubectl delete validatingadmissionpolicybinding safe-upgrades.gateway.networking.k8s.io
kubectl delete validatingadmissionpolicy safe-upgrades.gateway.networking.k8s.io
```

These were only guardrails, not runtime dependencies.

## 7. Install compatible Gateway API CRDs

Install the Gateway API version compatible with the running Cilium version.

### Standard CRDs
```shell
kubectl apply -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/standard-install.yaml
```
### Experimental CRDs

Use server-side apply:

```shell
kubectl apply --server-side -f https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.4.1/experimental-install.yaml
```
Verify TLSRoute version
```shell
kubectl get crd tlsroutes.gateway.networking.k8s.io -o yaml | grep -A12 versions:
```

Expected:

- name: `v1alpha2`

## 8. Update Cilium values

Use Helm-managed Gateway API and GatewayClass creation.

`cilium-values.yaml`
```yaml
kubeProxyReplacement: "true"

k8sServiceHost: "192.168.0.210"
k8sServicePort: 6443

ipam:
  mode: "kubernetes"

routingMode: "tunnel"
tunnelProtocol: "vxlan"

gatewayAPI:
  enabled: true
  gatewayClass:
    create: true

l2announcements:
  enabled: true

externalIPs:
  enabled: true

k8sClientRateLimit:
  qps: 20
  burst: 40

resources:
  requests:
    cpu: "1"
    memory: 512Mi
  limits:
    cpu: "3"
    memory: 2Gi

hubble:
  enabled: true

  relay:
    enabled: true
    replicas: 2
    resources:
      requests:
        cpu: 200m
        memory: 256Mi
      limits:
        cpu: "1"
        memory: 512Mi
    prometheus:
      enabled: true
      serviceMonitor:
        enabled: true

  ui:
    enabled: true

  metrics:
    enabled:
      - dns:query;ignoreAAAA
      - drop:labelsContext=source_namespace,destination_namespace,traffic_direction
      - tcp
      - flow:labelsContext=source_namespace,source_workload,destination_namespace,destination_workload,traffic_direction
      - httpV2:labelsContext=source_namespace,source_workload,destination_namespace,destination_workload,traffic_direction
    serviceMonitor:
      enabled: true

cgroup:
  autoMount:
    enabled: false
  hostRoot: /sys/fs/cgroup

securityContext:
  capabilities:
    ciliumAgent:
      - CHOWN
      - KILL
      - NET_ADMIN
      - NET_RAW
      - IPC_LOCK
      - SYS_ADMIN
      - SYS_RESOURCE
      - DAC_OVERRIDE
      - FOWNER
      - SETGID
      - SETUID
    cleanCiliumState:
      - NET_ADMIN
      - SYS_ADMIN
      - SYS_RESOURCE

prometheus:
  enabled: true
  serviceMonitor:
    enabled: true

operator:
  prometheus:
    enabled: true
    serviceMonitor:
      enabled: true

  relay:
    prometheus:
      enabled: true
      serviceMonitor:
        enabled: true
```
Important note

Do not enable both:

```yaml
- http
- httpV2
```

in Hubble metrics at the same time.

That caused crashloops with:

```yaml
failed to setup hubble metrics: plugin http conflicts with plugin httpV2
```

Keep only `httpV2`.

## 9. Upgrade Cilium with Helm
```shell
helm upgrade cilium cilium/cilium \
  --namespace kube-system \
  -f cilium-values.yaml
```

Restart if needed:

```shell
kubectl -n kube-system rollout restart ds/cilium
kubectl -n kube-system rollout restart deployment/cilium-operator
```

Verify:

```shell
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec -it <cilium-pod> -- cilium status
kubectl get gatewayclass
kubectl describe gatewayclass cilium
```

Expected:

- all Cilium pods healthy
- `GatewayClass cilium`
- `ACCEPTED=True`

## 10. Create TLS cert and key for LAN testing

Create a self-signed cert for the LAN hostname.

Example hostname
- `deploy-confidence.lab.local`

Generate cert and key
```shell
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout tls.key \
  -out tls.crt \
  -subj "/CN=deploy-confidence.lab.local"
```

This creates:

- `tls.key`
- `tls.crt`

## 11. Create Kubernetes TLS secret

Create the secret in the app namespace:

```shell
kubectl -n deploy-confidence create secret tls deploy-confidence-lan-tls \
  --cert=tls.crt \
  --key=tls.key
```

Verify:

```shell
kubectl get secret -n deploy-confidence deploy-confidence-lan-tls
```

## 12. Create Gateway
`deploy-confidence-gateway.yaml`
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: Gateway
metadata:
  name: deploy-confidence-gateway
  namespace: deploy-confidence
spec:
  gatewayClassName: cilium
  listeners:
    - name: http
      protocol: HTTP
      port: 80
      hostname: deploy-confidence.lab.local
      allowedRoutes:
        namespaces:
          from: Same
    - name: https
      protocol: HTTPS
      port: 443
      hostname: deploy-confidence.lab.local
      tls:
        mode: Terminate
        certificateRefs:
          - kind: Secret
            name: deploy-confidence-lan-tls
      allowedRoutes:
        namespaces:
          from: Same
```

Apply:

```shell
kubectl apply -f deploy-confidence-gateway.yaml
```

## 13. Create HTTPRoute
`deploy-confidence-httproute.yaml`
```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata:
  name: deploy-confidence-route
  namespace: deploy-confidence
spec:
  parentRefs:
    - name: deploy-confidence-gateway
  hostnames:
    - deploy-confidence.lab.local
  rules:
    - matches:
        - path:
            type: PathPrefix
            value: /
      backendRefs:
        - name: deploy-confidence-service
          port: 8000
```

Apply:

```shell
kubectl apply -f deploy-confidence-httproute.yaml
```

## 14. Verify Gateway and Route
```shell
kubectl get gateway -n deploy-confidence
kubectl describe gateway deploy-confidence-gateway -n deploy-confidence

kubectl get httproute -n deploy-confidence
kubectl describe httproute deploy-confidence-route -n deploy-confidence
```

Expected:

- `Gateway Accepted=True`
- eventually `Programmed=True`
- `HTTPRoute Accepted=True`
- backend references resolved

## 15. Check generated Gateway Service

Cilium creates a service like:

```shell
kubectl get svc -n deploy-confidence
kubectl get svc cilium-gateway-deploy-confidence-gateway -n deploy-confidence -o yaml
```

At first it showed:

- type: `LoadBalancer`
- external IP: `<pending>`

This meant the Gateway was fine, but no LAN IP was assigned yet.

## 16. Define a LoadBalancer IP pool

Pick a free static range outside DHCP.

Chosen range

- `192.168.0.230 - 192.168.0.239`

`lb-pool.yaml`
```yaml
apiVersion: cilium.io/v2
kind: CiliumLoadBalancerIPPool
metadata:
  name: lan-pool
spec:
  blocks:
    - start: 192.168.0.230
      stop: 192.168.0.239
```

Apply:

```shell
kubectl apply -f lb-pool.yaml
```

Verify:

```shell
kubectl get ciliumloadbalancerippools -o yaml
```
## 17. Confirm node LAN interface

Check the interface on a real Cilium pod:

```shell
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec -it <cilium-pod> -- ip -4 -br addr
  #main proof for the interface
ip -br link
```

Confirmed node interface:

- `ens18`
## 18. Create L2 announcement policy

The first L2 policy used the wrong selector and matched no services.

### Wrong selector example
```yaml
serviceSelector:
  matchExpressions:
    - key: io.kubernetes.service.name
      operator: Exists
```

This was wrong because `serviceSelector` matches service labels, not the service name field.

Correct policy

Check service labels first:

```shell
kubectl -n deploy-confidence get svc cilium-gateway-deploy-confidence-gateway --show-labels
```

The Gateway Service had labels including:

- `io.cilium.gateway/owning-gateway=deploy-confidence-gateway`
`l2-policy.yaml`
```yaml
apiVersion: cilium.io/v2alpha1
kind: CiliumL2AnnouncementPolicy
metadata:
  name: lan-l2-policy
spec:
  serviceSelector:
    matchLabels:
      io.cilium.gateway/owning-gateway: deploy-confidence-gateway
  interfaces:
    - ens18
  externalIPs: true
  loadBalancerIPs: true
```

Apply:

```shell
kubectl apply -f l2-policy.yaml
```

Verify:
```shell
kubectl get ciliuml2announcementpolicies lan-l2-policy -o yaml
```
## 19. Troubleshooting: why the LB IP was still unreachable
Symptom

Even after the pool and L2 policy were created:

- ARP failed
- `192.168.0.230` had no MAC
- TCP 80/443 failed

Commands used
```shell
ping -c 3 192.168.0.230
arp -an | grep 192.168.0.230 || ip neigh | grep 192.168.0.230
sudo arping -I ens18 192.168.0.230 -c 5
nc -vz 192.168.0.230 80
nc -vz 192.168.0.230 443
```
### Root cause

Two Cilium agents were crashlooping because of this:

- `failed to setup hubble metrics: plugin http conflicts with plugin httpV2`

This left Cilium in a mixed, unhealthy state.

Fix

- Remove `- http` from Hubble metrics, keep only `httpV2`, then run:

```shell
helm upgrade cilium cilium/cilium \
  --namespace kube-system \
  -f cilium-values.yaml

kubectl -n kube-system rollout restart ds/cilium
kubectl -n kube-system rollout restart deployment/cilium-operator
```
## 20. Final healthy Cilium verification

Check:

```shell
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec -it <cilium-pod> -- cilium status
```

Expected:

- all Cilium pods healthy
- Hubble metrics OK
- no crashloops
- LoadBalancer IPAM working
- L2 announcements working

## 21. Final LAN LoadBalancer verification

After Cilium converged, the Gateway service got:

- `EXTERNAL-IP = 192.168.0.230`

Check:

```shell
kubectl get svc -n deploy-confidence cilium-gateway-deploy-confidence-gateway -o wide
kubectl get gateway -n deploy-confidence
kubectl describe gateway deploy-confidence-gateway -n deploy-confidence
```

Expected:

- Gateway Programmed=True
- Address 192.168.0.230

Then verify ARP and TCP:

```shell
sudo arping -I ens18 192.168.0.230 -c 5
nc -vz 192.168.0.230 80
nc -vz 192.168.0.230 443
```

Expected:

- ARP replies received
- ports 80 and 443 reachable

## 22. Test application through the Gateway

Use curl with SNI/hostname resolution:

```shell
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/health
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/details
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/score
```
Expected results
- `/` → likely `{"detail":"Not Found"}`
- `/health` → healthy status JSON
- `/details` → full scoring/details JSON
- `/score` → score summary JSON

`/` returning 404 is an app behavior, not a Gateway issue.

## 23. Access from browser on LAN

Add a hosts file entry on the client machine.

Windows hosts file
- `C:\Windows\System32\drivers\etc\hosts`

Add:

- `192.168.0.230 deploy-confidence.lab.local`

Then open:

- `https://deploy-confidence.lab.local/health`
- `https://deploy-confidence.lab.local/details`
- `https://deploy-confidence.lab.local/score`

> Because the cert is self-signed, the browser will show a warning.
Accept the risk for LAN testing.

## 24. Final working path
Browser / curl
```shell
→ deploy-confidence.lab.local
→ 192.168.0.230
→ Cilium Gateway LoadBalancer Service
→ Cilium Gateway
→ HTTPRoute
→ deploy-confidence-service:8000
→ FastAPI backend
```
## 25. Validation commands summary
Backend
```shell
kubectl get svc -n deploy-confidence
kubectl get pods -n deploy-confidence -o wide
```
Gateway API
```shell
kubectl get gatewayclass
kubectl describe gatewayclass cilium

kubectl get gateway -n deploy-confidence
kubectl describe gateway deploy-confidence-gateway -n deploy-confidence

kubectl get httproute -n deploy-confidence
kubectl describe httproute deploy-confidence-route -n deploy-confidence
```
Cilium
```shell
kubectl -n kube-system get pods -l k8s-app=cilium -o wide
kubectl -n kube-system exec -it <cilium-pod> -- cilium status
```
LB + L2
```shell
kubectl get ciliumloadbalancerippools -o yaml
kubectl get ciliuml2announcementpolicies -o yaml
kubectl -n deploy-confidence get svc cilium-gateway-deploy-confidence-gateway --show-labels
```
LAN reachability
```shell
sudo arping -I ens18 192.168.0.230 -c 5
nc -vz 192.168.0.230 80
nc -vz 192.168.0.230 443
```
App test
```shell
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/health
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/details
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/score
```
## 26. Final outcome

The cluster was stabilized and the app is now available on the LAN over HTTPS.

Final hostname
- `deploy-confidence.lab.local`

Final LAN IP
- 192.168.0.230

Working endpoints
- `/health`
- `/details`
- `/score`
