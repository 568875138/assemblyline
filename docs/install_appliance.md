# Assemblyline appliance installation instruction
This will install assemblyline on a bare-metal machine. All actions need to be performed from inside de machine your installing.

**Prerequisites:**

* You have to install the Ubuntu base OS before. See [Install Ubuntu Server](install_ubuntu_server.md)

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

### Create repository directory

    sudo mkdir -p ${PYTHONPATH} &&
    sudo chown -R `whoami`:`groups | awk '{print $1}'` ${PYTHONPATH}/.. &&
    cd ${PYTHONPATH}

### Clone/create main repos

    # Preferred bitbucket way (ssh keys) [Use default values with no passphrase for the ssh-keygen]
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

    OR

    # From bitbucket HTTPS
    cd $PYTHONPATH
    BB_USER=<your_bitbucket_username>
    git clone https://${BB_USER}@bitbucket.org/cse-assemblyline/assemblyline.git

## Install Riak

### Run install script

    export AL_SEED=assemblyline.al.install.seeds.assemblyline_appliance.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    sudo reboot

    export AL_SEED=assemblyline.al.install.seeds.assemblyline_appliance.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    unset AL_SEED

## Install Core

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_core.py

## Install Worker

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_worker.py

