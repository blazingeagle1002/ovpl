""" An interface for managing VMs for a selected platform. """

# Run this command for me, please.
# how long has your VM been running?
# what is your memory footprint?
# what is your diskspace footprint?
# what processes are currently running?
# what is your CPU load?

# to do : handle exceptions

import os
from __init__ import *
from httplogging.http_logger import logger
from lab_action_runner import LabActionRunner
from utils.git_commands import GitCommands
from utils.execute_commands import execute_command
from utils.envsetup import EnvSetUp


def execute(command):
    # do some validation
    try:
        logger.info("Command executed: " + command)
        (ret_code, output) = execute_command(command)
        return output
    except Exception, e:
        logger.error("Execution failed: " + str(e))
        return "Error executing the command: " + str(e)


def running_time():
    logger.info("Command executed: uptime")
    return execute("uptime")


def mem_usage():
    logger.info("Command executed: free -mg")
    return execute("free -mg")


def disk_usage():
    logger.info("Command executed: df -h")
    return execute("df -h")


def running_processes():
    logger.info("Command executed: ps -e -o command")
    return execute("ps -e -o command")


def cpu_load():
    logger.info("Command executed: ps -e -o pcpu")
    return execute("ps -e -o pcpu | awk '{s+=$1} END {print s\"%\"}'")


def test_lab(lab_src_url, version=None):
    # check out the source with version provided
        # is repo already exists? if yes, then do a git pull
        # else clone the repo
    # get the labspec from /scripts/lab_spec.json
    # get the appropriate the actions from lab_spec.json
    # run LabAction Runner
        # instantiate the object
    e = EnvSetUp.Instance()
    git = GitCommands()
    logger.info("Environment http_proxy = %s" % os.environ["http_proxy"])
    logger.info("Environment https_proxy = %s" % os.environ["https_proxy"])

    def fill_aptconf(lab_spec):
        OS = str(lab_spec['lab']['runtime_requirements']['platform']['os'])
        http_proxy = os.environ["http_proxy"]
        https_proxy = os.environ["https_proxy"]
        if OS == "ubuntu":
            try:                
                http_cmd = r'echo "Acquire::http::Proxy \"%s\";"%s' % (http_proxy, '>>/etc/apt/apt.conf')
                https_cmd = r'echo "Acquire::https::Proxy \"%s\";"%s' % (https_proxy, '>>/etc/apt/apt.conf')
                (ret_code, output) = execute_command(http_cmd)
                (ret_code, output) = execute_command(https_cmd)
            except Exception, e:
                logger.error("Writing to /etc/apt/apt.conf failed with error: %s"
                             % (str(e)))
                raise e
        else:
            pass

    def get_build_steps_spec(lab_spec):
        return {"build_steps": lab_spec['lab']['build_requirements']['platform']['build_steps']}

    def get_build_installer_steps_spec(lab_spec):
        return {"installer": lab_spec['lab']['build_requirements']['platform']['installer']}

    def get_runtime_installer_steps(lab_spec):
        return {"installer": lab_spec['lab']['runtime_requirements']['platform']['installer']}

    def get_runtime_actions_steps(lab_spec):
        return lab_spec['lab']['runtime_requirements']['platform']['lab_actions']

    logger.info("Starting test_lab")

    try:

        repo_name = git.construct_repo_name(lab_src_url)
        lab_spec = git.get_lab_spec(repo_name)
        spec_path = git.get_spec_path(repo_name)
        logger.debug("spec_path: %s" % spec_path)
        os.chdir(spec_path)
        fill_aptconf(lab_spec)
        logger.debug("Changed to Diretory: %s" % spec_path)
        logger.debug("CWD: %s" % str(os.getcwd()))

        lar = LabActionRunner(get_build_installer_steps_spec(lab_spec))
        lar.run_install_source()

        lar = LabActionRunner(get_build_steps_spec(lab_spec))
        lar.run_build_steps()

        lar = LabActionRunner(get_runtime_installer_steps(lab_spec))
        lar.run_install_source()

        lar = LabActionRunner(get_runtime_actions_steps(lab_spec))
        lar.run_init_lab()
        lar.run_start_lab()
        logger.info("Finishing test_lab: Success")
        return "Success"
    except Exception, e:
        logger.error("VMManager.test_lab failed: " + str(e))
        return "Test lab failed"


if __name__ == "__main__":
    #test_lab("https://bitbucket.org/virtual-labs/cse02-programming.git")
    print cpu_load()
    print mem_usage()
