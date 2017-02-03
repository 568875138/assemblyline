# Assemblyline Development VM installation instruction
This will install assemblyline in a self contained VirtualMachine. All actions need to be performed from inside de virtual machine your installing.

*NOTE: Development VM installation disables Assemblyline VirtualMachine service support.*

**Prerequisites:**

* You have to install the Ubuntu base OS before. See [Install Ubuntu Server](install_ubuntu_server.md)
* Your machine should have a minimum of 8GB RAM and 20GB of disk space(less is possible through SOLR/Riak configs)
* You are on a network connected to the internet and can download file from Amazon S3

## Install bootstrap and source

### Install GIT and SSH

    sudo apt-get update
    sudo apt-get -y install git ssh

### Update .bashrc

    cat >> ~/.bashrc <<EOF
    export PYTHONPATH=/opt/al/pkg
    source /etc/default/al
    EOF

    source ~/.bashrc

    # The source command will generate an error, but it will disappear once the install is complete.

### Create repository directory

    sudo mkdir -p ${PYTHONPATH} &&
    sudo chown -R `whoami`:`groups | awk '{print $1}'` ${PYTHONPATH}/.. &&
    cd ${PYTHONPATH}

### Clone/create main repos

    # Clone repos using ssh keys
    cd
    ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    cat ~/.ssh/id_rsa.pub  # Add this output to your bitbucket trusted keys (read-only)

    printf "Host bitbucket.org\n\tHostName bitbucket.org\n\tUser git\n\tIdentityFile ~/.ssh/id_rsa\n" > ~/.ssh/config
    chmod 600 ~/.ssh/id_rs*
    chmod 600 ~/.ssh/config
    ssh -T git@bitbucket.org

    mkdir $PYTHONPATH/../.ssh/
    cp ~/.ssh/* $PYTHONPATH/../.ssh/
    chmod 700 $PYTHONPATH/../.ssh/

    cd $PYTHONPATH
    git clone git@bitbucket.org:cse-assemblyline/assemblyline.git

### Create Dev VM Deployment

    /opt/al/pkg/assemblyline/deployment/create_deployment.py

    # Answer the questions from deployment script
    # NOTE:
    #    Answer to "Which deployment type would you like?" has to be: 1
    #    Answer to "Where would you like us to create your deployment?" has to be: /opt/al/pkg
    #    You don't really need to save the al_private to your git repo.

## Install Riak

### Run install script

    export AL_SEED=al_private.seeds.deployment.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    sudo reboot

    export AL_SEED=al_private.seeds.deployment.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    unset AL_SEED

## Install Core

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_core.py

## Install Worker

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_worker.py

## Tweaks (optional but recommended)

You should do this tweak if you don't plan on coding on this VM and instead you want to code on your desktop and sync the code to this VM via SSH or via pycharm remote deployment interface. This will prevent the VM to be able to pull the code when the hostagent is restarted.

Remove the id_rsa files with the following command:

    sudo rm ~/.ssh/id_rsa*
    sudo rm /opt/al/.ssh/id_rsa*
