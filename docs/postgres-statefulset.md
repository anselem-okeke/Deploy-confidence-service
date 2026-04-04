# PostgreSQL StatefulSet Package Setup for Deploy Confidence

## Purpose

This document explains how the PostgreSQL package was set up for the `deploy-confidence` application using a Kubernetes `StatefulSet`, why this pattern was chosen, what each manifest does, and the correct deployment order.

The goal of this setup is to provide:

- stable database identity
- persistent storage
- predictable pod naming
- simpler application connectivity
- a cleaner Kubernetes-native stateful design than a plain Deployment

---

# Why we moved to StatefulSet

At first, PostgreSQL was deployed using a normal `Deployment` plus a standalone PVC.

That worked as a first functional step, but it was not the best structure for a database because:

- PostgreSQL is a **stateful workload**
- stateful workloads need stable identity and persistent storage
- `StatefulSet` is the Kubernetes-native controller for this kind of workload

A `StatefulSet` gives:

- stable pod names such as `deploy-confidence-postgres-0`
- stable storage per pod
- predictable startup/shutdown behavior
- better long-term structure for database workloads

So the PostgreSQL package was redesigned into a `StatefulSet` package.

---

# Package components

The PostgreSQL package consists of these manifests:

1. `k8s/postgres-storageclass.yaml`
2. `k8s/postgres-secret.yaml`
3. `k8s/postgres-headless-service.yaml`
4. `k8s/postgres-service.yaml`
5. `k8s/postgres-statefulset.yaml`

---

# 1. StorageClass

## File
`k8s/postgres-storageclass.yaml`

## Purpose

This StorageClass defines how Longhorn provisions storage for PostgreSQL.

We used a dedicated StorageClass so the database storage behavior is explicit and separated from the default cluster storage behavior.

## Manifest

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: longhorn-retain
provisioner: driver.longhorn.io
allowVolumeExpansion: true
reclaimPolicy: Retain
volumeBindingMode: Immediate
parameters:
  numberOfReplicas: "1"
  staleReplicaTimeout: "30"
  fsType: "ext4"
```

### Why this setup
- numberOfReplicas: "1" was chosen because the lab cluster had storage scheduling issues with multi-replica Longhorn volume placement
- reclaimPolicy: Retain keeps the underlying storage safer during object deletion
- fsType: ext4 is a straightforward and supported choice for PostgreSQL PVCs

### 2. Secret
File

`k8s/postgres-secret.yaml`

Purpose

This Secret provides PostgreSQL credentials and database name.

Manifest
```shell
apiVersion: v1
kind: Secret
metadata:
  name: deploy-confidence-postgres-secret
  namespace: deploy-confidence
type: Opaque
stringData:
  POSTGRES_DB: deploy_confidence
  POSTGRES_USER: deploy_confidence
  POSTGRES_PASSWORD: change_me
```
Why this setup

The Postgres container expects these values:

- POSTGRES_DB
- POSTGRES_USER
- POSTGRES_PASSWORD

These are injected into the container through environment variables.

### 3. Headless Service
File

`k8s/postgres-headless-service.yaml`

Purpose

The headless service exists for the StatefulSet itself.

It gives each PostgreSQL pod a stable network identity.

Manifest
```shell
apiVersion: v1
kind: Service
metadata:
  name: deploy-confidence-postgres-headless
  namespace: deploy-confidence
spec:
  clusterIP: None
  selector:
    app: deploy-confidence-postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
```
Why we need it

A StatefulSet uses a governing service to provide stable DNS identity.

For example, the Postgres pod gets a stable DNS name like:

```shell
deploy-confidence-postgres-0.deploy-confidence-postgres-headless.deploy-confidence.svc.cluster.local
```

This is useful for StatefulSet identity and stable pod naming.

### 4. Normal ClusterIP Service
File

`k8s/postgres-service.yaml`

Purpose

This is the service the application uses to connect to PostgreSQL.

Manifest
```shell
apiVersion: v1
kind: Service
metadata:
  name: deploy-confidence-postgres
  namespace: deploy-confidence
spec:
  selector:
    app: deploy-confidence-postgres
  ports:
    - name: postgres
      port: 5432
      targetPort: 5432
  type: ClusterIP
```
Why we need it

The application should not have to connect directly to the StatefulSet pod DNS name.

Instead, it should connect to a simple service name:

```shell
deploy-confidence-postgres:5432
```

So the roles are:

- `headless service → StatefulSet identity`
- `ClusterIP service → app connectivity`

This gives us a clean separation of concerns.

### 5. StatefulSet
File

`k8s/postgres-statefulset.yaml`

Purpose

This is the actual PostgreSQL workload definition.

Manifest
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: deploy-confidence-postgres
  namespace: deploy-confidence
spec:
  serviceName: deploy-confidence-postgres-headless
  replicas: 1
  selector:
    matchLabels:
      app: deploy-confidence-postgres
  template:
    metadata:
      labels:
        app: deploy-confidence-postgres
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: postgres
          image: postgres:16
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 5432
              name: postgres
          env:
            - name: POSTGRES_DB
              valueFrom:
                secretKeyRef:
                  name: deploy-confidence-postgres-secret
                  key: POSTGRES_DB
            - name: POSTGRES_USER
              valueFrom:
                secretKeyRef:
                  name: deploy-confidence-postgres-secret
                  key: POSTGRES_USER
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: deploy-confidence-postgres-secret
                  key: POSTGRES_PASSWORD
            - name: PGDATA
              value: /var/lib/postgresql/data/pgdata
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 6
          livenessProbe:
            exec:
              command:
                - sh
                - -c
                - pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
            initialDelaySeconds: 20
            periodSeconds: 20
            timeoutSeconds: 3
            failureThreshold: 6
          resources:
            requests:
              cpu: "100m"
              memory: "256Mi"
            limits:
              cpu: "500m"
              memory: "512Mi"
  volumeClaimTemplates:
    - metadata:
        name: postgres-data
      spec:
        accessModes:
          - ReadWriteOnce
        storageClassName: longhorn-retain
        resources:
          requests:
            storage: 5Gi
```
Important design decisions
### 1. Why `serviceName` points to the headless service
```yaml
serviceName: deploy-confidence-postgres-headless
```

- The StatefulSet must use the headless service because that service provides the stable identity mechanism for the StatefulSet pod.

### 2. Why PGDATA is set
```yaml
- name: PGDATA
  value: /var/lib/postgresql/data/pgdata
```

- This was required because PostgreSQL failed when initializing directly in the root of the mounted PVC.

The error was:

```shell
initdb: error: directory "/var/lib/postgresql/data" exists but is not empty
initdb: detail: It contains a lost+found directory, perhaps due to it being a mount point.
```

To fix that, PostgreSQL was told to initialize in a subdirectory:

`/var/lib/postgresql/data/pgdata`

That avoids the lost+found issue.

### 3. Why volumeClaimTemplates is used

- This is the proper StatefulSet storage pattern.

- Instead of creating a standalone PVC separately, the StatefulSet creates its own persistent volume claim for the pod.

- The generated PVC becomes something like:

```shell
postgres-data-deploy-confidence-postgres-0
```

- This matches the StatefulSet identity and is cleaner than mixing StatefulSet with an external hand-managed PVC.

### 4. Why there are two services

This is the most important conceptual part.

### Headless service

- Used by the StatefulSet for stable pod identity.

### Normal ClusterIP service

- Used by the application to connect to PostgreSQL using a simple service name.

So:

`deploy-confidence-postgres-headless` → StatefulSet internal identity
`deploy-confidence-postgres` → application-facing DB connection target

### Application database connection

The application secret should use the normal PostgreSQL service, not the headless service.

Correct value:
```yaml

apiVersion: v1
kind: Secret
metadata:
  name: deploy-confidence-secret
  namespace: deploy-confidence
type: Opaque
stringData:
  DATABASE_URL: "postgresql+psycopg://deploy_confidence:change_me@deploy-confidence-postgres:5432/deploy_confidence"
```
Why this is correct

Because the app should connect to the normal ClusterIP service:

```yaml
deploy-confidence-postgres:5432
```

and not directly to the StatefulSet pod DNS unless there is a special reason.

### Correct deployment order

Apply the PostgreSQL package in this order:

```shell
kubectl apply -f k8s/postgres-storageclass.yaml
kubectl apply -f k8s/postgres-secret.yaml
kubectl apply -f k8s/postgres-headless-service.yaml
kubectl apply -f k8s/postgres-service.yaml
kubectl apply -f k8s/postgres-statefulset.yaml
```

Then verify:

```shell
kubectl -n deploy-confidence get pods -o wide
kubectl -n deploy-confidence get pvc
kubectl -n deploy-confidence get svc
kubectl -n deploy-confidence get endpoints
kubectl -n deploy-confidence logs statefulset/deploy-confidence-postgres
```
### What success looks like

Expected state:

Pod
```shell
deploy-confidence-postgres-0   1/1 Running
```
PVC
```shell
postgres-data-deploy-confidence-postgres-0   Bound
```
Services
```shell
deploy-confidence-postgres
deploy-confidence-postgres-headless
```
Endpoints

Both services point to the Postgres pod IP, for example:

```shell
deploy-confidence-postgres            10.244.x.x:5432
deploy-confidence-postgres-headless   10.244.x.x:5432
```
### How the app deployment fits into this

Once PostgreSQL is healthy, restart the application:

```shell
kubectl -n deploy-confidence rollout restart deployment deploy-confidence-service
kubectl -n deploy-confidence get pods -w
kubectl -n deploy-confidence logs deployment/deploy-confidence-service --tail=100
```
The app should then be able to connect using:

```shell
deploy-confidence-postgres:5432
```

through the normal ClusterIP service.

### Final architecture summary
PostgreSQL package structure
- `StorageClass` → defines Longhorn storage behavior
- `Secret` → provides DB credentials
- `Headless Service` → provides StatefulSet identity
- `ClusterIP Service` → provides application connectivity
- `StatefulSet` → runs the PostgreSQL database with stable identity and storage

###Connectivity model
- StatefulSet identity
```shell
deploy-confidence-postgres-0.deploy-confidence-postgres-headless.deploy-confidence.svc.cluster.local
```
- Application DB host
```shell
deploy-confidence-postgres:5432
```
### Final conclusion

The PostgreSQL package was redesigned into a proper Kubernetes StatefulSet package so that:

- PostgreSQL runs as a stateful workload
- storage is managed in a StatefulSet-native way
- the pod gets stable identity
- the application gets a simple service endpoint
- the earlier PVC mount issue with lost+found is avoided
- the cluster setup is closer to a clean enterprise-style structure than the original Deployment-based design