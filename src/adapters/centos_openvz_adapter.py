""" A module for managing VMs on CentOS - OpenVZ platform. """

""" Open issues with the current version:
   1. Not designed for concurrent use e.g. find_available_ip uses vzlist for
        finding available ip, but if a vm is in the process of being created,
        vzlist will probably not list it, resulting in duplicate ip address.
        These functionalities should be moved up to VMPool for enabling
        concurrency.
    2. Very little of any kind of error handling is done.
    3. Logging has not been implemented yet.
"""

__all__ = [
    'create_vm',
    'start_vm',
    'stop_vm',
    'restart_vm',
    'start_vm_manager',
    'destroy_vm',
    'is_running_vm',
    'migrate_vm',
    'get_resource_utilization',
    'take_snapshot',
    'InvalidVMIDException',
    ]

# Standard Library imports
import re
from exceptions import Exception
# Third party imports

# VLEAD imports
from __init__ import *
import vm_utils
from dict2default import dict2default
from config.adapters import base_config
import base_adapter
from httplogging.http_logger import logger
from utils.execute_commands import execute_command
from utils.git_commands import GitCommands
from config.adapters import centos_openvz_config as config

# Globals
VZCTL = "/usr/sbin/vzctl"
VZLIST = "/usr/sbin/vzlist -a"
IP_ADDRESS_REGEX = r"[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}.[0-9]{1,3}"
# IP_ADDRESS_REGEX =
# "^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1
# [0-9]{2}|2[0-4][0-9]|25[0-5])$";


class InvalidVMIDException(Exception):
    def __init__(msg):
        Exception.__init__(msg)


class CentOSVZAdapter(object):

    time_before_next_retry = None
    git = None

    def __init__(self):
        self.git = GitCommands()
        self.time_before_next_retry = 5

    def create_vm(self, lab_spec, vm_id=""):
        logger.debug("centos_openvz_adapter: create_vm()")
        """If no vm_id is specified, it is computed using the last two
        segments"""
        """of an available IP address; vm_spec is an object """
        if vm_id == "":
            ip_address = base_adapter.find_available_ip()
            m = re.match(r'[0-9]+.[0-9]+.([0-9]+).([0-9]+)', ip_address)
            if m is not None:
                vm_id = str((int(m.group(1) + m.group(2))))
                # vm_id = m.group(1) + m.group(2)
        else:
            ip_address = None
            vm_id = self.validate_vm_id(vm_id)

        (vm_create_args, vm_set_args) = self.construct_vzctl_args(lab_spec)

        logger.debug("centos_openvz_adapter: create_vm(): ip = %s, vm_id = %s, \
                     vm_create_args = %s, vm_set_args = %s" %
                     (ip_address, vm_id, vm_create_args, vm_set_args))

        try:
            command = (r'ssh -o "%s" %s "%s create %s %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        VZCTL, vm_id, vm_create_args))
            logger.debug("centos_openvz_adapter: create_vm(): create command = %s" %
                         command)
            (ret_code, output) = execute_command(command)

            if ret_code == 0:

                command = (r'ssh -o "%s" %s "%s start %s"' %
                           (base_config.NO_STRICT_CHECKING,
                            base_config.BASE_IP_ADDRESS,
                            VZCTL, vm_id))
                logger.debug("centos_openvz_adapter: create_vm():start command = %s" %
                             command)
                (ret_code, output) = execute_command(command)

                if ret_code == 0:

                    command = (r'ssh -o "%s" %s "%s set %s %s"' %
                               (base_config.NO_STRICT_CHECKING,
                                base_config.BASE_IP_ADDRESS,
                                VZCTL, vm_id, vm_set_args))
                    logger.debug("centos_openvz_adapter:create_vm():set command=%s" %
                                 command)
                    (ret_code, output) = execute_command(command)

                    if ret_code == 0:
                        return (True, vm_id)

        except Exception, e:
            logger.error("Error creating VM: " + str(e))
            # raise e
            return (False, -1)

    def init_vm(self, vm_id, lab_repo_name):
        logger.debug("centos_openvz_adapter: init_vm(): vm_id = %s" % vm_id)
        success = True
        success = success and self.copy_public_key(vm_id)
        success = success and self.copy_ovpl_source(vm_id)
        success = success and self.copy_lab_source(vm_id,
                                                   lab_repo_name,
                                                   self.git.get_git_clone_loc())
        success = success and self.start_vm_manager(vm_id)
        response = {"vm_id": vm_id, "vm_ip": self.get_vm_ip(vm_id), "vm_port": base_config.VM_MANAGER_PORT}

        # check if the VMManager service came up and running..
        logger.debug("Ensuring VMManager service is running on VM %s" %
                     response['vm_ip'])
        vmmgr_port = int(base_config.VM_MANAGER_PORT)
        success = base_adapter.wait_for_service(response['vm_ip'],
                                                vmmgr_port,
                                                self.time_before_next_retry,
                                                config.TIMEOUT)

        if not success:
            logger.debug("Could not reach VMManager after %s secs!! Aborting." %
                         config.TIMEOUT)
            return (success, response)

        logger.debug("centos_openvz_adapter: init_vm(): success = %s, response = %s" %
                     (success, response))

        return (success, response)

    def destroy_vm(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        try:

            command = (r'ssh -o "%s" %s "%s stop %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        VZCTL, vm_id))
            logger.debug("centos_openvz_adapter: destroy_vm(): stop command = %s" %
                         command)
            (ret_code, output) = execute_command(command)

            if ret_code == 0:
                command = (r'ssh -o "%s" %s "%s destroy %s"' %
                           (base_config.NO_STRICT_CHECKING,
                            base_config.BASE_IP_ADDRESS,
                            VZCTL, vm_id))
                logger.debug("centos_openvz_adapter:destroy_vm():destroy command %s" %
                             command)
                (ret_code, output) = execute_command(command)
                if ret_code == 0:
                    return "Success"
        except Exception, e:
            logger.error("Error destroying VM: " + str(e))
            return "Failed to destroy VM: " + str(e)

    def restart_vm(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        try:
            command = (r'ssh -o "%s" %s "%s restart %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        VZCTL, vm_id))
            logger.debug("centos_openvz_adapter: restart_vm(): restart command = %s" %
                         command)
            (ret_code, output) = execute_command(command)
        except Exception, e:
            raise e
        return start_vm_manager(vm_id)

    def start_vm(self, vm_id):
        # HACK
        self.restart_vm(self, vm_id)

    def start_vm_manager(self, vm_id):
        ovpl_dir_name = base_adapter.OVPL_DIR_PATH.split("/")[-1]
        vm_ovpl_path = base_config.VM_DEST_DIR + ovpl_dir_name
        ip_address = self.get_vm_ip(vm_id)
        start_vm_manager_command = ("python %s%s %s" %
                                    (vm_ovpl_path,
                                     base_config.VM_MANAGER_SERVER_PATH,
                                     ">>/root/vm.log 2>&1 </dev/null &"))
        command = (r"ssh -o '%s' %s%s '%s'" %
                   (base_config.NO_STRICT_CHECKING,
                    "root@", ip_address,
                    start_vm_manager_command))
        logger.debug("centos_openvz_adapter: start_vm_manager(): command = %s" %
                     command)
        try:
            (ret_code, output) = execute_command(command)
            return True
        except Exception, e:
            logger.error("centos_openvz_adapter: start_vm_manager(): command = %s, \
                         ERROR = %s" %
                         (command, str(e)))
            return False

    def get_resource_utilization(self):
        pass

    def stop_vm(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        try:
            command = (r'ssh -o "%s" %s "%s stop %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        VZCTL, vm_id))
            logger.debug("centos_openvz_adapter: stop_vm(): command = %s" %
                         command)
            (ret_code, output) = execute_command(command)
            return "Success"

        except Exception, e:
            logger.error("Error stopping VM: " + str(e))
            return "Failed to stop VM: " + str(e)

    def test_logging(self):
        logger.debug("centos_openvz_adapter: test_logging()")

    def is_running_vm(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        pass

    def migrate_vm(self, vm_id, destination):
        vm_id = self.validate_vm_id(vm_id)
        pass

    def take_snapshot(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        pass

    def copy_public_key(self, vm_id):

        try:
            if base_config.ADS_ON_CONTAINER:
                public_key_file = ("%s%s%s%s" %
                                   (base_config.VM_ROOT_DIR,
                                    base_config.ADS_SERVER_VM_ID,
                                    base_config.VM_DEST_DIR, ".ssh/id_rsa.pub"))
            else:
                public_key_file = ("%s" %
                                   ("/root/.ssh/id_rsa.pub"))

            authorized_key_file = ("%s%s%s%s" %
                                   (base_config.VM_ROOT_DIR, vm_id,
                                    base_config.VM_DEST_DIR,
                                    ".ssh/authorized_keys"))

            logger.debug("public key location = %s, authorized key location = %s" %
                         (public_key_file, authorized_key_file))
            command = (r'ssh -o "%s" %s "%s %s > %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        "/bin/cat", public_key_file, authorized_key_file))
            logger.debug("command to cpy the public key = %s" % command)
            (ret_code, output) = execute_command(command)
            return True
        except Exception, e:
            logger.error("ERROR = %s" % str(e))
            return False

    def copy_files(self, src_dir, dest_dir):

        try:
            copy_command = "rsync -arz --progress " + src_dir + " " + dest_dir
            logger.debug("copy command = %s" % copy_command)
            command = (r'ssh %s "%s"' %
                       (base_config.BASE_IP_ADDRESS, copy_command))
            logger.debug("Command = %s" % command)
            (ret_code, output) = execute_command(command)
            if ret_code == 0:
                logger.debug("Copy successful")
                return True
            else:
                logger.debug("Copy Unsuccessful, return code is %s" % str(ret_code))
                return False
        except Exception, e:
            logger.error("ERROR = %s" % str(e))
            return False

    def copy_ovpl_source(self, vm_id):
        src_dir = None
        if base_config.ADS_ON_CONTAINER:
            src_dir = "%s%s%s" % (base_config.VM_ROOT_DIR,
                                  base_config.ADS_SERVER_VM_ID,
                                  base_adapter.OVPL_DIR_PATH)
        else:
            src_dir = "%s" % (base_adapter.OVPL_DIR_PATH)

        dest_dir = "%s%s%s" % (base_config.VM_ROOT_DIR, vm_id,
                               base_config.VM_DEST_DIR)

        logger.debug("vm_id = %s, src_dir=%s, dest_dir=%s" %
                     (vm_id, src_dir, dest_dir))

        try:
            return self.copy_files(str(src_dir), str(dest_dir))
        except Exception, e:
            logger.error("ERROR = %s" % str(e))
            return False

    def copy_lab_source(self, vm_id, lab_repo_name, git_clone_loc):

        directories = git_clone_loc.split("/")
        labs_dir = directories[-2]
        src_dir = None
        if base_config.ADS_ON_CONTAINER:
            src_dir = "%s%s%s%s%s%s" % (base_config.VM_ROOT_DIR,
                                        base_config.ADS_SERVER_VM_ID,
                                        base_config.VM_DEST_DIR, labs_dir,
                                        "/", lab_repo_name)
        else:
            src_dir = "%s%s%s%s" % (base_config.VM_DEST_DIR, labs_dir,
                                    "/", lab_repo_name)

        dest_dir = "%s%s%s" % (base_config.VM_ROOT_DIR, vm_id,
                               base_config.VM_DEST_DIR + "labs")

        logger.debug("vm_id = %s, src_dir=%s, dest_dir=%s" %
                     (vm_id, src_dir, dest_dir))

        try:
            return self.copy_files(src_dir, dest_dir)
        except Exception, e:
            logger.error("ERROR = %s" % str(e))
            return False

    def get_vm_ip(self, vm_id):
        vm_id = self.validate_vm_id(vm_id)
        try:
            command = (r'ssh -o "%s" %s "%s | grep %s"' %
                       (base_config.NO_STRICT_CHECKING,
                        base_config.BASE_IP_ADDRESS,
                        VZLIST, vm_id))
            (ret_code, vzlist) = execute_command(command)
            if vzlist == "":
                return                                  # raise exception?
            ip_address = re.search(IP_ADDRESS_REGEX, vzlist)
            if ip_address is not None:
                ip_address = ip_address.group(0)
            return ip_address
        except Exception, e:
            raise e

    def construct_vzctl_args(self, lab_specz={}):
        """ Returns a tuple of vzctl create arguments and set arguments """

        def get_vm_spec():
            lab_spec = dict2default(lab_specz)
            vm_spec = {
                "lab_ID": lab_spec['lab']['description']['id'],
                "os": lab_spec['lab']['runtime_requirements']['platform']['os'],
                "os_version": lab_spec['lab']['runtime_requirements']
                ['platform']['osVersion'],
                "ram": lab_spec['lab']['runtime_requirements']['platform']
                ['memory']['min_required'],
                "diskspace": lab_spec['lab']['runtime_requirements']
                ['platform']['storage']['min_required'],
                "swap": lab_spec['lab']['runtime_requirements']['platform']
                ['memory']['swap']
            }
            return vm_spec

        vm_spec = get_vm_spec()
        lab_ID = None
        if vm_spec["lab_ID"] == "":
            lab_ID = base_adapter.get_test_lab_id()
        else:
            lab_ID = vm_spec["lab_ID"]
        host_name = lab_ID + "." + base_adapter.get_adapter_hostname()
        ip_address = base_adapter.find_available_ip()
        os_template = base_adapter.find_os_template(vm_spec["os"],
                                                    vm_spec["os_version"],
                                                    config.supported_template)
        (ram, swap) = vm_utils.get_ram_swap(vm_spec["ram"], vm_spec["swap"])
        (disk_soft, disk_hard) = vm_utils.get_disk_space(vm_spec["diskspace"])
        vm_create_args = " --ostemplate " + os_template + \
                         " --ipadd " + ip_address + \
                         " --diskspace " + disk_soft + ":" + disk_hard + \
                         " --hostname " + host_name
        # Note to self: check ram format "0:256M" vs "256M"
        vm_set_args = " --nameserver " + base_config.ADAPTER_NAME_SERVER + \
                      " --ram " + ram + \
                      " --swap " + swap + \
                      " --onboot yes" + \
                      " --save"
        return (vm_create_args, vm_set_args)

    def validate_vm_id(self, vm_id):
        vm_id = str(vm_id).strip()
        m = re.match(r'^([0-9]+)$', vm_id)
        if m is None:
            raise InvalidVMIDException("Invalid VM ID.  VM ID must be numeric.")
        vm_id = int(m.group(0))
        if vm_id <= 0:
            raise InvalidVMIDException("Invalid VM ID.VM ID must be greater \
            than 0.")
        if vm_id > base_config.MAX_VM_ID:
            raise InvalidVMIDException("Invalid VM ID.  Specify a smaller VM ID.")
        return str(vm_id)


def test():
    # vm_spec = VMSpec.VMSpec({'lab_ID': 'test99'})
    import json
    lab_spec = json.loads(open("sample_lab_spec.json").read())
    create_vm(lab_spec)
    create_vm(lab_spec, "99100")
    # create_vm(vm_spec, "99101")
    # create_vm("99102", vm_spec)
    # create_vm("99103", vm_spec)
    destroy_vm("99100")
    # destroy_vm("99101")
    # destroy_vm("99102")
    # destroy_vm("99103")


if __name__ == "__main__":

    # Start an HTTP server and wait for invocation
    # Parse the invocation command and route to
    # appropriate methods.
    # test()
    # if copy_ovpl_source(584):
    #    logger.debug("test Successful")
    # else:
    #    logger.debug("test UNSuccessful")

    def test_find_os_template():
        os = "ubuntu"
        os_version = "12"
        try:
            template = find_os_template(os, os_version)
            logger.debug("Returned template = %s" % template)
        except Exception, e:
            logger.debug("Exception = %s" % str(e))

    test_find_os_template()
