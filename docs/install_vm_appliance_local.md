# Assemblyline VM appliance installation instruction
This will install assemblyline in a self contained VirtualMachine. All actions need to be performed from inside de virtual machine your installing.

*NOTE: VM Appliance installation disables Assemblyline VirtualMachine service support.*

**Prerequisites:**

* You have to install the Ubuntu base OS before. See [Install Ubuntu Server](install_ubuntu_server.md)
* Your machine should have a minimum of 8GB RAM and 20GB of disk space(less is possible through SOLR/Riak configs)
* You have copied installdeps-assemblyline-bundle.tar.gz into your home directory

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

    The source command will generate an error, but it will disappear once the install is complete.

### Create repository directory

    sudo mkdir -p ${PYTHONPATH} &&
    sudo chown -R `whoami`:`groups | awk '{print $1}'` ${PYTHONPATH}/.. &&
    cd ${PYTHONPATH}

### Unpack install dependancy file

    mkdir -p ${PYTHONPATH}/../var/installdeps
    mv ~/installdeps-assemblyline-bundle.tar.gz ${PYTHONPATH}/../var/installdeps
    cd ${PYTHONPATH}/../var/installdeps
    tar zxvf installdeps-assemblyline-bundle.tar.gz
    rm installdeps-assemblyline-bundle.tar.gz

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

    OR

    # From your host if you have a git server running
    cd $PYTHONPATH
    export AL_BRANCH=production
    git clone http://192.168.122.1/git/assemblyline --branch ${AL_BRANCH}

## Install Riak

### Run install script

    export AL_SEED=assemblyline.al.install.seeds.assemblyline_appliance_local_vm.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    sudo reboot

    export AL_SEED=assemblyline.al.install.seeds.assemblyline_appliance_local_vm.seed
    /opt/al/pkg/assemblyline/al/install/install_riak.py
    unset AL_SEED

## Install Core

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_core.py

## Install Worker

### Run install script

    /opt/al/pkg/assemblyline/al/install/install_worker.py

