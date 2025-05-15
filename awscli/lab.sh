##################################################################################################
# This script creates an EKS cluster and deploys a sample application on it.
# The backend is a MySQL database running on an EC2 instance.
# The VPC is spread over two availability zones.
#
# May 2025
##################################################################################################

# Variables
sg1_name=db-sg
sg2_name=app-sg
kp_name=joseaws2025
# instance_size='t2.nano'
instance_size='t2.micro'
instance_image=ami-0f9a76ac74287e07e
# instance_image=ami-'059cd2be9c27a0e81'
# instance_image=ami-a4827dc9
vpc_prefix='172.16.0.0/16'
subnet1_prefix='172.16.1.0/24'
subnet2_prefix='172.16.2.0/24'
subnet3_prefix='172.16.3.0/24'

######################
#   Infrastructure   #
######################

# How to get image names/IDs
# aws ec2 describe-images --filters "Name=name,Values=ubuntu-2204-standard*" "Name=architecture,Values=x86_64" --query 'Images[*].[Name, ImageId, CreationDate]' --output table

# Create Key Pair if not there
kp_id=$(aws ec2 describe-key-pairs --key-name "$kp_name" --query 'KeyPairs[0].KeyPairId' --output text)
if [[ -z "$kp_id" ]]; then
    echo "Key pair $kp_name does not exist, creating new..."
    pemfile="$HOME/.ssh/${kp_name}.pem"
    touch "$pemfile"
    aws ec2 create-key-pair --key-name $kp_name --key-type rsa --query 'KeyMaterial' --output text > "$pemfile"
    chmod 400 "$pemfile"
else
    echo "Key pair $kp_name already exists with ID $kp_id"
fi

# VPC and subnet
# https://docs.aws.amazon.com/vpc/latest/userguide/vpc-subnets-commands-example.html
vpc_id=$(aws ec2 create-vpc --cidr-block "$vpc_prefix" --query Vpc.VpcId --output text)
zone1_id=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].ZoneId' --output text)
zone2_id=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[1].ZoneId' --output text)
zone3_id=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[2].ZoneId' --output text)
subnet1_id=$(aws ec2 create-subnet --vpc-id "$vpc_id" --cidr-block "$subnet1_prefix" --availability-zone-id "$zone1_id" --query Subnet.SubnetId --output text)
subnet2_id=$(aws ec2 create-subnet --vpc-id "$vpc_id" --cidr-block "$subnet2_prefix" --availability-zone-id "$zone2_id" --query Subnet.SubnetId --output text)
subnet3_id=$(aws ec2 create-subnet --vpc-id "$vpc_id" --cidr-block "$subnet3_prefix" --availability-zone-id "$zone3_id" --query Subnet.SubnetId --output text)
igw_id=$(aws ec2 create-internet-gateway --query InternetGateway.InternetGatewayId --output text)
if [[ -n "$igw_id" ]]; then
    aws ec2 attach-internet-gateway --vpc-id "$vpc_id" --internet-gateway-id "$igw_id"
fi
aws ec2 modify-subnet-attribute --subnet-id "$subnet1_id" --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id "$subnet2_id" --map-public-ip-on-launch
aws ec2 modify-subnet-attribute --subnet-id "$subnet3_id" --map-public-ip-on-launch

# If subnet and VPC already existed
vpc_id=$(aws ec2 describe-vpcs --filters "Name=cidr-block,Values=$vpc_prefix" --query 'Vpcs[0].VpcId' --output text)
subnet1_id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=cidr-block,Values=$subnet1_prefix" --query 'Subnets[0].SubnetId' --output text)
subnet2_id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=cidr-block,Values=$subnet2_prefix" --query 'Subnets[0].SubnetId' --output text)
subnet3_id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" "Name=cidr-block,Values=$subnet3_prefix" --query 'Subnets[0].SubnetId' --output text)

# Route table
rt_id=$(aws ec2 create-route-table --vpc-id "$vpc_id" --query RouteTable.RouteTableId --output text)
aws ec2 create-route --route-table-id "$rt_id" --destination-cidr-block 0.0.0.0/0 --gateway-id "$igw_id"
aws ec2 associate-route-table --subnet-id "$subnet1_id" --route-table-id "$rt_id"
aws ec2 associate-route-table --subnet-id "$subnet2_id" --route-table-id "$rt_id"
aws ec2 associate-route-table --subnet-id "$subnet3_id" --route-table-id "$rt_id"

# Create SG
aws ec2 create-security-group --group-name $sg1_name --description "Database SG" --vpc-id "$vpc_id"
sg1_id=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$sg1_name" --query 'SecurityGroups[0].GroupId' --output text)
aws ec2 authorize-security-group-ingress --group-id "$sg1_id" --protocol tcp --port 22 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id "$sg1_id" --protocol tcp --port 3306 --cidr 0.0.0.0/0

######################
#    EC2 instance    #
######################

# Create EC2 instance for MySQL in subnet 1
aws ec2 run-instances --image-id "$instance_image" --key-name "$kp_name" --security-group-ids "$sg1_id" --instance-type "$instance_size" --subnet-id "$subnet1_id"
# aws ec2 run-instances  --image-id ami-5ec1673e --key-name MyKey --security-groups EC2SecurityGroup --instance-type t2.micro --placement AvailabilityZone=us-west-2b --block-device-mappings DeviceName=/dev/sdh,Ebs={VolumeSize=100} --count 2
instance1_id=$(aws ec2 describe-instances --filters "Name=subnet-id,Values=$subnet1_id" --query 'Reservations[0].Instances[0].InstanceId' --output text)

# Check SSH access
instance1_pip=$(aws ec2 describe-instances --instance-id "$instance1_id" --query 'Reservations[*].Instances[*].PublicIpAddress' --output text) && echo "$instance1_pip"
pemfile="$HOME/.ssh/${kp_name}.pem"
# user=ec2-user # (for Amazon Linux)
user=ubuntu # (for Ubuntu)
sleep 30       # 30 secs to wait for the instance to be up
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -i "$pemfile" "${user}@${instance1_pip}" "ip a"

# Install MySQL
ssh -n -o BatchMode=yes -o StrictHostKeyChecking=no -i "$pemfile" "${user}@${instance1_pip}" "sudo apt update && sudo apt install mysql-server -y"

# Add an additional user that can connect from anywhere. These commands should be run in the MySQL shell (sudo mysql)
# CREATE USER 'mysqluser'@'localhost' IDENTIFIED BY 'Microsoft123!';
# GRANT ALL PRIVILEGES ON *.* TO 'mysqluser'@'localhost' WITH GRANT OPTION;
# CREATE USER 'mysqluser'@'%' IDENTIFIED BY 'Microsoft123!';
# GRANT ALL PRIVILEGES ON *.* TO 'mysqluser'@'%' WITH GRANT OPTION;

# Create a new DB in the mysql shell (we will need it to connect from the EKS cluster)
# CREATE DATABASE test;

# Modify mysql config in /etc/mysql/mysql.conf.d/mysqld.cnf
# bind-address = 0.0.0.0
# mysqlx-bind-address = 0.0.0.0

# Restart mysql
# sudo systemctl restart mysql

# Get private IP of the instance (we will need it to connect from the EKS cluster)
instance1_private_ip=$(aws ec2 describe-instances --instance-id "$instance1_id" --query 'Reservations[*].Instances[*].PrivateIpAddress' --output text) && echo "$instance1_private_ip"

######################
# Deploy EKS cluster #
######################

# https://computingforgeeks.com/easily-setup-kubernetes-cluster-on-aws-with-eks/
# https://docs.aws.amazon.com/eks/latest/userguide/create-cluster.html

# Install eksctl
# https://docs.aws.amazon.com/eks/latest/userguide/eksctl.html
ARCH=amd64
PLATFORM=$(uname -s)_$ARCH
curl -sLO "https://github.com/eksctl-io/eksctl/releases/latest/download/eksctl_$PLATFORM.tar.gz"
tar -xzf eksctl_$PLATFORM.tar.gz -C /tmp && rm eksctl_$PLATFORM.tar.gz
sudo mv /tmp/eksctl /usr/local/bin
eksctl version

# Set some values
region=$(aws configure get region)
eks_name=prod-eks-cluster
eks_node_size=t3.micro
zone1_name=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[0].ZoneName' --output text)
zone2_name=$(aws ec2 describe-availability-zones --query 'AvailabilityZones[1].ZoneName' --output text)

# Create EKS cluster (can take 15 minutes)
eksctl create cluster -f - <<EOF
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig
metadata:
  name: $eks_name
  region: $region
  version: "1.32"
# cloudWatch:
#   clusterLogging:
#     enableTypes: ["*"]
vpc:
  clusterEndpoints:
    publicAccess: true
    privateAccess: true
  subnets:
    public:
      $zone1_name: { id: $subnet1_id }
      $zone2_name: { id: $subnet2_id }
managedNodeGroups:
  - name: node-group-01
    labels: { role: workers }
    instanceType: $eks_node_size
    privateNetworking: false
    desiredCapacity: 2
    minSize: 1
    maxSize: 2
    volumeSize: 80
    ssh:
      allow: true # will use ~/.ssh/id_rsa.pub as the default ssh key
EOF

# Permissions]
# https://computingforgeeks.com/grant-developers-access-to-eks-kubernetes-cluster/


# Verify EKS cluster
eksctl get cluster
aws eks --region $region update-kubeconfig --name $eks_name

######################
#       K8s app      #
######################

api_image=erjosito/mysqlapi:1.0
web_image=erjosito/mysqlweb:1.0
sql_username='mysqluser'
sql_password='Microsoft123!'
db_name='test'

# API component
kubectl apply -f - <<EOF
apiVersion: v1
kind: Secret
metadata:
  name: sqlpassword
type: Opaque
stringData:
  password: $sql_password
---
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    run: api
  name: api
spec:
  replicas: 1
  selector:
    matchLabels:
      run: api
  template:
    metadata:
      labels:
        run: api
    spec:
      containers:
      - image: $api_image
        name: api
        ports:
        - containerPort: 8080
          protocol: TCP
        env:
        - name: SQL_SERVER_FQDN
          value: "$instance1_private_ip"
        - name: SQL_SERVER_DB
          value: "$db_name"
        - name: SQL_SERVER_USERNAME
          value: "$sql_username"
        - name: SQL_SERVER_PASSWORD
          valueFrom:
            secretKeyRef:
              name: sqlpassword
              key: password
      restartPolicy: Always
---
apiVersion: v1
kind: Service
metadata:
  name: api
spec:
  type: LoadBalancer
  ports:
  - port: 8080
    targetPort: 8080
  selector:
    run: api
EOF

# Web component
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  labels:
    run: web
  name: web
spec:
  replicas: 1
  selector:
    matchLabels:
      run: web
  template:
    metadata:
      labels:
        run: web
    spec:
      containers:
      - image: $web_image
        name: web
        ports:
        - containerPort: 80
          protocol: TCP
        env:
        - name: API_URL
          value: "http://api:8080"
      restartPolicy: Always
---
apiVersion: v1
kind: Service
metadata:
  name: web
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
spec:
  type: LoadBalancer
  ports:
  - port: 80
    targetPort: 80
  selector:
    run: web
EOF

###############
#   Cleanup   #
###############

function delete_vpc() {
    vpc_id=$1
    # Look for IGW attachments
    igw_id=$(aws ec2 describe-internet-gateways --query 'InternetGateways[].{VpcId: Attachments[*].VpcId|[0], IgwId: InternetGatewayId}|[?VpcId==`'$vpc_id'`].IgwId|[0]' --output text)
    while [[ -n "$igw_id" ]] && [[ "$igw_id" != "None" ]]; do
        echo "Found attachment between IGW $igw_id and VPC $vpc_id. Detaching IGW..."
        aws ec2 detach-internet-gateway --vpc-id "$vpc_id" --internet-gateway-id "$igw_id"
        echo "Trying to delete IGW $igw_id..."
        aws ec2 delete-internet-gateway --internet-gateway-id "$igw_id"
        igw_id=$(aws ec2 describe-internet-gateways --query 'InternetGateways[].{VpcId: Attachments[*].VpcId|[0], IgwId: InternetGatewayId}|[?VpcId==`'$vpc_id'`].IgwId|[0]' --output text)
    done
    # Look for subnets
    subnet_id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" --query 'Subnets[0].SubnetId' --output text)
    while [[ -n "$subnet_id" ]] && [[ "$subnet_id" != "None" ]]; do
        echo "Found subnet $subnet_id in VPC $vpc_id. Trying to delete subnet now..."
        aws ec2 delete-subnet --subnet-id "$subnet_id"
        subnet_id=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$vpc_id" --query 'Subnets[0].SubnetId' --output text)
    done
    # Look for a RT associated to this VPC
    rt_id=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" --query 'RouteTables[0].RouteTableId' --output text)
    previous_rt_id=""       # We keep track of the last route table ID
    while [[ -n "$rt_id" ]] && [[ "$rt_id" != "None" ]] && [[ "$rt_id" != "$previous_rt_id" ]]; do
        echo "Found Route Table $rt_id in VPC $vpc_id. Looking for associations..."
        # Disassociating RT first...
        ass_id_list=$(aws ec2 describe-route-tables --route-table-id $rt_id --query 'RouteTables[0].Associations[].RouteTableAssociationId' --output text)
        i=1
        ass_id=$(echo "$ass_id_list" | cut -f $i)
        previous_ass_id=""      # We keep count of the previous association ID, because single count results doesnt seem to work fine with cut, and `echo $ass_id_list | cut -f x` will always return the same, regardless x
        while [[ -n $ass_id ]] && [[ "$ass_id" != "$previous_ass_id" ]]; do
            echo "Deleting route table association ID $i: $ass_id..."
            aws ec2 disassociate-route-table --association-id "$ass_id"
            i=$(( i + 1 ))
            previous_ass_id=$ass_id
            ass_id=$(echo "$ass_id_list" | cut -f $i)
        done
        # Delete routes
        # Delete RT
        echo "Deleting route table $rt_id now..."
        aws ec2 delete-route-table --route-table-id "$rt_id"
        previous_rt_id="$rt_id"
        rt_id=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$vpc_id" --query 'RouteTables[0].RouteTableId' --output text)
    done
    # Delete VPC
    echo "Trying to delete VPC $vpc_id..."
    aws ec2 delete-vpc --vpc-id "$vpc_id"
}

function delete_all_sgs() {
    sg_list=$(aws ec2 describe-security-groups --query 'SecurityGroups[*].[GroupId]' --output text)
    while read -r sg_id
    do
        echo "Deleting SG ${sg_id}..."
        aws ec2 delete-security-group --group-id "$sg_id"
    done < <(echo "$sg_list")
}

function delete_all_instances() {
    instance_list=$(aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId]' --output text)
    while read -r instance_id
    do
        echo "Terminating instance ${instance_id}..."
        aws ec2 terminate-instances --instance-ids "${instance_id}"
    done < <(echo "$instance_list")
}

# eksctl delete cluster "$eks_name"
# delete_all_instances
# delete_all_sgs
# delete_vpc "$vpc_id"