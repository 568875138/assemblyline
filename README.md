# Assemblyline

Assemblyline is a scalable *__distributed file analysis framework__*. It is designed to process millions of files per day but can also be installed on a single box.

An Assemblyline cluster consists of 3 types of boxes: Core, Datastore and Worker.

## Components

### Assemblyline Core

The Assemblyline Core server runs all the required components to receive/dispatch tasks to the different workers. It hosts to following processes:

* Redis (Queue/Messaging)
* FTP (proftpd: File transfer)
* Dispatcher (Worker tasking and job completion)
* Ingester (High volume task insgestion)
* Expiry (Data deletion)
* Alerter (Creates alerts when score threshold is met)
* UI/API (NGINX, UWSGI, Flask, AngularJS)
* Websocket (NGINX, Gunicorn, GEvent)

### Assemblyline Datastore

Assemblyline uses Riak as its persistent data storage. Riak is a Key/Value pair datastore with SOLR integration for search. It is fully distributed and horizontally scalable.

### Assemblyline Workers

Workers are responsible for processing the given files.
Each worker has a hostagent process that starts the different services to be run on the current worker and makes sure that those service behave.
The hostagent is also responsible for downloading and running virtual machines for services that are required to run inside of a virtual machine or that only run on Windows.

### Assemblyline reference manual

If you want to know more about Assemblyline, you can get a copy of the full [reference manual](https://bitbucket.org/cse-assemblyline/assemblyline/src/master/manuals/). It can also be found in the `assemblyline/manuals` directory of your installation.

## Getting started

### Use as an appliance

An appliance is a full deployment that's self contained on one box/vm. You can easily deploy an Assemblyline appliance by following the appliance creation documentation.

[Install Appliance Documentation](docs/install_appliance.md)

### Deploy a production cluster

If you want to scan a massive amount of files then you can deploy Assemblyline as a production cluster. Follow the cluster deployment documentation to do so.

[Install Cluster Documentation](docs/install_cluster.md)

### Development

You can help us out by creating new services, adding functionality to the infrastructure or fixing bugs that we currently have in the system.

You can follow this documentation to get started with development.

#### Setup your development desktop

Setting up your development desktop can be done in two easy steps:

* Clone the Assemblyline repo
* run the setup script

##### Clone repo

First, create your Assemblyline working directory:

    export ASSEMBLYLINE_DIR=~/git/al
    mkdir -p ${ASSEMBLYLINE_DIR}

Then clone the Assemblyline repo with one of those two techniques:

###### SSH Keys

    ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    cat ~/.ssh/id_rsa.pub  # Add this output to your bitbucket trusted keys

    printf "Host bitbucket.org\n\tHostName bitbucket.org\n\tUser git\n\tIdentityFile ~/.ssh/id_rsa\n" > ~/.ssh/config
    chmod 600 ~/.ssh/id_rs*
    chmod 600 ~/.ssh/config
    ssh -T git@bitbucket.org

    cd $ASSEMBLYLINE_DIR
    git clone git@bitbucket.org:cse-assemblyline/assemblyline.git -b prod_3.1

###### App password

First you need to create an app password for your user on bitbucket, then:

    export GIT_USER=<your git user>
    export GIT_PASS=<your app password>
    cd $ASSEMBLYLINE_DIR
    git clone https://${GIT_USER}:${GIT_PASS}@bitbucket.org/cse-assemblyline/assemblyline.git -b prod_3.1

##### Clone other repos

    ${ASSEMBLYLINE_DIR}/assemblyline/al/run/setup_dev_environment.py

**NOTE**: The setup script will use the same git remote that you've used to clone the Assemblyline repo

#### Setup your development VM

After you're done setting up your Desktop, you can setup the VM from which you're going to run your personal Assemblyline instance.

##### Local VM

If you want to use a local VM make sure your desktop is powerful enough to run a VM with 2 cores and 8 GB of memory.

You can install the OS by following this doc: [Install Ubuntu Server](docs/install_ubuntu_server.md)

##### (Alternative) Amazon AWS or other cloud providers

Alternatively you can use a cloud provider like Amazon AWS. We recommend 2 cores and 8 GB of ram for you Dev VM. In the case of AWS this is the equivalent to an m4.large EC2 node.

Whatever provider and VM size you use, make sure you have a VM with Ubuntu 14.04.3 installed.

##### Installing the assemblyline code on the dev VM

When you're done installing the OS on your VM, you need to install all Assemblyline components on that VM.

To do so, follow the documentation: [Install a Development VM](docs/install_development_vm.md)

#### Finishing setup

Now that the code is synced on your desktop and your Dev VM is installed, you should setup your development UI. Make sure to run the tweaks on your Dev VM to remove the id_rsa keys in order to have your desktop drive the code in your VM instead of the git repos.

If you have a copy of PyCharm Pro, you can use the remote python interpreter and remote deployment features to automatically sync code to your Dev VM. Alternatively, you can just manually rsync your code to your Dev VM every time you want to test your changes.

##### Setting up pycharm

Open PyCharm and open your project: ~/git/al (or ASSEMBLYLINE_DIR if you change the directory)

Pycharm will tell you there are unregistered git repos, click the 'add roots' button and add the unregistered repos.

###### Remote interpreter (pro only)

If you have the PyCharm Pro version you can set up the remote interpreter:

    file -> settings
    Project: al -> Project Interpreter

    Cog -> Add Remote

    SSH Credentials
    host: ip/domain of your VM
    user: al
    authtype: pass or keypair if AWS
    password: whatever password you picked in the create_deployment script

    click ok

**NOTE**: Leave the settings page opened for remote deployments. At this point you should be done with your remote interpreter. Whenever you click the play or debug button it should run the code on the remote Dev VM.

###### Remote Deployment (PyCharm Pro only)

Still in the settings page:

    Build, Execution, Deployment - > Deployment

    Plus button
    Name: assemblyline dev_vm
    Type: SFTP

    click OK

    # In the connection tab
    SFTP host: ip/domain of your VM
    User name: al
    authtype: pass or keypair if AWS
    password: whatever password you picked in the create_deployment script

    Click autodetect button

    Switch to Mappings page
    click "..." near Deployment path on server
    choose pkg
    click ok

**NOTE**: At this point you should be done with your remote deployment. When you make changes to your code, you can sync it to the remote Dev VM by opening the 'Version Control' tab at the bottom of the interface, selecting 'Local changes', right clicking on Default and selecting upload to 'assemblyline dev_vm'
#### Create a new service

To create a new service, follow the create service tutorial.

[Create service tutorial](docs/create_new_service.md)
