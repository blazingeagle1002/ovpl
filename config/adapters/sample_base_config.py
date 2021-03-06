# This can be either 'TRUE' or 'FALSE' based from where the ADS services are
# running.
ADS_ON_CONTAINER = False
# BASE_IP_ADDRESS will hold the IP of the base machine on which containers
# will be created"
SUBNET = ["X.X.X.X/X"]
BASE_IP_ADDRESS = "root@<base-ip>"
NO_STRICT_CHECKING = "StrictHostKeyChecking no"
# ADS_SERVER_ID will be CTID of the container running ADS services
ADS_SERVER_VM_ID = "<CTID>"
VM_ROOT_DIR = "/vz/root/"
VM_DEST_DIR = "/root/"
VM_MANAGER_PORT = "9089"
LAB_ID = "engg01"
OS = "Ubuntu"
OS_VERSION = "12.04"
HOST_NAME = "base4.vlabs.ac.in"
ADAPTER_NAME_SERVER = "inherit"
# run VMManagerServer with the default VMManager
VM_MANAGER_SERVER_PATH = "/src/vmmanager/vm_manager_server.py"
MAX_VM_ID = 2147483644  # 32-bit; exact value based on trial-and-error

#Hooks configuration
#ADS_USING_HOOKS = True will invoke hooks service and return the domain name (FQDN)
#False will return the ip address of the deployed lab.
ADS_USING_HOOKS = True
SERVICE_HOST = "root@ansible.base4.vlabs.ac.in"

#SECREATE KEY

SECRET_KEY = "placethekeyhere"
