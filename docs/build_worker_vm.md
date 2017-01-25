# Building a New Virtual Machine for Assemblyline

### Pre-requisites

You are on your desktop and you have libvirt installed. You need to make sure that "datastore.al" is non route-able on your box because this is an DNS redirection that we use to bootstrap a single VM on multiple environment. You can't create VM from a worker or an appliance...

### Get or create a base disk

This tutorial is meant to teach you how to create a VM disk for your service. You must derive your VM disk from a base image of either a windows or a linux box.

For documentation on how to create base disk, follow these links (Note: often these base disks are already created and available for your use. Ask the dev team):

* [Base disk - Ubuntu 14.04](build_vm_base_disk_ubuntu_14.04.md)
* [Base disk - Windows 7](build_vm_base_disk_windows_7.md)
* [Base disk - Windows 10](build_vm_base_disk_windows_10.md)
* [Base disk - Ubuntu 2k8](build_vm_base_disk_windows_2k8.md)

### Create your derived disk image

qemu-img is the the qemu disk tool used to create / modify / convert kvm-qemu compatible disk images. We use it with the -b (backing disk) option:

    qemu-img create -f qcow2 {NEWDISK_NAME}.qcow2 -b {BASEDISK_NAME}.qcow2

### Create a Virtual Machine and finish mastering the new disk.

virt-manager this the GUI front end for libvirt/kvm.

    virt-manager

Do the following:

    Right Click localhost (QEMU)
      New
        Name: ServiceName.001
        Choose how you would like to install the operating system:
            select Import existing disk
        Forward

        Provide the existing storage path:
          Browse and select the .qcow image you create above.

        Choose an operating system type and version:
          OS Type: <Your OS Type>
          Version: <Your OS Variant>
        Forward

        Choose Memory and CPU (This can be changed later)
          Memory (RAM): 2048
          CPUs: 2
        Forward

        Ready to begin installation of ServiceName.001:
          Check 'Customize configuration before install'
        Finish

    Select 'Disk 1'
       Expand 'Advanced Options'
         Change Disk bus to 'Virtio'
         Change Storage format to 'qcow2'
         Click Apply

    Click NIC:nn:nn:nn
      Select Device model 'virtio'
      Click Apply

**Note:** It should now take a few seconds to initialize the VM configuration and launch the VM for the first time.

### Install your service dependencies and update git

#### First turn off the hostagent-bootstrap
This is how the system bootstrap. Since your running on a system where "datastore.al" is not route-able, the bootstrap feature is failling constantly in the background.

    #Linux
    sudo service hostagent stop

    #Windows
    Open task manager and kill the wscript.exe process
    Close the terminal windows that opened at boot

#### Get an updated version of your code
Update the assemblyline code to the latest version:

    cd /opt/al/pkg/assemblyline && git pull

#### Perform service specific installation
Run the following:

    #Linux
    sudo su -c "PYTHONPATH=/opt/al/pkg AL_SEED=<python_classpath_to_your_seed>.seed AL_SEED_STATIC=<python_classpath_to_your_seed>.seed python /opt/al/pkg/al_services/alsvc_<service_name>/installer.py"

    #Windows
    set AL_SEED=<path_to_your_seed>.seed
    /opt/al/pkg/al_services/alsvc_<service_name>/installer.py

Power off the VM completely

**Note:** Follow additional instructions on screen if any.

### Upload this new base disk to the disk store

Now you need to upload you disk to the location specified in your seeds in `filestore.support_urls` + `vm/disks`.

### Create your Virtual Machine Entry via the AL UI

    * Admin Drop Down (Upper Right Corner) -> Choose 'Virtual Machines'
    * Click + Add Virtual Machine
    * Virtual Machine Name: <ServiceName>
    * Os Type: <Your OS Type>
    * OS Variant: <Your OS Variant>
    * VCpus 2
    * RAM: 2048
    * Virtual Disk Image: <servicename>.001.qcow
    * Default Profile:  <ServiceName> (Make sure that the profile name match the VM name and match the Service name so the auto-provisioner works)

And your DONE!

**Note:** If you assign this VM to any existing physical nodes profiles they will automatically download your new disk and launch it as specificed in the profile.