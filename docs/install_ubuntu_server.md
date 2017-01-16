# Preparing a node for Assemblyline Installation


**Prerequisites**: 

* Ubuntu 14.04.3 Server x64 installation media.
* Install machine (or VM) should have at least 8GB RAM and 20GB of disk space
* Accessible Ubuntu APT repository
* You should know the assemblyline username and password you will use for the primary account. (we suggest 'user')
* You should know the hostname that will be used for this node.

## Install the Ubuntu 14.04.3 x64 base operating system


### Install Ubuntu 14.04.3 OS

**Boot from the installation media and follow the menu guidance below:**

* English -> Install Ubuntu Server
* Language: English (Default)
* Country: United States (Default)
* Detected Keyboard Layout: No (Default)
* Keyboard: English US (Default)
* Select a primary network interface (using the first enumerated interface).
* Hostname: Your predtermined hostname. Typically of the form al-linux-<N>.
* User: user
* Password: xxxx
* Encrypt your home directory: No (Default)
* Timezone: Eastern

**If it prompts you that a partition is in use, select 'Yes' for unmount partitions.**

* Disk: Guided - use entired disk.
* Write changes to disk: <YES>
* Choose: No automatic updates
* Install Grub boot loader: <YES>

Installation complete <Continue>

*The system will reboot.*


### On first login

#### Make sure your installation is running the lastest version

    sudo apt-get update
    sudo apt-get dist-upgrade

**Note**: If apt cannot find the Ubuntu mirror you likely need to configure your DNS or edit */etc/apt/sources.list* to match that of your internal mirror.

#### PIP mirror (OPTIONAL)

If your assemblyline cluster is not connected to the internet or cannot get access to the PIP mirrors, you can set pip to be redirected to an internal mirror.

    nano ~/.pip/pip.conf

pip.conf should look like this

    [global]
    index-url = http://my-domain.com//pypi/web/simple

Also edit your easy install file:

    nano ~/.pydistutils.cfg

.pydistutils.cfg should look like this

    [easy_install]
    index-url=http://my-domain.com/pypi/web/simple/


#### Change your IP
You need to make sure that your IP or DNS name matches either a worker, riak or a core node from your installation seed


