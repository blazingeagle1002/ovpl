import netaddr
import sh
import re
from time import sleep
import socket
from __init__ import *
from utils.envsetup import EnvSetUp
from utils.execute_commands import execute_command
from httplogging.http_logger import logger
from config.adapters import base_config

VZCTL = "/usr/sbin/vzctl"
VZLIST = "/usr/sbin/vzlist -a"
OVPL_DIR_PATH = EnvSetUp.Instance().get_ovpl_directory_path()


class BaseAdapter:
    def create_vm(lab_spec):
        raise Exception("BaseAdapter: unimplemented create_vm()")

    def init_vm(vm_id, lab_repo_name):
        raise Exception("BaseAdapter: unimplemented init_()")
        # success status, response string
        return (False, "unimplemented")


class AdapterDetails:
    pass


class OSNotFound(Exception):
    """
    use this exception class to raise an exception when a suitable OS is not
    found
    """
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return repr(self.msg)

 # wait for a particular service to come up..
 # sleeps for the given amount of time between each rety
 # timesout and returns False after given timeout
   
def is_service_up(vm_ip, port):
        logger.debug("base_adapter: is_service_up(): VM IP: %s" % vm_ip)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            logger.debug("base_adapter: trying to connect to port: %s of: %s" %
                         (port, vm_ip))
            s.connect((vm_ip, port))
            logger.debug("base_adapter: VM %s: port: %s is up.." % (vm_ip, port))
            return True
        except socket.error as e:
            logger.debug("base_adapter: VM %s: Error connecting to port: %s: %s" %
                         (vm_ip, port, e))
            logger.debug("base_adapter: retrying to reach port %s.." % port)
            s.close()
            return False

def wait_for_service(vm_ip, port, sleep_time, timeout):
    logger.debug("base_adapter: wait_for_service(): VM IP: %s" % vm_ip)
    logger.debug("base_adapter: port: %s; sleep: %s; timeout: %s" %
                 (port, sleep_time, timeout))
    
    total_slept = 0
    
    # check if the VM is up and the given TCP port is reachable
    # assumption - the port is running a TCP service
    
    while not is_service_up(vm_ip, port):
        total_slept += sleep_time
        logger.debug("total slept: %s" % total_slept)
        # we have tried for the `timeout` time. Abort checking and return
        # False(failure)
        if total_slept >= timeout:
            return False
            
        logger.debug("VM %s: waiting for service at port: %s to be up.." %
                     (vm_ip, port))
        sleep(sleep_time)

    return True
    

def find_os_template(os, os_version, supported_images):
    """
    Find a suitable os image from the list of supported images from
    the given OS and OS version. If a suitable OS is not found, raise
    appropriate Exception
    """
    logger.debug("OS = %s and OS_VERSION = %s" % (os, os_version))
    logger.debug("Supported images = %s" % supported_images)

    if os == "" or os_version == "":
        msg = "No OS or Version specified"
        logger.error(msg)
        raise OSNotFound(msg)

    # sanitize input
    os = os.strip().upper()
    os_version = os_version.strip()

    if os == 'UBUNTU' and os_version == '12':
        os_version = '12.04'

    if os == 'UBUNTU' and os_version == '13':
        os_version = '13.04'

    if os == 'UBUNTU' and os_version == '14':
        os_version = '14.04'
    
    if os == 'CENTOS' and os_version == '6':
        os_version = '6.9'

    # filter the supported image list by the os and the by the version
    all_versions_of_os = filter(lambda x: x['os'] == os, supported_images)
    logger.debug("List of all the supported versions of OS = %s is %s" %
                 (os, all_versions_of_os))
    if all_versions_of_os:
        chosen_template = filter(lambda x: x['version'] ==
                                 os_version, all_versions_of_os)
        logger.debug("The image supported for OS = %s, Version = %s is %s" %
                     (os, os_version, chosen_template))
    else:
        msg = "OS = %s is not supported" % os
        logger.error(msg)
        raise OSNotFound(msg)

    if not chosen_template or not len(chosen_template):
        msg = "Version = %s is not supported" % os_version
        logger.error(msg)
        raise OSNotFound(msg)

    # chose the item; there should be only one.
    chosen_template = chosen_template[0]

    logger.debug("Choosen image: %s; based on input OS: %s, version: %s" %
                 (chosen_template, os, os_version))
    return chosen_template['id']


def get_test_lab_id():
    # can be used to create a test lab ID if lab id is empty
    LAB_ID = base_config.LAB_ID
    assert isinstance(LAB_ID, str)
    assert LAB_ID != ""
    return LAB_ID


def get_test_os():
    # can be used to set a default OS if OS is not specified in lab spec
    OS = base_config.OS
    assert isinstance(OS, str)
    assert OS != ""
    return OS


def get_test_os_version():
    # can be used to set a default OS version
    # if OS is not specified in lab spec
    OS_VERSION = base_config.OS_VERSION
    assert isinstance(OS_VERSION, str)
    assert OS_VERSION != ""
    return OS_VERSION


def get_adapter_hostname():
    HOST_NAME = base_config.HOST_NAME
    return HOST_NAME


def find_available_ip():
    # try and ping. if the IP does not respond, (gives wrong return code)
    # return the IP as free
    def is_ip_free(ip):
        try:
            sh.ping(str(ip), c=1)
        except sh.ErrorReturnCode:
            if is_ctid_free(str(ip)):
                return True
            else:
                return False

    def is_ctid_free(ip):
        # to check vm_id is already exist or not
        m = re.match(r'[0-9]+.[0-9]+.([0-9]+).([0-9]+)', ip)
        vm_id = str(int(m.group(1) + m.group(2)))
        command = (r'ssh -o "%s" %s "%s %s| grep %s"' %
                   (base_config.NO_STRICT_CHECKING,
                    base_config.BASE_IP_ADDRESS,
                    VZLIST, vm_id, vm_id))
        logger.debug("CentOSVZAdapter: vzlist command = %s" %
                     command)
        try:
            (ret_code, vzlist) = execute_command(command)
            if ret_code == 0:
                return False
            else:
                return True
        except Exception:
            logger.debug("No container found with vm id = %s" % vm_id)
            return True

    def is_ip_usable(ip):
        #  reject IP's like  192.0.2.0 or 192.0.2.255 for subnet 192.0.2.0/24
        return not (ip == ip_network.network or ip == ip_network.broadcast)

    for subnet in base_config.SUBNET:
        ip_network = netaddr.IPNetwork(subnet)
        ip_addrs = list(ip_network)
        # logger.debug("ip addresses: %s" % str(ip_addrs))
        for ip in ip_addrs:
            if is_ip_usable(ip) and is_ip_free(ip):
                return str(ip)

    raise Exception("unable to find free ip in subnet ", base_config.SUBNET)
    return None


def get_adapter_details():
    adapter_details = AdapterDetails()
    env = EnvSetUp.Instance()
    config_spec = env.get_config_spec()
    adapter_details.create_uri = \
        config_spec["VMPOOL_CONFIGURATION"]["ADAPTER_ENDPOINTS"]["CREATE_URI"]
    adapter_details.destroy_uri = \
        config_spec["VMPOOL_CONFIGURATION"]["ADAPTER_ENDPOINTS"]["DESTROY_URI"]
    adapter_details.restart_uri = \
        config_spec["VMPOOL_CONFIGURATION"]["ADAPTER_ENDPOINTS"]["RESTART_URI"]
    pool_id = config_spec["ADAPTER_TO_USE"]["POOLID"] - 1
    adapter_id = config_spec["ADAPTER_TO_USE"]["ADAPTERID"] - 1
    adapter_details.port = \
        config_spec["VMPOOL_CONFIGURATION"]["VMPOOLS"][pool_id]["PORT"]
    adapter_details.module_name = \
        config_spec["VMPOOL_CONFIGURATION"]["VMPOOLS"][pool_id]["ADAPTERS"] \
        [adapter_id]["MODULE"]
    adapter_details.adapter_name = \
        config_spec["VMPOOL_CONFIGURATION"]["VMPOOLS"][pool_id]["ADAPTERS"] \
        [adapter_id]["ADAPTER"]

    return adapter_details

if __name__ == '__main__':
    def test_find_available_ip():
        ip = find_available_ip()
        logger.debug("IP = %s" % ip)

    test_find_available_ip()
