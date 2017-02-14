# Creating an Assemblyline service

This document will serve as a guide to developers looking to create services for Assemblyline. It is aimed at people who have development knowledge and basic Python skills, but who know little about the Assemblyline framework.

## Setting up a Development Environment

### Virtual machine appliance

You can set yourself a Virtual Machine Appliance by following those two guides:

1. [Install Ubuntu Server](install_ubuntu_server.md)
    * __Note:__ You may want to use Ubuntu desktop instead of server if you want to develop with a GUI.
2. [Install Development VM](install_developement_vm.md)

## Service Guidelines

### What is a service

Services are pieces of code that take a file or metadata about a file at input, analyse said file or metadata to achieve the following results:

* Produce a human readable analysis of the data
* Extract embedded pieces of data for further analysis
* Tag distinctive features of the data
* Set a level of confidence if the data is good or bad

### Type of service

These are the different type of services that we have so far in the system and most likely, your service will fit into one of those categories.

**NOTE**: Some service will be hybrid services meaning that they will leverage two type of services.

#### Assemblyline only services

This is a service that was 100% designed for file analysis in the context of Assemblyline. This is a Python only service that has the following properties:

* It did not exist prior to Assemblyline.
* It does not just wrap any prior existing library.

**Example**: Metapeek

#### Python wrappers

This is a service that essentially wrap a pre-existing Python library and parses its output to create Assemblyline results.

**Example**: PEFile, PeePDF, PDFiD...

#### Command line wrappers

This is a service that will execute a command line tool and wait for its output. The service will then parse said output to produce and Assemblyline result.

**Example**: Avg, Mcafee, Suricata, Unpacker ...

#### API wrappers

This is a service that will callout to an external service for processing and wait for the results.

You'll want to avoid this type of service as often as possible because these service are harder to setup and harder to scale. Spinning up new instances of a API wrapper service might not necessarily increase throughput but might actually reduce it depending if the targeted server is overloaded.

That said, in some case this makes a lot of sense and is the right way to go.

**Example**: FSecure, KasperskyIcap, Metadefender, NSRL, VirusTotal...

### What should I consider before creating a service

1. Think big: You'll want your service to process as fast as possible because it will have to process millions of files per day.
2. Small footprint: Reduce CPU/Memory consumption as much as you can so we don't waste important resources in the cluster
3. Easy installer: The service should have an installer that does it all.
3.1 Installation documentation: In the case of the API wrapper services, installation documentation of the external component is required
4. If needed, think about your updating strategy. (e.g: AV signatures updates, Yara rules updates...)

### Example of failures

This is a few examples of what not to do when creating a service because it cause to much strain on the system or makes it too complex

#### Asking to much of the workers

The NSRL service was originally supposed to install the NSRL hashset on each of the worker instead of having one central NSRL DB that the service query into.

This caused the following problems

1. You have to install postgresql server on each worker which takes a lot of resources away from actual processing of files
2. Pushing updates to NSRL meant few hours of extra resources usage on each worker reducing throughput
3. Each instances of postgresql on the worker was using a lot of RAM but was actually idle in terms of CPU usage.

We fixed it by having only one support server that hosted the DB (and other services dependancies). Now the service is very light weight because all it does is a SQL query to an external database. Also the database server can easily handle thousands of instances of this service connected at the same time.

#### Queue to a queue

The Suricata service is a good example of originally over-designing a service. The person came to the DEV team asking for a spare server to run a Suricata processing farm they build using celery. They then wanted to create a service that interface with their celery queue.

The Dev team response to this was the Assemblyline is already a queuing system and that doing it this way would make it really hard to scale.

We went back to the drawing board and created a Suricata service as a **command line wrapper** service instead of the **API wrapper** original design. This is now a lot easier to manage and to scale.

### Before getting started

Talk to CSE's Assemblyline team before getting started. They may already be working on the same service or know someone that does. The DEV team can help you out planning the design of your service depending of its complexity.

## Your First Service

### Tutorial Service
This section will walk you through the bare minimum needed to create a running (if functionally useless) service.

* Under the `/opt/al/pkg/al_services/` directory, create a directory named "alsvc_tutorial".
* Create the file `__init__.py` in this directory with the following contents:

    from al_services.alsvc_tutorial.service_tutorial import ServiceTutorial

Create the file `service_tutorial.py` in that same directory with the following contents:

    from assemblyline.al.service.base import ServiceBase
    from assemblyline.al.common.result import Result, ResultSection, SCORE

    class ServiceTutorial(ServiceBase):
        SERVICE_CATEGORY = 'Static Analysis'
        SERVICE_ACCEPTS = '.*'
        SERVICE_REVISION = ServiceBase.parse_revision('$Id$')
        SERVICE_VERSION = '1'
        SERVICE_ENABLED = True
        SERVICE_STAGE = 'CORE'
        SERVICE_CPU_CORES = 1
        SERVICE_RAM_MB = 256

        def __init__(self, cfg=None):
            super(Example, self).__init__(cfg)

        def start(self):
            self.log.debug("Tutorial service started")

        def execute(self, request):
            result = Result()
            section = ResultSection(SCORE.NULL, "Tutorial service completed")
            section.add_line("Nothing done.")
            result.add_section(section)
            request.result = result

Run this command to register your service with assemblyline (you only need to do this once):

    /opt/al/pkg/assemblyline/al/service/register_service.py al_services.alsvc_tutorial.ServiceTutorial

You will see a confirmation message if the registration succeeded.

    INFO:root:Storing al_services.alsvc_tutorial.ServiceTutorial
    INFO:assemblyline.al.datastore:riakclient opened...

*__NOTE:__ If you do not, the `service_tutorial.py` service may have a bug in it; isolate the bug and fix it.*

You can now run your service with the following command:

    /opt/al/pkg/assemblyline/al/service/run_service_live.py al_services.alsvc_tutorial.ServiceTutorial

You should see startup and heartbeat messages. If the service doesn't start, then once again, run `service_tutorial.py` through pylint to ensure it has no syntax errors that would prevent it from running.

Submit a file to the local assemblyline instance using your Chromium/Firefox window, and enable only this service. It should have the result added by the example above.


#### Breaking it Down

Any service will have these three components at a bare minimum:

##### Configuration

    class ServiceTutorial(ServiceBase):
        SERVICE_CATEGORY = 'Static Analysis'
        SERVICE_ACCEPTS = '.*'
        SERVICE_REVISION = ServiceBase.parse_revision('$Id$')
        SERVICE_VERSION = '1'
        SERVICE_ENABLED = True
        SERVICE_STAGE = 'CORE'
        SERVICE_CPU_CORES = 1
        SERVICE_RAM_MB = 256

Most of this should be self-explanatory. The `SERVICE_ACCEPTS` item specifies a regex of MIME types that your service supports. This service accepts everything. Other examples include `java/jar` or `executable/.*` .

##### Constructor

    def __init__(self, cfg=None):
        super(Example, self).__init__(cfg)

This example simply calls the parent constructor. Use this to set up any default configuration that cannot be statically coded. Don't use this for initialization, instead use...start()

    def start(self):
        self.log.debug("Example service started")

This function is called when the service is being prepared to accept requests and process them. Use this to perform any initialization that your service needs.

##### Execute function

    def execute(self, request):
        result = Result()
        section = ResultSection(SCORE.NULL, "Example service completed")
        section.add_line("Nothing done.")
        result.add_section(section)
        request.result = result

This function is called when a file is being passed to your service. The request object has methods for getting information about the submitted file and for accessing it. For this example, we use it simply to report results.


### Results

For a service to be useful, it must report the results of its analysis. As the above code demonstrates, a Result has one or more ResultSection objects, each of which can have multiple lines.

A ResultSection has a score. The sum of all scores on a submitted file determines its likelihood of being malicious; higher scores mean it's more likely bad. A total score of over 500 will raise an alert for this file.

A score of 0 or `SCORE.NULL` is for informational messages. You should keep those to a minimum, so that important messages do not get lost in the noise, but it makes a good example in this case. A score of `SCORE.OK` is for indicators that the file is probably safe, and a score of `SCORE.NOT` is for files you're certain are not malicious. Other score values, in order of increasing suspicion, are `INFO`, `LOW`, `MED`, `HIGH`, `VHIGH`, and `SURE` (which has a score value of 1000 by itself).


### Tags

Another way to make your service useful is to provide tags in your Result object. Tags are key-value pairs which can be used within assemblyline to correlate files. Tags have scores (called weights), types (this is the tag key), an optional usage (e.g. `TAG_USAGE.IDENTIFICATION` or `TAG_USAGE.CORRELATION`), and a classification.


To tag a result, your service should import `TAG_TYPE`, `TAG_WEIGHT` and `TAG_USAGE` from `assemblyline.al.common.result`, and use code such as this:

    def execute(self, request):
        result = Result()
        ...
        result.add_tag(TAG_TYPE.NET_PROTOCOL, "tcp", TAG_WEIGHT.NULL, usage=TAG_USAGE.IDENTIFICATION)


The full list of supported tag types is given in `STANDARD_TAG_TYPES` in `assemblyline/common/constants.py`. You will notice that each literal tag name has a constant integer associated with it. You don't normally need to care about this number, but if you need to add a tag to either of these files, make sure that you give it a unique number as well as a unique name.


### Making it Useful

No service can be of much use unless it operates on the file submitted. You can get the file contents in one of two ways:

    def execute(self, request):
        file_path = request.download()    # Get a local copy of the file
        file_contents = request.get()      # Get contents of the file as a string

### Other Important Functions

In special circumstances, you will need do define additional methods in your service, with special names.

#### import_service_deps()

If your service depends on python modules which are not standard library modules, you should not import them directly at the top of your python file. This is because your service will be imported even when it's not going to be used, for example, on a different architecture. Instead, create the `import_service_deps()` method, with content similar to the following:

    def import_service_deps(self):
        global yara, requests
        import yara
        import requests


#### get_tool_version()

Assemblyline caches the scan results of a file, along with the version of the service that was used to produce those results. If your service depends on an external tool, you can provide this function to return the version of the tool used, and this will allow a file to be re-scanned by a newer version of the tool later, even if the service version stays the same.

The canonical paradigm for defining this function is as follows:

    class ServiceTutorial(ServiceBase):
        def __init__(self, cfg=None):
            super(Example, self).__init__(cfg)
            self._mytool_version = 'unknown'

         def start(self):
             # Get the version of mytool here
             # (from a config file or the result of running "mytool --version")
             # and put the result in self._mytool_version

         def get_tool_version(self):
             return self._mytool_version

### Further Development

As you make changes to your service, you should be able to see them right away by killing and restarting the run_service_live process. You will need to enable the Assemblyline option to bypass the scan cache if you resubmit the same test file repeatedly. (You can set this in your default settings for convenience.) Remember to not use this option in production Assemblyline without a good reason!

## Advanced Topics
### Service Configuration

Most services have configurable settings that can be modified by the assemblyline admins. To add such settings to your service, provide them in the class variable list:

    class ServiceTutorial(ServiceBase):
        ...
        SERVICE_DEFAULT_CONFIG = {
            'IS_BOOLEAN': True,
            'TOOL_PATH': '/opt/al/support/service_tutorial/',
        }

Then, to use these settings elsewhere in your service, use the method `self.cfg.get()`, for example `self.cfg.get('TOOL_PATH')`. You should test the validity of your settings in your service's `start()` method before relying on them in your service's `execute()` method.

### Installation Scripts

Before your service is deployed, assemblyline checks for an installation script in your service directory. If your script needs any special package dependancies before it can run, you can put its configuration here.

In your service directory create and installer.py and use the SiteInstaller class to configure your service

    #!/usr/bin/env python


    def install(alsi):
        alsi.sudo_apt_install('libpq-dev')
        alsi.pip_install('psycopg2')

    if __name__ == '__main__':
        from assemblyline.al.install import SiteInstaller
        install(SiteInstaller())


### Working with Nested ResultSections

When dealing with large sets of results you might find yourself wanting to group these results together in a hierarchical manner. To do this you can easily create and nest multiple ResultSections by simply calling `add_section()` on each "parent" section. Any scores assigned to each individual section will be displayed on the results page, and the sum of all nested ResultSection scores will also be displayed at the top-level.

__Note:__ However this summation only occurs after the `execute()` block of your service has completed. Therefore if you want to say, sort or filter, nested sections off their cumulative score you will have to calculate that manually. This situation is ripe for recursion, and here's an example of that:

    def execute():
      ...

      grandparent = ResultSection(score=0, "Grandparent")
      parent1 = ResultSection(score=5, "Parent 1")
      parent2 = ResultSection(score=5, "Parent 2")
      child1 = ResultSection(score=20, "Child 1")
      child2 = ResultSection(score=10, "Child 2")

      parent1.add_section(child1)
      parent2.add_section(child2)

      grandparent.add_section(parent1)
      grandparent.add_section(parent2)

      print grandparent.score  # would print 0
      print parent1.score  # would print 5

      print parent2.score  # would print 5

      print self.calculate_nested_scores(grandparent)  # would print 40

      print self.calculate_nested_scores(parent1)  # would print 25
      print self.calculate_nested_scores(parent2)  # would print 15


    def calculate_nested_scores(self, section):
        score = section.score
        if len(section.subsections) > 0:
            for subsection in sect.subsections:
                score = score + self.calculate_nested_scores(subsection)
        return score

### Self-updating services

If your service can automatically update itself you can register and update callback which will be called at an intervale that you choose.

    from assemblyline.al.service.base import ServiceBase, UpdaterType, UpdaterFrequency

    class ServiceTutorial(ServiceBase):
    ....
        def start(self):
            self._register_update_callback(self.update_callback, utype=UpdaterType.BOX, freq=UpdaterFrequency.QUARTER_DAY)

        def update_callback(self, **kwargs):
            # you update code goes here
            pass

The `_register_update_callback` function can take the following extra parameters:

* `blocking`: Should we stop service execution while updating [default: False]
* `execute_now`: Should we execute the updater while we register the callback [default: True]
* `utype`: Type of updating strategy (BOX: updates the whole box, CLUSTER: updates the full cluster, PROCESS: updates only this process) [default: PROCESS]
* `freq`: At which frequency you want to update [default: HOURLY]

### Execution gone wild

There are many things that can go wrong by executing an external program/library and making sure that your assemblyline service stays up and still continue processing normally without eating up all the resources. We have some protection classes and functions to help with this.

#### Subprocess Reaper

Imagine this, you call a subprocess command which in turn calls another command but that second command hangs. Assemblyline service will auto-kill a service that reaches the timeout value but the second command will stay hung forever because the kill command does not follow through childrens.

Thankfully, Linux supports propagating kill signals to the childrens so we've added a special function to kill rogue children processes. Simply add `, preexec_fn=set_death_signal()` to your subprocess calls.

    from assemblyline.common.reaper import set_death_signal

    proc = Subprocess.Popen(["my_shell_command"], stdout=PIPE, stderr=PIPE, preexec_fn=set_death_signal())

#### Limit execution time

Your assemblyline service may need to process millions of files daily so if your calling functions or subprocess that can go rogue and take ages to run, you may to wrap those up into a timer.

Assemblyline provides two types of timers, one for direct python function and one especially made for Subprocess.

##### Python timer

Lets say you want to wrap `my_function` inside a 2 seconds timer you can do the following:

    from assemblyline.common.timeout import timeout

    def my_function(sleep_time):
        time.sleep(sleep_time)
        return "Done sleeping"

    try:
        output = timeout(my_function, (5,), timeout_duration=1)
    except TimeoutException:
        print "Timeout reached"

##### Subprocess timer

If you want to wrap call to a subprocessed function, you should use the SubprocessTimer class instead because that class will take care of killing the process if timer is reached.

    from assemblyline.common.timeout import SubprocessTimer

    try:
        with SubprocessTimer(2) as timer:
            proc = timer.run(subprocess.Popen(["sleep", "4"], stderr=subprocess.PIPE, stdout=subprocess.PIPE))
            std_out, std_err = proc.communicate()

        print "Execution complete!"
    except TimeoutException:
        print "Process timeout!"

***Note***: SubprocessTimer can be combined to Subprocess reaper for maximum execution security.