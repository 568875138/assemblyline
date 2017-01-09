#!/usr/bin/env python
from __future__ import print_function

import subprocess
from getters import *


DEPENDS = ["convert", "figlet"]
DEVEL_VM = "Development VM"
APPLIANCE = "Appliance (Full deployment on single machine)"
CLUSTER = "Cluster (High volume production deployment)"
DEPLOYMENT_TYPES = [DEVEL_VM, APPLIANCE, CLUSTER]

FONT = "DejaVu-Sans-Mono-Bold"

FIGLET_CMD = 'figlet {text} | grep -v "^\s*$"'
FAV_ICON_CMD = 'convert -gravity Center -size 256x256 -font "{font}" ' \
               '-pointsize 30 -background transparent -fill black label:\'{{text}}\' {{target}}'.format(font=FONT)
BANNER_CMD = 'convert -font "{font}" -pointsize 36 -background ' \
             'transparent -fill black label:\'{{text}}\' {{target}}'.format(font=FONT)

current_dir = os.path.dirname(os.path.realpath(__file__))


def banner(msg):
    stdout, _ = subprocess.Popen(["figlet", msg], stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    print(stdout)


def check_libs():
    with open(os.devnull, "w") as devnull:
        for dep in DEPENDS:
            val = subprocess.call(["which"] + [dep], stdout=devnull)
            if val != 0:
                return False

    return True


def get_figlet(text):
    fig_proc = subprocess.Popen(FIGLET_CMD.format(text=text), shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    std_out, _ = fig_proc.communicate()
    std_out = std_out.replace("\\", "\\\\")
    std_out = std_out.replace("\n", "\\n")
    std_out = std_out.replace(" ", "\\ ")
    std_out = std_out.replace("'", "'\"'\"'")  # Fun with shells...

    return std_out


def create_images(app_name, banner_file, fav_icon_file):
    print("\t* Creating images for app %s" % app_name)

    exit_code = subprocess.call(FAV_ICON_CMD.format(text=get_figlet(app_name[0]), target=fav_icon_file), shell=True,
                                stderr=subprocess.PIPE)
    if exit_code != 0:
        print("ERR: Cannot create favicon for your deployment, "
              "verify that your imagemagick policy let you read labels.")
        exit(exit_code)

    exit_code = subprocess.call(BANNER_CMD.format(text=get_figlet(app_name), target=banner_file), shell=True,
                                stderr=subprocess.PIPE)
    if exit_code != 0:
        print("ERR: Cannot create banner image for your deployment, "
              "verify that your imagemagick policy let you read labels.")
        exit(exit_code)


def copy_skel(destination):
    print("\t* Copying skeleton to %s" % destination)

    shutil.copytree(os.path.join(current_dir, "skel"), destination)


def save_install_template(template_name, values, target):
    print("\t* Creating installation doc")

    install_template = open(os.path.join(current_dir, "templates", template_name)).read()
    install_template = install_template.format(**values)

    with open(target, 'wb') as seed_file:
        seed_file.write(install_template)


def save_seed_template(template_name, values, target):
    print("\t* Creating seed from template")

    seed_template = open(os.path.join(current_dir, "templates", template_name)).read()
    seed_template = seed_template.format(**values)

    with open(target, 'wb') as seed_file:
        seed_file.write(seed_template)


def save_site_spec_template(template_name, values, target):
    print("\t* Creating site_pecific from template")

    site_spec_template = open(os.path.join(current_dir, "templates", template_name)).read()
    site_spec_template = site_spec_template.format(**values)

    with open(target, 'wb') as site_spec_file:
        site_spec_file.write(site_spec_template)


def report_completion(dep_type, working_dir):
    print("{type} deployment skeleton has been created into {working_dir}.".format(type=dep_type,
                                                                                   working_dir=working_dir))
    if working_dir != "/opt/al/pkg/al_private":
        print("\nNOTE: You should commit the content of your {working_dir} to your personal or corporate "
              "GitHub account as al_private because you will need it during the deployment installation "
              "procedure. Your private deployment contains user and password and may even contain ssl certs. "
              "You should make your repo only accessible by yourself.\n".format(working_dir=working_dir))
        print("You can now follow the step by step instructions in "
              "{working_dir}/doc/deployment_installation.md.".format(working_dir=working_dir))


def appliance():
    # Questions
    banner("Appliance")
    print("\nLet's get started creating you an 'Appliance' deployment.\n\n")
    destination = get_string("Where would you like us to create your deployment? (the directory needs to "
                             "exist and need to be writeable by your current user)", validator=path_exits_validator,
                             default="/tmp")
    app_name = get_string("What will be the name of your deployment?", default="Appliance")
    organisation = get_string("What is your organisation acronym?")
    fqdn = get_string("What is the fully qualified domain name for your appliance?", default="assemblyline.local")
    ram = get_int("What amount of ram in GB does your box have?")
    solr_heap = min(int(ram / 3), 31)
    password = get_password("What password would you like for your admin user?", default="changeme")
    install_kvm = get_bool("Is this appliance a bare metal box?")

    ftp_pass = get_random_password(length=32)
    internal_pass = get_random_password(length=32)
    secret_key = get_random_password(length=128)

    # Apply answers
    working_dir = os.path.join(destination, "al_private")

    banner_file = os.path.join(working_dir, "ui", "static", "images", "banner.png")
    fav_icon_file = os.path.join(working_dir, "ui", "static", "images", "favicon.ico")

    target_install_doc = os.path.join(working_dir, "doc", "deployment_installation.md")
    target_seed = os.path.join(working_dir, "seeds", "deployment.py")
    target_site_spec = os.path.join(working_dir, "ui", "site_specific.py")

    if os.path.exists(working_dir):
        if get_bool("%s already exists. Do you want to override it? " % working_dir):
            shutil.rmtree(working_dir)
        else:
            print("Cancelling install...")
            exit(1)

    copy_skel(working_dir)
    save_install_template("install_appliance.tmpl", {'app_name': app_name}, target_install_doc)
    save_seed_template("appliance.tmpl", {
        'organisation': organisation,
        'fqdn': fqdn,
        'install_kvm': install_kvm,
        'password': password,
        "secret_key": secret_key,
        "ftp_pass": ftp_pass,
        "internal_pass": internal_pass,
        "solr_heap": solr_heap}, target_seed)
    save_site_spec_template("site_specific.tmpl", {'app_name': app_name}, target_site_spec)
    create_images(app_name, banner_file, fav_icon_file)

    report_completion("Appliance", working_dir)


def cluster():
    # Questions
    banner("Cluster")
    print("\nLet's get started creating your 'Cluster' deployment.\n\n")
    destination = get_string("Where would you like us to create your deployment? (the directory needs to "
                             "exist and need to be writeable by your current user)", validator=path_exits_validator,
                             default="/tmp")
    app_name = get_string("What will be the name of your deployment?")
    organisation = get_string("What is your organisation acronym?")
    if get_bool("Is this a production cluster?"):
        sys_name = 'production'
        repo_branch = 'production'
    else:
        sys_name = 'staging'
        repo_branch = 'master'
    password = get_password("What password would you like for your admin user?", default="@dminpAssw0rd!")

    fqdn = get_string("What is the fully qualified domain name for your core server?", default="assemblyline.local")
    ip_core = get_string("What will be your core server IP?", validator=ip_validator)
    ips_riak = get_string_list("What will be the IPs of the riak nodes? (Comma separated)",
                               validator=ip_list_validator)
    riak_ram = get_int("What amount of ram in GB does your riak boxes have?")
    solr_heap = min(int(riak_ram / 3), 31)

    ips_worker = get_string_list("What will be the IPs of the worker nodes? (Comma separated)",
                                 validator=ip_list_validator)
    install_kvm = get_bool("Will the worker be installed on baremetal boxes?")

    if get_bool("Will you have a log server for you cluster? (Recommended)"):
        ip_logger = get_string("What will be your log server IP?", validator=ip_validator)
        log_ram = get_int("What amount of ram in GB does your log server box have?")
        log_to_syslog = True
    else:
        ip_logger = None
        log_ram = 4
        log_to_syslog = False
    elastic_heap = min(int(log_ram / 3), 31)

    ftp_pass = get_random_password(length=32)
    internal_pass = get_random_password(length=32)
    logger_pass = get_random_password(length=32)
    secret_key = get_random_password(length=128)

    # Apply answers
    working_dir = os.path.join(destination, "al_private")

    banner_file = os.path.join(working_dir, "ui", "static", "images", "banner.png")
    fav_icon_file = os.path.join(working_dir, "ui", "static", "images", "favicon.ico")

    target_install_doc = os.path.join(working_dir, "doc", "deployment_installation.md")
    target_seed = os.path.join(working_dir, "seeds", "deployment.py")
    target_site_spec = os.path.join(working_dir, "ui", "site_specific.py")

    if os.path.exists(working_dir):
        if get_bool("%s already exists. Do you want to override it? " % working_dir):
            shutil.rmtree(working_dir)
        else:
            print("Cancelling install...")
            exit(1)

    copy_skel(working_dir)
    save_install_template("install_cluster.tmpl", {
        'app_name': app_name,
        'ip_core': ip_core
    }, target_install_doc)
    save_seed_template("cluster.tmpl", {
        'organisation': organisation,
        'fqdn': fqdn,
        'install_kvm': install_kvm,
        'logger_pass': logger_pass,
        'elastic_heap': elastic_heap,
        'log_to_syslog': log_to_syslog,
        'ip_logger': ip_logger,
        'ips_worker': ips_worker,
        'ips_riak': ips_riak,
        'ip_core': ip_core,
        'repo_branch': repo_branch,
        'sys_name': sys_name,
        'password': password,
        "secret_key": secret_key,
        "ftp_pass": ftp_pass,
        "internal_pass": internal_pass,
        "solr_heap": solr_heap
    }, target_seed)
    save_site_spec_template("site_specific.tmpl", {'app_name': app_name}, target_site_spec)
    create_images(app_name, banner_file, fav_icon_file)

    report_completion("Cluster", working_dir)


def devel_vm():
    # Questions
    banner("Devel VM")
    print("\nLet's get started creating you a 'Development VM' deployment.\n\n")
    destination = get_string("Where would you like us to create your deployment? (the directory needs to "
                             "exist and need to be writeable by your current user)", validator=path_exits_validator,
                             default="/tmp")
    app_name = get_string("What will be the name of your deployment?", default="Dev VM")
    password = get_password("What password would you like for all components in your VM?", default="changeme")
    secret_key = get_random_password(length=128)
    print("The password you've picked will be used for login into the web UI (user=user), "
          "for FTP file transfers (user=ssftp) and to ssh in for remote debugging (user=al).")

    # Apply answers
    working_dir = os.path.join(destination, "al_private")

    banner_file = os.path.join(working_dir, "ui", "static", "images", "banner.png")
    fav_icon_file = os.path.join(working_dir, "ui", "static", "images", "favicon.ico")

    target_install_doc = os.path.join(working_dir, "doc", "deployment_installation.md")
    target_seed = os.path.join(working_dir, "seeds", "deployment.py")
    target_site_spec = os.path.join(working_dir, "ui", "site_specific.py")

    if os.path.exists(working_dir):
        if get_bool("%s already exists. Do you want to override it? " % working_dir):
            shutil.rmtree(working_dir)
        else:
            print("Cancelling install...")
            exit(1)

    copy_skel(working_dir)
    save_install_template("install_devel_vm.tmpl", {'app_name': app_name}, target_install_doc)
    save_seed_template("devel_vm.tmpl", {
        'password': password,
        "secret_key": secret_key
    }, target_seed)
    save_site_spec_template("site_specific.tmpl", {'app_name': app_name}, target_site_spec)
    create_images(app_name, banner_file, fav_icon_file)

    report_completion("Development VM", working_dir)


def start():
    banner("assemblyline")
    print("Welcome to assemblyline deployment creator.\n\nWe will ask you a few question about the type of deployment "
          "you are trying to do and will automatically create you a deployment specific to you needs with all the "
          "required blocks to build on top of.\n\nPrior to run this tool, you should probably read the assemblyline "
          "reference manual so you have an idea of what are the requirements for the different deployment types.\n\n"
          "This tool will ask you specific questions about your deployment which may include: IPs that each machines "
          "will have on the network, amount of ram on each sepcific boxes, etc.")

    if get_bool("Are you ready to proceed?"):
        function = pick_from_list("Which deployment type would you like?", DEPLOYMENT_TYPES)
        DEPLOYMENT_MAP[function]()
    else:
        exit(1)


DEPLOYMENT_MAP = {
    DEVEL_VM: devel_vm,
    APPLIANCE: appliance,
    CLUSTER: cluster
}


if __name__ == "__main__":
    if check_libs():
        start()
    else:
        print("[ERROR]\nAssemblyline deployement creator requires you to "
              "have the following commands installed: \n%s" % ", ".join(DEPENDS))
