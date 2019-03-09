# gpu-deploy
Fabric library for Docker GPU deployment

Requirements: nvidia-docker 2.0.3, nvidia-container-runtime 1.0.0

On all host machines, set the default docker runtime to nvidia by adding the line `"default-runtime": "nvidia"` to `/etc/docker/daemon.json`
    


## Instalation

    sudo apt-get install fabric=1.14.0-1

    pip2 install git+https://github.com/atlab/gpu-deploy.git

    <!--git clone git@github.com:atlab/gpu-deploy.git

    cd gpu-deploy

    pip2 install . -->

## Usage

See the `fabfile.py` in the example/ folder for an example usage of gpu_deploy. `/example/` is a template for organizing required files; notice how these files are organized in directories: `Dockerfile` and `docker-compose.yml` must be together in a directory, all `*.py` scripts must be together in another directory, and the `.env` file can be in any location specified by the user.

Navigate to the `example` directory:
```bash
    cd example
```

To launch 2 jupyter notebook containers on the host `at-gpu-ex.bdc.bcm.edu` with 3 gpus per container:
```bash
    fab -H at-gpu-ex.bdc.bcm.edu deploy_atlab:n=2,gpus=3
```

To stop all of these jupyter notebook containers:
```bash
    fab -H at-gpu-ex.bdc.bcm.edu stop_atlab
```

To run 4 `hello.py` jobs on the host `at-gpu-ex.bdc.bcm.edu` with 1 gpu per container:
```bash
    fab -H at-gpu-ex.bdc.bcm.edu deploy_atlab:hello,n=4
```

To stop these `hello.py` jobs:
```bash
    fab -H at-gpu-ex.bdc.bcm.edu stop_atlab:hello
```
