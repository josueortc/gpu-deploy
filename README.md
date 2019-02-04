# gpu-deploy
Fabric library for Docker GPU deployment

Requirements: nvidia-docker 2.0.3, nvidia-container-runtime 1.0.0
On all host machines, set the default docker runtime to nvidia by adding the line `"default-runtime": "nvidia"` to `/etc/docker.daemon.json`
    {
        "runtimes": {
            "nvidia": {
                "path": "nvidia-container-runtime",
                "runtimeArgs": []
            }
        },
        "default-runtime": "nvidia"
    }
    

To Install:

    sudo apt-get install fabric=1.14.0-1

    git clone git@github.com:atlab/gpu-deploy.git

    cd gpu-deploy

    pip install .

`/example/` is a template for creating `fabfile.py`, `Dockerfile`, `docker-compose.yml`, `.env`, and scripts.  Pay attention to how these files should be organized in directories.  To use, navigate to the example directory with the fabfile:

    cd example

To launch 2 jupyter notebook containers on the host `at-gpu-ex.bdc.bcm.edu` with 3 gpus per container:

    fab -H at-gpu-ex.bdc.bcm.edu deploy_atlab:n=2,gpus=3

To stop all of these jupyter notebook containers:

    fab -H at-gpu-ex.bdc.bcm.edu stop_atlab

To run 4 `hello.py` jobs on the host `at-gpu-ex.bdc.bcm.edu` with 1 gpu per container:

    fab -H at-gpu-ex.bdc.bcm.edu deploy_atlab:hello,n=4

To stop these `hello.py` jobs:

    fab -H at-gpu-ex.bdc.bcm.edu stop_atlab:hello
