from gpu_deploy import *



DOCKER_DIR = abspath('./docker')
SCRIPTS_DIR = abspath('./scripts')
ENV_PATH = abspath('.env')


d = Deploy(DOCKER_DIR, SCRIPTS_DIR, ENV_PATH)

def deploy_atlab(script=None, n=10, gpus=1, token=None):
    d.deploy('atlab', script, n, gpus, token)

def stop_atlab(script=None):
    d.stop('atlab', script)
