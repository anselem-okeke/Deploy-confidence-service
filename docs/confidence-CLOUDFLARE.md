# Cloudflare Tunnel Setup Runbook
## deploy-confidence-service behind Cilium Gateway and Cloudflare

This document captures the full Cloudflare setup we performed after the LAN exposure of `deploy-confidence-service` was already working.

---

## 1. Starting point

Before Cloudflare, the application was already reachable on the LAN through the Cilium Gateway.

### Internal/LAN working state

- Internal Gateway hostname: `deploy-confidence.lab.local`
- Gateway LAN IP: `192.168.0.230`
- Backend service: `deploy-confidence-service`
- Namespace: `deploy-confidence`

### Verified working LAN endpoints

```text
https://deploy-confidence.lab.local/health
https://deploy-confidence.lab.local/details
https://deploy-confidence.lab.local/score
```

### Verified working LAN curl test
```shell
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/health
```
That returned the application health JSON successfully.

## 2. Goal

> Expose the already-working LAN application publicly through Cloudflare, without opening inbound ports directly to the homelab.

The target public hostname became:

```shell
deploy.anselemokeke.dpdns.org
```
## 3. Why Cloudflare Tunnel was chosen

Cloudflare Tunnel was used because it provides:

- outbound-only tunnel connectivity from the jumpbox to Cloudflare
- no need for direct public inbound port forwarding to the LAN
- a clean public hostname in front of the existing internal Gateway
- simple layering:
  - browser
  - Cloudflare
  - cloudflared
  - Cilium Gateway
  - HTTPRoute
  - backend service

## 4. Cloudflare prerequisites

At the start of this setup:

- the domain already existed in Cloudflare
- no `cloudflared` was installed yet on the jumpbox
- no tunnel was installed yet on the jumpbox
- the public hostname route did not yet exist

## 5. Create the tunnel in Cloudflare
Cloudflare dashboard path

Open the Cloudflare dashboard and go to:

- Cloudflare One
- Networks
- Connectors
- Cloudflare Tunnels

Then:

- Click Create a tunnel
- Choose Cloudflared
- Name the tunnel:
```shell
deploy-confidence-tunnel
```
- Save the tunnel

After saving, Cloudflare displays the token-based Linux install command for the tunnel service.

## 6. Install cloudflared on the jumpbox

On the jumpbox, install Cloudflare Tunnel client:

```shell
mkdir -p ~/cloudflare
cd ~/cloudflare

wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

If dependencies fail:

```shell
sudo apt-get update
sudo apt-get install -f -y
```

Verify install:

```shell
cloudflared --version
```
## 7. Install the tunnel as a system service

Back in Cloudflare, copy the tunnel install command shown by the dashboard.

It looks like:

```shell
sudo cloudflared service install <TUNNEL_TOKEN>
```

Run that on the jumpbox.

Then enable and verify the service:

```shell
sudo systemctl enable cloudflared
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
journalctl -u cloudflared -f
```
Expected result

The service should be active and the logs should show the tunnel registering multiple connections to Cloudflare.

Example pattern:

```shell
Registered tunnel connection ...
```

At this point the tunnel itself was healthy.

## 8. Important UI mistake encountered

At first, the wrong route type was opened in Cloudflare.

We landed on the private hostname / private network setup flow, which is meant for:

- private network resources
- Cloudflare One client / WARP-based access

That was not correct for this use case.

Correct choice

We needed the public hostname / published application flow instead.

So after going back, we opened the tunnel and used the route type for:

- Published applications
- Add a public hostname

## 9. Create the public hostname route

Inside the deploy-confidence-tunnel, add a public hostname.

Correct public hostname
- Subdomain: `deploy`
- Domain: `anselemokeke.dpdns.org`

This creates:

```shell
deploy.anselemokeke.dpdns.org
```
Important typo issue encountered

- A hostname typo caused confusion during testing.

- The configured hostname was:

```shell
deploy.anselemokeke.dpdns.org
```

But testing was initially done against a differently spelled domain.

This caused resolution/routing mismatch until the correct hostname was used consistently.

## 10. Configure the origin service

The Cloudflare Tunnel public hostname needed to point to the existing LAN Gateway origin.

### Service/origin settings
- Type: `HTTPS`
- Origin URL: `192.168.0.230:443`

> This means Cloudflare Tunnel forwards public traffic to the Cilium Gateway HTTPS listener on the LAN IP.

## 11. Initial origin TLS issue

After the route was added, public access failed with Cloudflare 502.

Tunnel log error
```shell
tls: failed to verify certificate: x509: certificate relies on legacy Common Name field, use SANs instead
```
### Meaning

Cloudflare Tunnel could reach the origin, but the certificate presented by the origin used only the old Common Name style and did not include a proper SAN entry.

At that point:

- public DNS worked
- tunnel was healthy
- Cloudflare reached the jumpbox
- jumpbox reached the origin
- but origin certificate validation failed

## 12. Temporary working fix: No TLS Verify

To get the public route working immediately, the tunnel origin TLS settings were adjusted.

Cloudflare origin settings used

Under the public hostname route:

### TLS settings
- Origin Server Name: `deploy-confidence.lab.local`
- No TLS Verify: `ON`
### HTTP settings
- HTTP Host Header: `deploy-confidence.lab.local`
### Why these settings mattered

Origin Server Name

The internal Gateway and certificate were built around:

```shell
deploy-confidence.lab.local
```
HTTP Host Header

The Gateway/HTTPRoute hostname matching also used:

```shell
deploy-confidence.lab.local
```

So although the public request came in for:

```shell
deploy.anselemokeke.dpdns.org
```

the tunnel had to rewrite the request correctly for the internal Gateway.

No TLS Verify

> This disabled strict origin certificate verification, allowing the request to work even though the internal cert was not yet acceptable to cloudflared.

## 13. Public route worked with No TLS Verify

After those settings were applied, public access worked.

Working public endpoints
```shell
https://deploy.anselemokeke.dpdns.org/health
https://deploy.anselemokeke.dpdns.org/details
https://deploy.anselemokeke.dpdns.org/score
```

> At this stage, the public application was working, but the origin certificate was still not properly trusted.

## 14. Clean-up goal after public success

> After getting the public route working with No TLS Verify, the next goal was to fix origin TLS properly so that verification could be turned back on.

The objective was:

- create a proper SAN certificate
- sign it with a CA
- make the jumpbox trust that CA
- disable No TLS Verify

## 15. Create a local CA

A local CA was created on the jumpbox.

Working directory
```shell
mkdir -p ~/deploy-confidence-ca
cd ~/deploy-confidence-ca
```
Generate CA key and cert
```shell
openssl genrsa -out rootCA.key 4096

openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
  -out rootCA.crt \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=Homelab/OU=Platform/CN=Homelab Root CA"
```

Files created:

- `rootCA.key`
- `rootCA.crt`

## 16. Create SAN-based origin certificate
Create SAN CSR config
```shell
cat > origin-san.cnf <<'EOF'
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
CN = deploy-confidence.lab.local

[req_ext]
subjectAltName = @alt_names
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = deploy-confidence.lab.local
EOF
```
Generate origin key and CSR
```shell
openssl genrsa -out tls.key 2048
openssl req -new -key tls.key -out tls.csr -config origin-san.cnf
```
Create cert extension file
```shell
cat > origin-ext.cnf <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=deploy-confidence.lab.local
EOF
```
Sign the origin cert with the local CA
```shell
openssl x509 -req -in tls.csr \
  -CA rootCA.crt -CAkey rootCA.key -CAcreateserial \
  -out tls.crt -days 825 -sha256 -extfile origin-ext.cnf
```

Files created:

- `tls.key`
- `tls.crt`

## 17. Verify the SAN and issuer
SAN verification
```shell
openssl x509 -in tls.crt -text -noout | grep -A3 "Subject Alternative Name"
```

Expected:

```shell
DNS:deploy-confidence.lab.local
```
Issuer verification
```shell
openssl x509 -in tls.crt -noout -issuer -subject
```

Expected:

- subject for `deploy-confidence.lab.local`
- issuer = `Homelab Root CA`

18. Replace Kubernetes TLS secret

Before replacing the secret, the old one was backed up:

```shell
kubectl -n deploy-confidence get secret deploy-confidence-lan-tls -o yaml > deploy-confidence-lan-tls.backup.yaml
```
Then replace it:

```shell
kubectl -n deploy-confidence delete secret deploy-confidence-lan-tls

kubectl -n deploy-confidence create secret tls deploy-confidence-lan-tls \
  --cert=tls.crt \
  --key=tls.key
```

Verify:

```shell
kubectl -n deploy-confidence get secret deploy-confidence-lan-tls
```
## 19. Verify the Gateway serves the new certificate
Verify issuer from the live origin
```shell
openssl s_client -connect 192.168.0.230:443 -servername deploy-confidence.lab.local </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -subject
```
Verify SAN from the live origin
```shell
openssl s_client -connect 192.168.0.230:443 -servername deploy-confidence.lab.local </dev/null 2>/dev/null \
  | openssl x509 -text -noout | grep -A3 "Subject Alternative Name"
```
Verify app still works locally
```shell
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/health
```
That continued to work.

## 20. New Cloudflare error after SAN fix

After turning No TLS Verify off, the old SAN-related error disappeared, but a new error appeared:

```shell
x509: certificate signed by unknown authority
```
Meaning

This proved that:

- SAN problem was fixed
- hostname alignment was improved
- but cloudflared still did not trust the CA that signed the origin cert

At that point, the issue was no longer certificate format — it was trust chain.

## 21. Install the CA into the jumpbox trust store

Because cloudflared runs on the jumpbox, the jumpbox OS must trust the CA.

Install CA into Debian/Ubuntu trust store
```shell
sudo cp rootCA.crt /usr/local/share/ca-certificates/homelab-root-ca.crt
sudo update-ca-certificates
```

Verify installation:

```shell
ls -l /etc/ssl/certs | grep -i homelab
```
## 22. Restart cloudflared

After updating the trust store:

```shell
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
journalctl -u cloudflared -f
```
## 23. Final Cloudflare origin settings

In the public hostname route, keep:

Public hostname
- `deploy.anselemokeke.dpdns.org`

Service
- Type: `HTTPS`
- Origin: `192.168.0.230:443`

TLS / Origin settings
- Origin Server Name: `deploy-confidence.lab.local`
- No TLS Verify: `OFF` once CA trust is working

HTTP settings
- HTTP Host Header: `deploy-confidence.lab.local`

## 24. Public validation commands
```shell
Test public health endpoint
curl -vk https://deploy.anselemokeke.dpdns.org/health
Test public details endpoint
curl -vk https://deploy.anselemokeke.dpdns.org/details
Test public score endpoint
curl -vk https://deploy.anselemokeke.dpdns.org/score
```
## 25. Important hostname note

The final public hostname used in this setup is:

```shell
deploy.anselemokeke.dpdns.org
```

Be careful to keep the spelling consistent everywhere:

- Cloudflare public hostname
- browser tests
- curl tests
- any future pipeline or integration using the public route

## 26. Final traffic flow

The final request flow is:

```shell
Browser / client
→ deploy.anselemokeke.dpdns.org
→ Cloudflare edge
→ Cloudflare Tunnel
→ cloudflared on jumpbox
→ https://192.168.0.230:443
→ Cilium Gateway
→ HTTPRoute
→ deploy-confidence-service:8000
→ FastAPI backend
```
## 27. Summary of problems encountered and fixes
### Problem 1 — wrong route type in Cloudflare

Used private hostname/private network screen instead of public hostname.

Fix

Used:

- tunnel
- published application
- public hostname
### Problem 2 — public hostname typo mismatch

The tested hostname did not match the hostname configured in Cloudflare.

Fix

Use the exact configured hostname consistently:

```shell
deploy.anselemokeke.dpdns.org
```
### Problem 3 — origin cert relied on Common Name only

Cloudflare rejected it with legacy Common Name / SAN validation error.

Fix

Create a SAN-based origin cert for:

```shell
deploy-confidence.lab.local
```
### Problem 4 — origin cert issuer not trusted

After SAN was fixed, Cloudflare still rejected the cert with unknown authority.

Fix

Create a local CA and install the CA into the jumpbox trust store.

### Problem 5 — internal routing hostname mismatch

Public hostname was different from internal Gateway hostname.

Fix

Set:

- `Origin Server Name = deploy-confidence.lab.local`
- `HTTP Host Header = deploy-confidence.lab.local`

## 28. Full command reference
### Install cloudflared
```shell
mkdir -p ~/cloudflare
cd ~/cloudflare
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
sudo apt-get update
sudo apt-get install -f -y
cloudflared --version
```
### Local CA and SAN cert creation
```shell
mkdir -p ~/deploy-confidence-ca
cd ~/deploy-confidence-ca

openssl genrsa -out rootCA.key 4096

openssl req -x509 -new -nodes -key rootCA.key -sha256 -days 3650 \
  -out rootCA.crt \
  -subj "/C=DE/ST=Berlin/L=Berlin/O=Homelab/OU=Platform/CN=Homelab Root CA"

cat > origin-san.cnf <<'EOF'
[req]
default_bits = 2048
prompt = no
default_md = sha256
req_extensions = req_ext
distinguished_name = dn

[dn]
CN = deploy-confidence.lab.local

[req_ext]
subjectAltName = @alt_names
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth

[alt_names]
DNS.1 = deploy-confidence.lab.local
EOF

openssl genrsa -out tls.key 2048
openssl req -new -key tls.key -out tls.csr -config origin-san.cnf

cat > origin-ext.cnf <<'EOF'
authorityKeyIdentifier=keyid,issuer
basicConstraints=CA:FALSE
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth
subjectAltName=@alt_names

[alt_names]
DNS.1=deploy-confidence.lab.local
EOF

openssl x509 -req -in tls.csr \
  -CA rootCA.crt -CAkey rootCA.key -CAcreateserial \
  -out tls.crt -days 825 -sha256 -extfile origin-ext.cnf
```
### Verify cert
```shell
openssl x509 -in tls.crt -text -noout | grep -A3 "Subject Alternative Name"
openssl x509 -in tls.crt -noout -issuer -subject
```
### Replace secret
```shell
kubectl -n deploy-confidence get secret deploy-confidence-lan-tls -o yaml > deploy-confidence-lan-tls.backup.yaml
kubectl -n deploy-confidence delete secret deploy-confidence-lan-tls
kubectl -n deploy-confidence create secret tls deploy-confidence-lan-tls \
  --cert=tls.crt \
  --key=tls.key
```
### Verify live origin cert
```shell
openssl s_client -connect 192.168.0.230:443 -servername deploy-confidence.lab.local </dev/null 2>/dev/null \
  | openssl x509 -noout -issuer -subject

openssl s_client -connect 192.168.0.230:443 -servername deploy-confidence.lab.local </dev/null 2>/dev/null \
  | openssl x509 -text -noout | grep -A3 "Subject Alternative Name"
```
### Trust CA on jumpbox
```shell
sudo cp rootCA.crt /usr/local/share/ca-certificates/homelab-root-ca.crt
sudo update-ca-certificates
sudo systemctl restart cloudflared
sudo systemctl status cloudflared
journalctl -u cloudflared -f
```
### Local LAN validation
```shell
curl -k --resolve deploy-confidence.lab.local:443:192.168.0.230 https://deploy-confidence.lab.local/health
```
### Public Cloudflare validation
```shell
curl -vk https://deploy.anselemokeke.dpdns.org/health
curl -vk https://deploy.anselemokeke.dpdns.org/details
curl -vk https://deploy.anselemokeke.dpdns.org/score
```
## 29. Final operational note

For CI/CD or other automation, choose the hostname based on where the caller lives:

- in-cluster: `http://deploy-confidence-service.deploy-confidence.svc.cluster.local:8000`
- inside LAN: `https://deploy-confidence.lab.local`
- external/public: `https://deploy.anselemokeke.dpdns.org`

> The public Cloudflare hostname is not the first choice for internal automation if a closer internal path exists.