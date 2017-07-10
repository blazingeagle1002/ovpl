import os
import json
from __init__ import *
from httplogging.http_logger import logger
from utils.execute_commands import execute_command
from utils.envsetup import EnvSetUp


class LabSpecInvalid(Exception):
    def __init__(self, msg):
        Exception(self, msg)


class GitCommands:

    env = None
    git_clone_loc = None
    lab_spec_dir = None
    lab_spec_file = None

    def __init__(self):
        self.env = EnvSetUp.Instance()
        self.git_clone_loc = (self.env.get_config_spec())["LABMANAGER_CONFIG"]["GIT_CLONE_LOC"]
        self.lab_spec_dir = (self.env.get_config_spec())["LABMANAGER_CONFIG"]["LAB_SPEC_DIR"]
        self.lab_spec_file = (self.env.get_config_spec())["LABMANAGER_CONFIG"]["LAB_SPEC_FILE"]
        logger.debug("GIT_CLONE_LOC = %s" % str(self.git_clone_loc))
        logger.debug("LAB_SPEC_DIR = %s" % str(self.lab_spec_dir))
        logger.debug("LAB_SPEC_FILE = %s" % str(self.lab_spec_file))

    def get_git_clone_loc(self):
        return self.git_clone_loc

    def get_lab_spec_dir(self):
        return self.lab_spec_dir

    def get_lab_spec_file(self):
        return self.lab_spec_file

    def construct_repo_name(self, lab_src_url):
        # sample lab_src_url: git@github.com:vlead/ovpl.git
        logger.debug("lab_src_url: %s" % lab_src_url)
        repo = lab_src_url.split('/')[-1]
        repo_name = (repo[:-4] if repo[-4:] == ".git" else repo)
        logger.debug("repo_name: %s" % repo_name)
        return str(repo_name)

    def repo_exists(self, repo_name):
        logger.debug("dir = %s" % (self.git_clone_loc + repo_name))
        return os.path.isdir(self.git_clone_loc + repo_name)

    def clone_repo(self, lab_src_url, repo_name):
        clone_cmd = "git clone %s %s%s" % (lab_src_url, self.git_clone_loc,
                                           repo_name)
        logger.debug(clone_cmd)
        try:
            (ret_code, output) = execute_command(clone_cmd)
            logger.debug("Clone repo successful")
        except Exception, e:
            logger.error("Error Cloning the repository: " + str(e))
            raise e

    def pull_repo(self, repo_name, version):
        repo = self.git_clone_loc + repo_name
        #pull_cmd = "git --git-dir=%s/.git --work-tree=%s pull" % (repo, repo)
        pull_cmd = "git -C %s pull origin %s" % (repo, version)
        logger.debug("pull cmd: %s" % pull_cmd)
        try:
            (ret_code, output) = execute_command(pull_cmd)
            logger.debug("Pull repo successful")
        except Exception, e:
            logger.error("Error Pulling the repository: " + str(e))
            raise e

    def reset_repo(self, repo_name):
        repo = self.git_clone_loc + repo_name
        reset_cmd = "git --git-dir=%s/.git --work-tree=%s reset --hard" % (repo, repo)
        logger.debug("reset cmd: %s" % reset_cmd)
        try:
            (ret_code, output) = execute_command(reset_cmd)
            logger.debug("reset repo successful")
        except Exception, e:
            logger.error("Error Resetting the repository: " + str(e))
            raise e

    def checkout_version(self, repo_name, version=None):
        repo = self.git_clone_loc + repo_name
        if version is None:
            version = "master"
        checkout_cmd = "git --git-dir=%s/.git --work-tree=%s checkout %s" % (repo, repo, version)
        try:
            (ret_code, output) = execute_command(checkout_cmd)
            logger.debug("Checkout repo successful")
        except Exception, e:
            logger.error("Error checking out the repository: " + str(e))
            raise e

    def get_spec_path(self, repo_name):
        return self.git_clone_loc + repo_name + self.lab_spec_dir

    def get_lab_spec(self, repo_name):
        spec_file_path = self.get_spec_path(repo_name) + self.lab_spec_file
        logger.debug("spec_file_path: %s" % spec_file_path)
        if not os.path.exists(spec_file_path):
            logger.error("Lab spec file not found")
            raise LabSpecInvalid("Lab spec file not found")
        try:
            return json.loads(open(spec_file_path).read())
        except Exception, e:
            logger.error("Lab spec JSON invalid: " + str(e))
            

if __name__ == '__main__':
    git = GitCommands()
    lab_src_url = "https://github.com/Virtual-Labs/computer-programming-iiith.git"
    try:
        repo_name = git.construct_repo_name(lab_src_url)
        if git.repo_exists(repo_name):
            #  reset_repo(repo_name)
            git.pull_repo(repo_name)
        else:
            git.clone_repo(lab_src_url, repo_name)
            git.checkout_version(repo_name, None)
    except Exception, e:
        logger.debug(str(e))
