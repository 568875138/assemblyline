# Assemblyline

Assemblyline is a scalable *__distributed file analysis framework__*. It is designed to process millions of files per day but can also be installed on a single box.

An Assemblyline cluster consist of 3 types of boxes: Core, Datastore and Worker.

## Components

### Assemblyline Core

The Assemblyline Core server runs all the required components to receive/dispatch tasks to the different workers. It hosts to following processes:

* Redis (Queue/Messaging)
* FTP (proftpd: File transfer)
* Dispatcher (Worker tasking and job completion)
* Ingester (High volume task insgestion)
* Expiry (Data deletion)
* Alerter (Creates alert when score threshold is met)
* UI/API (NGINX, UWSGI, Flask, AngularJS)
* Websocket (NGINX, Gunicorn, GEvent)

### Assemblyline Datastore

Assemblyline uses Riak as its persistent data storage. Riak is a Key/Value pair datastore with SOLR integration for search. It is fully distributed and horizontally scalable.

### Assemblyline Workers

Workers are actually responsible to process the given files.
Each worker has a hostagent process that starts the different service to be run on the current worker and make sure that those service behave.
The hostagent is also responsible to download and run virtual machines for service that are required to run inside of a virtual machine or that only run under windows.

## Get started

### Use as an appliance

An appliance is a full deployment self contained on one box/vm. You can easily deploy an assemblyline appliance by following the appliance creation documentation.

[Install Appliance Documentation](docs/install_appliance.md)

### Deploy a production cluster

You want to scan a massive amount of files then you can deploy assemblyline as a production cluster. Follow the cluster deployment documentation to do so.

[Install Cluster Documentation](docs/install_cluster.md)

### Development

You can help us out by creating new services, adding functionalities to the infrastructures or fixing bugs that we currently have in the system.

You can follow this documentation to get you started developping.

#### Setup your development desktop

Setting up your developement desktop can be done in two easy steps:

* Clone the assemblyline repo
* run the setup script

##### Clone repo

First create your assemblyline working directory:

    export ASSEMBLYLINE_DIR=~/git/al
    mkdir -p ${ASSEMBLYLINE_DIR}

Then clone assemblyline repo with one of those two techniques:

###### SSH Keys

    ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
    cat ~/.ssh/id_rsa.pub  # Add this output to your bitbucket trusted keys

    printf "Host bitbucket.org\n\tHostName bitbucket.org\n\tUser git\n\tIdentityFile ~/.ssh/id_rsa\n" > ~/.ssh/config
    chmod 600 ~/.ssh/id_rs*
    chmod 600 ~/.ssh/config
    ssh -T git@bitbucket.org

    cd $ASSEMBLYLINE_DIR
    git clone git@bitbucket.org:cse-assemblyline/assemblyline.git

###### App password

First you need to create an app password for your user in bitbucket then:

    export GIT_USER=<your git user>
    export GIT_PASS=<your app password>
    cd $ASSEMBLYLINE_DIR
    git clone https://${GIT_USER}:${GIT_PASS}@bitbucket.org/cse-assemblyline/assemblyline.git

##### Clone other repos

    ${ASSEMBLYLINE_DIR}/assemblyline/al/run/setup_dev_environment.py

**NOTE**: The setup script will use the same git remote that you've use to clone the assemblyline repo

#### Setup your development VM

After your done setting up your Desktop, you can setup the VM from which your gonna run your personal assemblyline instance.

##### Local VM

If you want to use a local VM make sure your desktop is powerful enough to run a VM with 2 cores and 8 GB.

You can install the OS by following this doc: [Install Ubuntu Server](docs/install_ubuntu_server.md)

##### (Alternative) Amazon AWS or other cloud providers

Alternatively you can use a cloud provider like Amazon AWS. We recommend 2 core and 8 GB of ram for you dev VM. In the case of AWS this is the equivalent to an m4.large EC2 node.

Whatever provider and VM size you use, make sure you have a VM with Ubuntu 14.04 installed.

##### Installing the assemblyline code on the dev VM

When your done installing the OS on your VM, you need to install all assemblyline components on that VM.

To do so, follow the documentation: [Install a Development VM](docs/install_development_vm.md)

#### Finishing setup

Now that the code is synced on your desktop and your Dev VM is installed. You should setup you development UI. Make sure that you ran the tweak on your Dev VM to remove the id_rsa keys because you'll want you desktop to drive the code in your VM not the git repos.

If you have a copy of pycharm pro, you can use the remote python interpreter and remote deployment features to automatically sync code to your Dev VM. Alternatively, you can just manually rsync your code to your Dev VM every time you want to test your changes.

##### Setting up pycharm

Open pycharm and open your project: ~/git/al (or ASSEMBLYLINE_DIR if you change the directory)

Pycharm will tell you there are unregistered git repos, click the 'add roots' button

###### Remote interpreter (pro only)

If you have the pro version you can setup the remote interpreter.

    file -> settings
    Project: al -> Project Interpreter

    Cog -> Add Remote

    SSH Credentials
    host: ip/domain of your VM
    user: al
    authtype: pass or keypair if AWS
    password: whatever password you picked in the create_deployment script

    click ok

**NOTE**: Leave settings page opened for remote deployment. At this point you should be done with your remote interpreter. Whenever you click the play or debug button it should run the code on the remote Dev VM.

###### Remote Deployment (pro only)

Still in the settings page

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

**NOTE**: At this point you should be done with your remote deployment. When you make changes to you code, to sync it to the remote Dev VM, open the 'Version Control' tab at the bottom of the interface, select 'Local changes', right click on Default and select upload to 'assemblyline dev_vm'
#### Create a new service

To create a new service, follow the create service tutorial.

[Create service tutorial](docs/create_new_service.md)

#### License (or lack thereof) and Conditions of use

As is fairly evident, we haven't selected a license for this project as of yet. As discussed when members were first granted read access to the repository, dissemination is based on the premise of originator controlled. If you feel there are other partners that would benefit from an early view and would be able to contribute, please contact the project leads and we should be able to sort it out.

We will soon be splitting the platform and services into two separate repo's, so please treat the services as slightly more sensitive than the platform itself, ie: release it and perish!!! ... but seriously, we do not grant anyone the right to do anything other than deploy the platform and use it. No sharing, presenting, etc without our knowledge. 

We hope to have a clear release plan soon.


