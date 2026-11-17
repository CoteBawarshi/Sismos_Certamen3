#!/usr/bin/env bash
# Crea la infraestructura en AWS con la CLI (se ejecuta desde la terminal del AWS Academy Learner Lab):
#   curl -sL https://raw.githubusercontent.com/CoteBawarshi/Sismos_Certamen3/main/deploy/crear_ec2.sh | bash
# Crea: security group (puertos 22 y 80), IP elástica fija e instancia EC2 Ubuntu 24.04 que, al encender,
# descarga el repositorio y ejecuta deploy/setup_ec2.sh automáticamente.
set -e
REPO=https://github.com/CoteBawarshi/Sismos_Certamen3.git
NOMBRE=sismos-django

echo "==> Región: $(aws configure get region)"

echo "==> 1. Security group"
SG=$(aws ec2 describe-security-groups --filters Name=group-name,Values=sismos-web --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null || true)
if [ -z "$SG" ] || [ "$SG" = "None" ]; then
  SG=$(aws ec2 create-security-group --group-name sismos-web --description "Sismos Django web" --query GroupId --output text)
  aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 80 --cidr 0.0.0.0/0 > /dev/null
  aws ec2 authorize-security-group-ingress --group-id "$SG" --protocol tcp --port 22 --cidr 0.0.0.0/0 > /dev/null
fi
echo "    $SG"

echo "==> 2. IP elástica (fija)"
ALLOC=$(aws ec2 allocate-address --domain vpc --tag-specifications "ResourceType=elastic-ip,Tags=[{Key=Name,Value=$NOMBRE}]" --query AllocationId --output text)
IP=$(aws ec2 describe-addresses --allocation-ids "$ALLOC" --query 'Addresses[0].PublicIp' --output text)
echo "    $IP"

echo "==> 3. Imagen Ubuntu 24.04"
AMI=$(aws ssm get-parameter --name /aws/service/canonical/ubuntu/server/24.04/stable/current/amd64/hvm/ebs-gp3/ami-id --query Parameter.Value --output text)
echo "    $AMI"

KEY=$(aws ec2 describe-key-pairs --query 'KeyPairs[0].KeyName' --output text 2>/dev/null || echo None)
KEYARG=""
[ "$KEY" != "None" ] && KEYARG="--key-name $KEY"

cat > /tmp/userdata.sh <<EOF
#!/bin/bash
apt-get update -y && apt-get install -y git
sudo -u ubuntu -i bash -c "export PUBLIC_IP=$IP; git clone $REPO Sismos_Certamen3 && cd Sismos_Certamen3 && bash deploy/setup_ec2.sh" > /var/log/sismos-setup.log 2>&1
echo FIN >> /var/log/sismos-setup.log
EOF

echo "==> 4. Instancia EC2 (t3.small)"
ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type t3.small --security-group-ids "$SG" $KEYARG \
  --user-data file:///tmp/userdata.sh \
  --block-device-mappings 'DeviceName=/dev/sda1,Ebs={VolumeSize=12,VolumeType=gp3}' \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=$NOMBRE}]" \
  --query 'Instances[0].InstanceId' --output text)
echo "    $ID (esperando que encienda...)"
aws ec2 wait instance-running --instance-ids "$ID"
aws ec2 associate-address --instance-id "$ID" --allocation-id "$ALLOC" > /dev/null

echo ""
echo "=============================================================="
echo " Instancia $ID lista con IP fija $IP"
echo " La instalación demora ~5-8 minutos. Luego abrir:"
echo "     http://$IP/"
echo "=============================================================="
