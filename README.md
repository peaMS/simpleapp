# Security analysis of a simple app

This is a 3-tier app inspired in the [YADA app](https://github.com/Microsoft/YADA). It is thought to be deployed in AWS with the following architecture:

1. Web tier: containerized, based on PHP, to be deployed in EKS.
1. App tier: containerized, based on Python/Flask, to be deployed in EKS.
1. Database: MySQL, to be installed on EC2.

There are many security problems with this architecture. Here a few, please feel free to create issues if you would like to add to the list:

- IMDS v1 doesnt require any auth (tokens), so every pod running in the cluster has access to confidential information.
- No HTTTPS: dance like nobody is watching, encrypt like everybody is.
- No IaC: not using IaC prevents you from using tools such as [Checkov](https://checkov.io) to detect security issues before deploying.
- No Web Application Firewall (WAF): poor application coding makes the app susceptible to web-based attacks such as Cross-Site Scripting (XSS) or SQL Code Injection. There are different ways to add a Web Application Firewall to this design:
  - As part of an ingress controller or reverse proxy running in the cluster.
  - Externally to the cluster running on an EC2 instance.
  - Externally to the customer using AWS CloudFront.
  - Using an external provider such as CloudFlare.
  - WAF functionality in agents installed in the servers.
- No egress firewall: having no egress firewall means that a compromised workload would be able to exfiltrate data. An egress firewall makes sure that only valid endpoints are reached from the workloads deployed in the VPC.
- Using container images based on broad OS (Ubuntu and Centos/RockyLinux), which include many unnecessary features that expand the attack surface of the application.
- Using container images from an external repository: the container images for the application are downloaded from a public repository (Docker Hub), which doesn't offer enterprise-grade security. Gaining access to the repository would mean gaining access to the application and the data.
- No network security inside of the cluster: no network policies or service mesh in the cluster means that every pod can communicate with every other pod, making lateral moves to attackers extremely easy.
- The database's security group allows access from the whole VPC. Even if this could be restricted by using the EKS cluster's security group, that would still allow all pods to access the database, even if they actually don't need to (for example, the web pods only need to access the app tier, not the database).
- The database password is stored in a Kubernetes secret. Kubernetes secrets are not encrypted (only MD5-encoded), so every EKS cluster administrator with enough privilege would be able to access the password. Instead, secrets should be stored in external stores such as [HashiCorp Vault](https://www.hashicorp.com/en/products/vault).
- No autoscaling: a very basic DDoS attack would be enough to bring down the application to its needs, since no autoscaling has been deployed (HPA or VPA).

What have I forgotten? Please send me a PR or an issue!
