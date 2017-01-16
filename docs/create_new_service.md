# Creating an Assemblyline service

This document will serve as a guide to developers looking to create services for Assemblyline. It is aimed at people who have development knowledge and basic Python skills, but who know little about the Assemblyline framework.

## Setting up a Development Environment

### Virtual machine appliance

You can set yourself a Virtual Machine Appliance by following those two guides:

1. [Install Ubuntu Server](install_ubuntu_server.md)
    * __Note:__ You may want to use Ubuntu desktop instead of server if you want to develop with a GUI.
2. [Appliance VM Installation](install_vm_appliance.md)

## Your First Service

### Tutorial Service
This section will walk you through the bare minimum needed to create a running (if functionally useless) service.

* Under the `/opt/al/pkg/assemblyline/al/service` directory, create a directory named "service_tutorial".
* Create the file `__init__.py` in this directory with the following contents:

    from assemblyline.al.service.service_tutorial.service_tutorial import ServiceTutorial

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

    /opt/al/pkg/assemblyline/al/service/register_service.py assemblyline.al.service.service_tutorial.service_tutorial.ServiceTutorial

You will see a confirmation message if the registration succeeded.

    INFO:root:Storing assemblyline.al.service.service_tutorial.service_tutorial.ServiceTutorial
    INFO:assemblyline.al.datastore:riakclient opened...

*__NOTE:__ If you do not, the `service_tutorial.py` service may have a bug in it; use pylint to isolate the bug and fix it.*

You can now run your service with the following command:

    /opt/al/pkg/assemblyline/al/service/run_service_live.py assemblyline.al.service.service_tutorial.service_tutorial.ServiceTutorial

You should see startup and heartbeat messages. If the service doesn't start, then once again, run `service_tutorial.py` through pylint to ensure it has no syntax errors that would prevent it from running.

Submit a file to the local assemblyline instance using your Chromium window, and enable only this service. It should have the result added by the example above.


#### Breaking it Down

Any service will have these three components at a bare minimum:

##### Configuration

    class Example(ServiceBase):
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

    class Example(ServiceBase):
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

    class Example(ServiceBase):
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
        alsi = SiteInstaller()
        install(alsi)


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
