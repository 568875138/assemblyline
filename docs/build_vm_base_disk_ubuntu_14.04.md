# Creating the Ubuntu 14.04 base VM disk
This will install the bootstrap code for an assemblyline base VM image. All actions need to be performed from inside de machine your installing.

**Prerequisites:**

* You have to install the Ubuntu base OS before. See [Install Ubuntu Server](install_ubuntu_server.md)
* You have copied **install_seed.py** on the **~/** directory on your VM

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

### Drop your install seed

    mkdir $PYTHONPATH/settings
    cp ~/install_seed.py $PYTHONPATH/settings
    touch $PYTHONPATH/settings/__init__.py

### Clone/create main repos

    # From bitbucket HTTPS
    cd $PYTHONPATH
    BB_USER=<your_bitbucket_username>
    git clone https://${BB_USER}@bitbucket.org/cse-assemblyline/assemblyline.git

### Install bootstrap code
    
    export AL_SEED=<python-path-to-seed-module>.seed
    /opt/al/pkg/assemblyline/al/install/install_linuxvm_bootstrap.py 
    
### Create a shrunken copy of the disk image.

From the Unix command line:

    mv base-ubuntu1404x64srv.001.qcow2 base-ubuntu1404x64srv.001.qcow2.original
    qemu-img convert -O qcow2 -f qcow2 base-ubuntu1404x64srv.001.qcow2.original base-ubuntu1404x64srv.001.qcow2
    sudo chown `whoami` base-ubuntu1404x64srv.001.qcow2

### Upload the new base disk to the disk store:

    Now you need to upload you disk (base-ubuntu1404x64srv.001.qcow2) to the location specified in your seed's in `filestore.support_urls` + `vm/disks`.

