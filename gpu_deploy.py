from fabric.state import env
import fnmatch
from distutils.util import strtobool

from fabric.api import local, abort, run, sudo
from fabric.context_managers import cd, settings, hide, shell_env, lcd
import re
from os.path import join, realpath, dirname, basename, abspath
from getpass import getpass
from fabric.contrib.files import exists
from fabric.operations import put
from fabric.utils import puts
import inspect

device_re = r'/dev/nvidia(?P<device>\d+)'


def with_sudo():
    """
    Prompts and sets the sudo password for all following commands. 

    Use like

    fab with_sudo command
    """
    env.sudo_password = getpass('Please enter sudo password: ')


def on(which, *args):
    env.hosts = list(filter(lambda x: x not in args, getattr(env, which).split(',')))


def excluding(*args):
    with hide('output', 'running'):
        env.hosts = list(filter(lambda x: x not in args, env.hosts))


def all_machines():
    """
    Sets the machines on which the following commands are executed to the `machines` in `.~/fabricrc`. 
    This overrides the `-H` argument. 

    Use like

    fab all_machines -P command
    """
    env.hosts = env.machines.split(',')


def gpu_devices():
    ret = []
    for dev in run('ls /dev/nvidia*').split():
        m = re.match(device_re, dev)
        if m:
            ret.append(m.groupdict()['device'])
    return ret


def free_gpu_slots():
    with hide('output', 'running'):
        gpus = gpu_devices()
        containers = run('docker ps -q --no-trunc').split()
        for container in containers:
            host_devs = run("docker exec {} /bin/ls /dev".format(container))
            for dev in re.findall(r'nvidia(?P<device>\d+)', host_devs):
                if dev in gpus:
                    gpus.remove(dev)
    return gpus


def availability():
    puts(env.host_string + ' free GPUs: ' + ','.join(free_gpu_slots()))


def docker_login():
    run('docker login')


def remove_old_containers():
    with settings(warn_only=True):
        run('docker ps -aq| xargs docker rm')


def remove_old_images():
    with settings(warn_only=True):
        run('docker image prune -f')


def clean():
    remove_old_containers()
    remove_old_images()


def containers():
    with hide('running'):
        ret = run("docker ps --format '{{.Names}} -> {{.ID}}'")
    return [r.strip() for r in ret.split('\n') if '->' in r]


ps = containers


def stop(wildcard):
    candidates = {k: v for k, v in map(lambda s: s.split(' -> '), containers())}
    selection = fnmatch.filter(candidates.keys(), wildcard)
    stop = [candidates[s] for s in selection]
    if len(stop) > 0:
        run('docker stop {}'.format(' '.join(stop)))


def kill(wildcard):
    candidates = {k: v for k, v in map(lambda s: s.split(' -> '), containers())}
    selection = fnmatch.filter(candidates.keys(), wildcard)
    stop = [candidates[s] for s in selection]
    if len(stop) > 0:
        run('docker kill {}'.format(' '.join(stop)))


def logs(pattern, wildcard='*'):
    candidates = {k: v for k, v in map(lambda s: s.split(' -> '), containers())}
    selection = fnmatch.filter(candidates.keys(), wildcard)
    candidates = [candidates[s] for s in selection]
    for candidate in candidates:
        run('docker logs {} | egrep "{}"'.format(candidate, pattern))


class Deploy():

    def __init__(self, docker_dir, scripts_dir, env_path):
        assert basename(env_path) == '.env', 'env_file for docker-compose must be named ".env"'
        assert basename(scripts_dir) != str(env.user), 'scripts directory name cannot be the same as the username'

        self.local_docker_dir = docker_dir
        self.local_scripts_dir = scripts_dir
        self.local_env_path = env_path

        self.host_dir = join('/home', env.user, '.gpu-deploy')
        self.host_docker_dir_tmp = join(self.host_dir, basename(self.local_docker_dir))
        self.host_docker_dir = join(self.host_dir, env.user)
        self.host_scripts_dir = join(self.host_dir, basename(self.local_scripts_dir))

    def initialize(self):
        run('rm -rf ' + self.host_dir)
        run('mkdir -p ' + self.host_dir)
        local('scp -r {} {}@{}:{}'.format(self.local_docker_dir, env.user, env.host_string, self.host_dir))
        run('mv {} {}'.format(self.host_docker_dir_tmp, self.host_docker_dir))
        local('scp -r {} {}@{}:{}'.format(self.local_scripts_dir, env.user, env.host_string, self.host_dir))
        local('scp {} {}@{}:{}'.format(self.local_env_path, env.user, env.host_string, self.host_docker_dir))

    def finalize(self):
        remove_old_images()
        run('rm -rf ' + self.host_dir)

    def no_gpu_deploy(self, service, script=None, token=None):
        _service = service

        name = env.user + '_' + service + '_{script}_no_gpu'

        self.initialize()

        with cd(self.host_docker_dir):

            if script is None:
                name = name.format(script='notebook')
                args = '-p 8888:8888'
                if token is not None:
                    service += ' --NotebookApp.token={}'.format(token)
            else:
                name = name.format(script)
                args = ' -v {}:/scripts'.format(join(self.host_scripts_dir))
                args += ' --entrypoint "python3 /scripts/{}.py"'.format(script)

            exists = run('(docker ps | grep {} > /dev/null 2>&1) && echo True'.format(name), warn_only=True)
            if exists == 'True':
                puts('Notebook already exists')
                return

            run('(docker ps -a | grep {name}) && docker rm {name}'.format(name=name),
                warn_only=True)
            run('docker-compose build --no-cache --build-arg ssh_prv_key="$(cat ~/.ssh/id_rsa)" --build-arg ssh_pub_key="$(cat ~/.ssh/id_rsa.pub)" {}'.format(_service))
            run('docker-compose run -d -e NVIDIA_VISIBLE_DEVICES=none {} --name {} {}'.format(args, name, service))

    def deploy(self, service, script=None, n=10, gpus=1, token=None, pyargs=None):
        _service = service
        gpus = int(gpus)
        n = int(n)
        pyargs = '' if pyargs is None else ' {}'.format(pyargs)

        if len(free_gpu_slots()) == 0:
            puts('No free gpus on {}'.format(env.host_string))
            return

        self.initialize()
        with cd(self.host_docker_dir):
            run('docker-compose build --no-cache --build-arg ssh_prv_key="$(cat ~/.ssh/id_rsa)" --build-arg ssh_pub_key="$(cat ~/.ssh/id_rsa.pub)" {}'.format(service))
            bare_run_str = 'docker-compose run -d'
            free_gpus = sorted(free_gpu_slots())
            gpu_i = 0
            container_i = 0
            gpu_groups = []
            while gpu_i < len(free_gpus):
                service = _service
                gpu_j = gpu_i + gpus
                gpu_ids = free_gpus[gpu_i: gpu_j]

                if len(gpu_ids) < gpus or container_i >= n:
                    break

                name = env.user + '_' + service + '_{script}_gpu_' + '_'.join(gpu_ids)
                args = ' -e NVIDIA_VISIBLE_DEVICES={}'.format(','.join(gpu_ids))
                gpu_run_str = bare_run_str + args

                if script is None:
                    name = name.format(script='notebook')
                    args = '-p 444{}:8888'.format(gpu_ids[0])
                    if token is not None:
                        service += ' --NotebookApp.token={}'.format(token)
                else:
                    name = name.format(script=script)
                    args = ' -v {}:/scripts'.format(join(self.host_scripts_dir))
                    args += ' --entrypoint "python3 /scripts/{}.py{}"'.format(script, pyargs)

                run('(docker ps -a | grep {name}) && docker rm {name}'.format(name=name),
                    warn_only=True)
                run('{} {} --name {} {}'.format(gpu_run_str, args, name, service))

                gpu_i = gpu_j
                container_i += 1
                gpu_groups.append(','.join(gpu_ids))

        self.finalize()
        puts('started service {} on {} on GPUs {}'.format(env.host_string, service, ' '.join(gpu_groups)))

    def stop(self, service, script=None, token=None):
        wildcard = env.user + '_' + service + '_{script}_gpu'
        wildcard = wildcard.format(script='notebook' if script is None else script)
        stop('{}*'.format(wildcard))

    def no_gpu_stop(self, service, script=None):
        wildcard = env.user + '_' + service + '_{script}_no_gpu'
        wildcard = wildcard.format(script='notebook' if script is None else script)
        stop('{}*'.format(wildcard))
