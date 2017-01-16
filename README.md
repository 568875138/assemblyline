# Assemblyline

Assemblyline is a scalable *__distributed file analysis framework__*. It is designed to process millions of files per day but can also be installed on a single box.

An Assemblyline cluster consist of 3 types of boxes: Core, Datastore and Worker.

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

### Get Started

#### Pre-Requisite

* [Install Ubuntu Server](docs/install_ubuntu_server.md)

#### Development

* [Install a self contained VM Appliance](docs/install_vm_appliance.md)
* [Create service tutorial](docs/create_new_service.md)

#### License (or lack thereof) and Conditions of use

As is fairly evident, we haven't selected a license for this project as of yet. As discussed when members were first granted read access to the repository, dissemination is based on the premise of originator controlled. If you feel there are other partners that would benefit from an early view and would be able to contribute, please contact the project leads and we should be able to sort it out.

We will soon be splitting the platform and services into two separate repo's, so please treat the services as slightly more sensitive than the platform itself, ie: release it and perish!!! ... but seriously, we do not grant anyone the right to do anything other than deploy the platform and use it. No sharing, presenting, etc without our knowledge. 

We hope to have a clear release plan soon.


