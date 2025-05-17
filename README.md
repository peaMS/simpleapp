# Deployment of a simple app

This is a 3-tier app inspired in the [YADA app](https://github.com/Microsoft/YADA). 
It is thought to be deployed in AWS with the following architecture:

1. Web tier: containerized, based on PHP, to be deployed in EKS.
1. App tier: containerized, based on Python/Flask, to be deployed in EKS.
1. Database: MySQL, to be installed on EC2.


