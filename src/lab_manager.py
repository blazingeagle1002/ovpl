from exceptions import Exception
import requests
import time
import math

from __init__ import *
from httplogging.http_logger import logger
from utils.envsetup import EnvSetUp
from utils.git_commands import GitCommands


class LabManager:
    env = None
    git = None

    def __init__(self):
        self.env = EnvSetUp.Instance()
        self.git = GitCommands()

    def get_lab_reqs(self, lab_src_url, version=None):
        logger.debug("Will return lab spec")
        try:
            repo_name = self.git.construct_repo_name(lab_src_url)
            if version is None:
                version = "master"
            if self.git.repo_exists(repo_name):
                self.git.reset_repo(repo_name)
                self.git.checkout_version(repo_name, version)
                self.git.pull_repo(repo_name, version)
            else:
                self.git.clone_repo(lab_src_url, repo_name)
                self.git.checkout_version(repo_name, version)

            return self.git.get_lab_spec(repo_name)
        except Exception, e:
            logger.error("Error: %s" % str(e))
            raise e

    def test_lab(self, vmmgr_ip, port, lab_src_url, version=None):
        if 'http' not in vmmgr_ip:
            error = 'Protocol not specified in VMManager host address!!'
            raise Exception(error)
        logger.debug("vmmgr_ip = %s, port = %s, lab_src_url = %s" %
                     (vmmgr_ip, port, lab_src_url))
        payload = {"lab_src_url": lab_src_url, "version": version}
        config_spec = self.env.get_config_spec()
        TEST_LAB_API_URI = config_spec["VMMANAGER_CONFIG"]["TEST_LAB_URI"]
        url = '%s:%s%s' % (vmmgr_ip, port, TEST_LAB_API_URI)
        logger.debug("url = %s, payload = %s" % (url, str(payload)))
        exception_str = ""
        for i in (1, 2, 4, 8, 16):
            time.sleep(i)
            try:
                response = requests.post(url=url, data=payload)
                logger.debug("response = %s" % response)
                return ("Success" in response.text, response.text)
            except Exception, e:
                exception_str = str(e)
                attempts = ['first', 'second', 'third', 'fourth', 'fifth']
                logger.error("Error installing lab on VM for the %s attempt with error %s" %
                             (attempts[int(math.log(i)/math.log(2))], str(e)))
        return (False, exception_str)

if __name__ == '__main__':

    def test_testlab():
        vmmgrurl = "http://10.2.56.4"
        port = "9089"
        lab_src_url = "https://github.com/Virtual-Labs/computer-programming-iiith.git"
        labmgr = LabManager()
        try:
            (ret_val, ret_str) = labmgr.test_lab(vmmgrurl, port, lab_src_url)
            if (ret_val):
                logger.debug("Test Successful, ret_val = %s, ret_str = %s" %
                             (str(ret_val), ret_str))
            else:
                logger.debug("Test UnSuccessful, ret_val = %s, ret_str = %s" %
                             (str(ret_val), ret_str))
        except Exception, e:
            logger.debug("Exception occured , error = %s" % str(e))

    def test_get_lab_reqs():
        lab_src_url = "https://github.com/Virtual-Labs/computer-programming-iiith.git"
        labmgr = LabManager()
        try:
            lab_spec = labmgr.get_lab_reqs(lab_src_url, version=None)
            logger.debug("Lab spec: %s" % str(lab_spec))
        except Exception, e:
            logger.error("Test failed with error: " + str(e))

    #    test_testlab()
    test_get_lab_reqs()
