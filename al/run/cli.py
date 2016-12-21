#!/usr/bin/env python

import cmd
import sys
import multiprocessing
import os
import signal
import time

from pprint import pprint, pformat

from assemblyline.common.importing import module_attribute_by_name
from assemblyline.common.net import get_mac_address
from assemblyline.al.common import forge, log as al_log
from assemblyline.al.common.backupmanager import SystemBackup, DistributedBackup
from assemblyline.al.common.message import send_rpc
from assemblyline.al.common.queue import reply_queue_name, NamedQueue
from assemblyline.al.common.task import Task
from assemblyline.al.core.agents import AgentRequest, ServiceAgentClient, VmmAgentClient
from assemblyline.al.core.controller import ControllerClient
from assemblyline.al.core.dispatch import DispatchClient
from assemblyline.al.service import register_service

config = forge.get_config()
config.logging.log_to_console = False
al_log.init_logging('cli')

RESET_COLOUR = '\033[0m'
YELLOW_COLOUR = '\033[93m'
PROCESSES_COUNT = 50
COUNT_INCREMENT = 500
DATASTORE = None
t_count = 0
t_last = time.time()

YaraParser = forge.get_yara_parser()


def init():
    global DATASTORE
    DATASTORE = forge.get_datastore()
    signal.signal(signal.SIGINT, signal.SIG_IGN)


# noinspection PyProtectedMember
def bucket_delete(bucket_name, key):
    try:
        DATASTORE._delete_bucket_item(DATASTORE.get_bucket(bucket_name), key)
    except Exception, e:
        print e
        return "DELETE", bucket_name, key, False

    return "deleted", bucket_name, key, True


# noinspection PyProtectedMember
def update_signature_status(status, key):
    try:
        data = DATASTORE._get_bucket_item(DATASTORE.get_bucket('signature'), key)
        data['meta']['al_status'] = status
        data = DATASTORE.sanitize('signature', data, key)
        DATASTORE._save_bucket_item(DATASTORE.get_bucket('signature'), key, data)
    except Exception, e:
        print e


def submission_delete_tree(key):
    try:
        with forge.get_filestore() as f_transport:
            DATASTORE.delete_submission_tree(key, transport=f_transport)
    except Exception, e:
        print e
        return "DELETE", "submission", key, False

    return "deleted", "submission", key, True


def action_done(args):
    global t_count, t_last, COUNT_INCREMENT
    action, bucket, key, success = args
    if success:
        t_count += 1
        if t_count % COUNT_INCREMENT == 0:
            new_t = time.time()
            print "[%s] %s %s so far (%s at %s keys/sec)" % \
                  (bucket, t_count, action, new_t - t_last, int(COUNT_INCREMENT / (new_t - t_last)))
            t_last = new_t
    else:
        print "!!ERROR!! [%s] %s ==> %s" % (bucket, action, key)


def _reindex_template(bucket_name, keys_function, get_function, save_function, bucket=None, filter_out=None):
        if not filter_out:
            filter_out = []

        print "\n%s:" % bucket_name.upper()
        print "\t[x] Listing keys..."
        keys = keys_function()

        print "\t[-] Re-indexing..."
        for key in keys:
            skip = False
            for f in filter_out:
                if f in key:
                    skip = True
            if skip:
                continue
            if bucket:
                value = get_function(bucket, key)
                save_function(bucket, key, value)
            else:
                value = get_function(key)
                save_function(key, value)

        print "\t[x] Indexed!"


# noinspection PyMethodMayBeStatic,PyProtectedMember,PyBroadException
class ALCommandLineInterface(cmd.Cmd):  # pylint:disable=R0904

    intro = 'AL 3.1 - Console. (type help).'

    def __init__(self):
        cmd.Cmd.__init__(self)
        self.local_mac = get_mac_address()
        self.mac = self.local_mac  # the mac we are currently targetting.
        self.queue = None
        self.prompt = None
        self.datastore = forge.get_datastore()
        self.controller_client = ControllerClient(async=False)
        self.vmm_client = VmmAgentClient(async=False)
        self.svc_client = ServiceAgentClient(async=False)
        self.config = forge.get_config()
        self._update_context()

    def _update_context(self):
        label = 'local' if self.mac == self.local_mac else 'remote'
        self.prompt = '%s (%s)> ' % (self.mac, label)
        self.queue = NamedQueue(self.mac)

    def _send_agent_cmd(self, command, args=None):
        self.queue.push(AgentRequest(self.mac, command, body=args))

    def _send_agent_rpc(self, command, args=None):
        return send_rpc(AgentRequest(self.mac, command, body=args))

    #
    # Seed actions
    #
    def do_reseed(self, args):
        """
        This script takes a seed path as parameter and save the seed into
        the target key in the blob bucket.
        """
        try:
            seed_path, target = args.split(" ")
        except:
            print "reseed <seed_path> <target_blob>"
            return

        seed = module_attribute_by_name(seed_path)
        services_to_register = seed['services']['master_list']

        for service, service_detail in services_to_register.iteritems():
            classpath = service_detail['classpath']
            config_overrides = service_detail.get('config', {})

            new_srv_registration = register_service.register(classpath, config_overrides=config_overrides,
                                                             store_config=False,
                                                             enabled=service_detail.get('enabled', True))
            seed['services']['master_list'][service].update(new_srv_registration)

        if target == "seed":
            cur_seed = self.datastore.get_blob('seed')
            self.datastore.save_blob('previous_seed', cur_seed)
            print "Current seed was copied to previous_seed key."

        self.datastore.save_blob(target, seed)
        print "Module '%s' was loaded into blob '%s'." % (seed_path, target)

    def do_reseed_current(self, _):
        """
        This script takes the current seed_module and reloads it into the seed key
        """
        module = self.datastore.get_blob('seed_module')
        self.do_reseed("%s seed" % module)

    def do_restore_previous_seed(self, _):
        """
        This script swaps 'seed' and 'previous_seed' to restore the previous seed
        """
        cur_seed = self.datastore.get_blob('seed')
        self.datastore.save_blob('seed', self.datastore.get_blob('previous_seed'))
        self.datastore.save_blob('previous_seed', cur_seed)
        print "Previous seed and current seed were swapped."

    #
    # Delete actions
    #
    def do_delete_full_submission_by_query(self, args):
        pool = multiprocessing.Pool(processes=PROCESSES_COUNT, initializer=init)
        if args:
            query = args
        else:
            query = raw_input("Query to run: ")

        try:
            prompt = True
            cont = True
            print "\nNumber of items matching this query: %s\n\n" % \
                  self.datastore._search_bucket(self.datastore.submissions, query, start=0, rows=0)["total"]

            for data in self.datastore.stream_search("submission", query, item_buffer_size=COUNT_INCREMENT):
                if prompt:
                    print "This is an exemple of the data that will be deleted:\n"
                    print data, "\n"
                    cont = raw_input("Are your sure you want to continue? (y/N) ")
                    cont = cont == "y"
                    prompt = False

                if not cont:
                    print "\n**ABORTED**\n"
                    break

                pool.apply_async(submission_delete_tree, (data["_yz_rk"], ), callback=action_done)
        except KeyboardInterrupt, e:
            print "Interrupting jobs..."
            pool.terminate()
            pool.join()
            raise e
        except Exception, e:
            print "Something when wrong, retry!\n\n %s\n" % e
        else:
            pool.close()
            pool.join()
            if prompt:
                print "\nNothing matches that query...\n"
            else:
                self.datastore.commit_index('submission')

    def do_delete_by_query(self, args):
        pool = multiprocessing.Pool(processes=PROCESSES_COUNT, initializer=init)
        try:
            bucket_name, query = args.split(" ", 1)
        except:
            bucket_name = raw_input("Which bucket?: ")
            query = raw_input("Query to run: ")

        try:
            prompt = True
            cont = True
            print "\nNumber of items matching this query: %s\n\n" % \
                self.datastore._search_bucket(self.datastore.get_bucket(bucket_name),
                                              query, start=0, rows=0)["total"]

            for data in self.datastore.stream_search(bucket_name, query, item_buffer_size=COUNT_INCREMENT):
                if prompt:
                    print "This is an exemple of the data that will be deleted:\n"
                    print data, "\n"
                    cont = raw_input("Are your sure you want to continue? (y/N) ")
                    cont = cont == "y"
                    prompt = False

                if not cont:
                    print "\n**ABORTED**\n"
                    break

                pool.apply_async(bucket_delete, (bucket_name, data["_yz_rk"]), callback=action_done)
        except KeyboardInterrupt, e:
            print "Interrupting jobs..."
            pool.terminate()
            pool.join()
            raise e
        except Exception, e:
            print "Something when wrong, retry!\n\n %s\n" % e
        else:
            if prompt:
                print "\nNothing matches that query...\n"

            pool.close()
            pool.join()

    #
    # Remove actions
    #
    def do_remove_user(self, user):
        if user:
            self.datastore.delete_user(user)
        else:
            print "Please use: remove_user <user>"

    def do_remove_signature(self, key):
        if not id:
            print "ERROR: you must specify the key of the signature to remove.\nremove_signature <id>r.<rule_version>"

        self.datastore.delete_signature(key)

    def do_remove_node(self, node):
        self.datastore.delete_node(node)

    #
    # Re-index functions
    #
    def do_reindex_alerts(self, _):
        _reindex_template("alert", self.datastore.list_alert_debug_keys, self.datastore.get_alert,
                          self.datastore.save_alert)

    def do_reindex_errors(self, _):
        _reindex_template("error", self.datastore.list_error_debug_keys, self.datastore._get_bucket_item,
                          self.datastore._save_bucket_item, self.datastore.errors)

    def do_reindex_files(self, _):
        _reindex_template("file", self.datastore.list_file_debug_keys, self.datastore._get_bucket_item,
                          self.datastore._save_bucket_item, self.datastore.files)

    def do_reindex_filescores(self, _):
        _reindex_template("filescore", self.datastore.list_filescore_debug_keys, self.datastore._get_bucket_item,
                          self.datastore._save_bucket_item, self.datastore.filescores)

    def do_reindex_nodes(self, _):
        _reindex_template("node", self.datastore.list_node_debug_keys, self.datastore.get_node,
                          self.datastore.save_node)

    def do_reindex_profiles(self, _):
        _reindex_template("profile", self.datastore.list_profile_debug_keys, self.datastore.get_profile,
                          self.datastore.save_profile)

    def do_reindex_results(self, _):
        _reindex_template("result", self.datastore.list_result_debug_keys, self.datastore._get_bucket_item,
                          self.datastore._save_bucket_item, self.datastore.results)

    def do_reindex_signatures(self, _):
        _reindex_template("signature", self.datastore.list_signature_debug_keys, self.datastore.get_signature,
                          self.datastore.save_signature)

    def do_reindex_submissions(self, _):
        _reindex_template("submission", self.datastore.list_submission_debug_keys, self.datastore.get_submission,
                          self.datastore.save_submission, filter_out=["_tree", "_summary"])

    def do_reindex_users(self, _):
        _reindex_template("user", self.datastore.list_user_debug_keys, self.datastore.get_user,
                          self.datastore.save_user)

    def do_commit_all_index(self, _):
        print "Forcing commit procedure for all indexes"
        indexed_buckets = self.datastore.INDEXED_BUCKET_LIST + self.datastore.ADMIN_INDEXED_BUCKET_LIST
        for bucket in indexed_buckets:
            self.datastore.commit_index(bucket)

    def do_recreate_search_indexes(self, _):
        print "Recreating indexes:"

        indexes = [
            {'n_val': 0, 'name': 'filescore', 'schema': 'filescore'},
            {'n_val': 0, 'name': 'node', 'schema': 'node'},
            {'n_val': 0, 'name': 'signature', 'schema': 'signature'},
            {'n_val': 0, 'name': 'user', 'schema': 'user'},
            {'n_val': 0, 'name': 'file', 'schema': 'file'},
            {'n_val': 0, 'name': 'submission', 'schema': 'submission'},
            {'n_val': 0, 'name': 'error', 'schema': 'error'},
            {'n_val': 0, 'name': 'result', 'schema': 'result'},
            {'n_val': 0, 'name': 'profile', 'schema': 'profile'},
            {'n_val': 0, 'name': 'alert', 'schema': 'alert'},
        ]

        print "\tDisabling bucket association:"
        for index in indexes:
            bucket = self.datastore.client.bucket(index['name'], bucket_type="data")
            props = self.datastore.client.get_bucket_props(bucket)
            index['n_val'] = props['n_val']
            self.datastore.client.set_bucket_props(bucket, {"search_index": "_dont_index_",
                                                            "dvv_enabled": False,
                                                            "last_write_wins": True,
                                                            "allow_mult": False})
            print "\t\t%s" % index['name'].upper()

        print "\tDeleting indexes:"
        for index in indexes:
            try:
                self.datastore.client.delete_search_index(index['name'])
            except:
                pass
            print "\t\t%s" % index['name'].upper()

        print "\tCreating indexes:"
        for index in indexes:
            self.datastore.client.create_search_index(index['name'], schema=index['schema'], n_val=index['n_val'])
            print "\t\t%s" % index['name'].upper()

        print "\tAssociating bucket to index:"
        for index in indexes:
            bucket = self.datastore.client.bucket(index['name'], bucket_type="data")
            self.datastore.client.set_bucket_props(bucket, {"search_index": index['name']})
            print "\t\t%s" % index['name'].upper()

        print "All indexes successfully recreated!"

    def do_reindex_all_buckets(self, _):
        self.do_reindex_alerts(None)
        self.do_reindex_errors(None)
        self.do_reindex_files(None)
        self.do_reindex_filescores(None)
        self.do_reindex_nodes(None)
        self.do_reindex_profiles(None)
        self.do_reindex_results(None)
        self.do_reindex_signatures(None)
        self.do_reindex_submissions(None)
        self.do_reindex_users(None)

    def do_reindex_non_essential_buckets(self, _):
        self.do_reindex_alerts(None)
        self.do_reindex_errors(None)
        self.do_reindex_files(None)
        self.do_reindex_filescores(None)
        self.do_reindex_results(None)
        self.do_reindex_submissions(None)

    def do_reindex_essential_buckets(self, _):
        self.do_reindex_nodes(None)
        self.do_reindex_profiles(None)
        self.do_reindex_signatures(None)
        self.do_reindex_users(None)

    #
    # Backup functions
    #
    def do_backup(self, args):
        try:
            path, buckets = args.rsplit(" ", 1)
            buckets = buckets.split("|")
        except:
            path = args
            buckets = None

        backup_manager = SystemBackup(path)

        if not path:
            print "ERROR: You must specify an output file. You can optionally select the specific bucket(s) " \
                  "you want to backup.\nbackup <output_file> <%s>\n" % "|".join(backup_manager.VALID_BUCKETS)
            return

        backup_manager.backup(buckets)

    def do_restore(self, args):
        try:
            path, buckets = args.rsplit(" ", 1)
            buckets = buckets.split("|")
        except:
            path = args
            buckets = None

        backup_manager = SystemBackup(path)

        if not path and not os.path.exists(path):
            print "ERROR: you must specify a valid backup file to restore. You can optionally select the specific " \
                  "bucket(s) you want to restore.\nrestore <backup_file_path> <%s>\n" % \
                  "|".join(backup_manager.VALID_BUCKETS)
            return

        backup_manager.restore(buckets)

    def do_distributed_backup(self, args):
        try:
            path, buckets = args.rsplit(" ", 1)
            buckets = buckets.split("|")
        except:
            backup_manager = DistributedBackup(None)

            print "ERROR: You must specify an output folder and the specific buckets you want to backup." \
                  "\ndistributed_backup <output_folder> <%s>\n" % "|".join(backup_manager.VALID_BUCKETS)
            return

        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except:
            print "ERROR: Cannot make %s folder. Make sure you can write to this folder. " \
                  "Maybe you should write your backups in /tmp ?" % path
            return

        backup_manager = DistributedBackup(path)
        backup_manager.backup(buckets)

    def do_backup_by_query(self, args):
        try:
            path, bucket_name, query = args.split(" ", 2)
        except:
            path = raw_input("Folder to store the backup ?: ")
            bucket_name = raw_input("Which bucket?: ")
            query = raw_input("Query to run: ")

        data = self.datastore._search_bucket(self.datastore.get_bucket(bucket_name), query, start=0, rows=1)
        print "\nNumber of items matching this query: %s\n\n" % data["total"]

        if data['total'] > 0:
            print "This is an exemple of the data that will be backuped:\n"
            print data['items'][0], "\n"
            cont = raw_input("Are your sure you want to continue? (y/N) ")
            cont = cont == "y"
        else:
            cont = False

        if not cont:
            print "\n**ABORTED**\n"
            return

        deep = raw_input("Do you want to do a deep backup? (y/N) ")
        deep = deep == "y"

        total = data['total']
        if deep:
            total *= 100

        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except:
            print "ERROR: Cannot make %s folder. Make sure you can write to this folder. " \
                  "Maybe you should write your backups in /tmp ?" % path
            return

        backup_manager = DistributedBackup(path, worker_count=max(1, min(total / 1000, 50)))
        backup_manager.backup([bucket_name], follow_keys=deep, query=query)

    def do_distributed_follow_backup(self, args):
        try:
            path, buckets = args.rsplit(" ", 1)
            buckets = buckets.split("|")
        except:
            backup_manager = DistributedBackup(None)

            print "ERROR: You must specify an output folder and the specific buckets you want to backup." \
                  "\ndistributed_follow_backup <output_folder> <%s>\n" % "|".join(backup_manager.VALID_BUCKETS)
            return

        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except:
            print "ERROR: Cannot make %s folder. Make sure you can write to this folder. " \
                  "Maybe you should write your backups in /tmp ?" % path
            return

        backup_manager = DistributedBackup(path)
        backup_manager.backup(buckets, follow_keys=True)

    def do_distributed_restore(self, args):
        path = args

        if not path:
            print "ERROR: You must specify an input folder.\ndistributed_restore <input_folder>\n"
            return

        workers = len(os.listdir(path))
        backup_manager = DistributedBackup(path, worker_count=workers)
        backup_manager.restore()

    def do_distributed_cluster_backup(self, args):
        path = args

        if not path:
            print "ERROR: You must specify an output folder.\ndistributed_cluster_backup <output_folder>\n"
            return

        buckets = [
            "blob",
            "user",
            "signature",
            "node",
            "profile",
            "alert"
        ]

        try:
            if not os.path.exists(path):
                os.makedirs(path)
        except:
            print "Cannot make %s folder. Make sure you can write to this folder. " \
                  "Maybe you should write your backups in /tmp ?" % path
            return

        backup_manager = DistributedBackup(path)
        backup_manager.backup(buckets, follow_keys=True)

    #
    # Host functions
    #
    def do_host_stop(self, _):
        pprint(self.controller_client.stop(self.mac))

    def do_host_start(self, _):
        pprint(self.controller_client.start(self.mac))

    def do_host_restart(self, _):
        pprint(self.controller_client.restart(self.mac))

    def do_host_status(self, _):
        pprint(self.controller_client.status(self.mac))

    def do_host_heartbeat(self, _):
        pprint(self.controller_client.heartbeat(self.mac))

    #
    # Enable/Disable functions
    #
    def _set_enabled_status(self, enabled=True):
        reg = self.datastore.get_node(self.mac)
        if not reg:
            print 'No such registration'
            return
        reg['enabled'] = enabled
        self.datastore.save_node(self.mac, reg)
        return "Rule enabled field is now set to %s" % enabled

    def do_enable_node(self, _):
        print(self._set_enabled_status(True))

    def do_disable_node(self, _):
        print(self._set_enabled_status(False))

    def do_enable_service(self, name):
        if not name:
            print "You must provide a service name"
            return

        service_entry = self.datastore.get_service(name)
        if not service_entry:
            print "Service '%s' does not exists"
            return

        if not service_entry['enabled']:
            service_entry['enabled'] = True
        self.datastore.save_service(name, service_entry)
        print 'Enabled'

    def do_disable_service(self, name):
        if not name:
            print "You must provide a service name"
            return

        service_entry = self.datastore.get_service(name)
        if not service_entry:
            print "Service '%s' does not exists"
            return

        if service_entry['enabled']:
            service_entry['enabled'] = False
        self.datastore.save_service(name, service_entry)
        print 'Disabled'

    #
    # Node Jump
    #
    def do_change_node(self, mac):
        if not mac:
            print "You must provide a mac to switch to"
            return

        if mac not in self.datastore.list_node_keys():
            print 'Warning. (%s) is not a registered agent.' % mac
            return

        self.mac = mac
        self._update_context()

    #
    # Exit functions
    #
    def do_exit(self, arg):
        arg = arg or 0
        sys.exit(int(arg))

    def do_quit(self, arg):
        self.do_exit(arg)

    # noinspection PyPep8Naming
    def do_EOF(self, _):
        print
        self.do_exit(0)

    #
    # Dispatcher functions
    #
    def do_dispatcher_get_time(self, dispatcher):
        if not dispatcher:
            dispatcher = '0'
        pprint(DispatchClient.get_system_time(dispatcher))

    def do_dispatcher_list_services(self, dispatcher):
        if not dispatcher:
            dispatcher = '0'
        pprint(DispatchClient.list_service_info(dispatcher))

    def do_dispatcher_outstanding(self, dispatcher):
        if not dispatcher:
            for dispatcher in range(int(self.config.core.dispatcher.shards)):
                pprint(DispatchClient.list_outstanding(dispatcher))
            return
        pprint(DispatchClient.list_outstanding(dispatcher))

    def do_dispatcher_services(self, sid):
        if not sid:
            print "You must provide a SID"
            return

        pprint(DispatchClient.get_outstanding_services(sid))

    def do_dispatcher_explain_state(self, sid):
        if not sid:
            print "You must provide a SID"
            return

        name = reply_queue_name('SID')
        t = Task({}, **{
            'sid': sid,
            'state': 'explain_state',
            'watch_queue': name,
        })
        n = forge.determine_dispatcher(sid)
        forge.get_control_queue('control-queue-' + str(n)).push(t.raw)
        nq = NamedQueue(name)
        r = nq.pop(timeout=3000)
        while r:
            print '    ' * int(r['depth']) + str(r['srl']), str(r['message'])
            r = nq.pop(timeout=3000)
        if r is None:
            print 'Timed out'

    #
    # GET functions
    #
    def do_get_current_node_profile(self, _):
        reg = self.datastore.get_node(self.mac)
        if not reg:
            print "Machine not registered: %s" % self.mac
            return

        profile_name = reg['profile']
        if not profile_name:
            print 'Profile not found: %s' % profile_name
            return
        profile_contents = self.datastore.get_profile(profile_name)
        profile = {profile_name: profile_contents}
        pprint(profile)

    def do_get_profile_by_name(self, profilename):
        if not profilename:
            print "You must provide a profile name"
            return
        pprint(self.datastore.get_profile(profilename.strip("'")))

    def do_get_node(self, mac=None):
        mac = mac or self.mac
        pprint(self.datastore.get_node(mac))

    def do_get_service_by_name(self, name):
        if not name:
            print "You must provide a name"
            return
        service_entry = self.datastore.get_service(name)
        print pformat(service_entry)

    #
    # Wipe functions
    #
    def do_wipe_non_essential(self, _):
        self.do_wipe_files(None)
        self.do_wipe_submissions(None)
        self.do_wipe_errors(None)
        self.do_wipe_results(None)
        self.do_wipe_alerts(None)
        self.do_wipe_emptyresult(None)
        self.do_wipe_filescore(None)

    def do_wipe_data_except_alerts(self, _):
        self.do_wipe_submissions(None)
        self.do_wipe_files(None)
        self.do_wipe_errors(None)
        self.do_wipe_results(None)
        self.do_wipe_emptyresult(None)
        self.do_wipe_filescore(None)

    def do_data_reset(self, full):
        self.do_backup("/tmp/riak_cli_backup.tmp")

        self.do_wipe_nodes(None)
        self.do_wipe_profiles(None)
        self.do_wipe_signatures(None)
        self.do_wipe_users(None)
        self.do_wipe_blob(None)

        if full == "full":
            self.do_wipe_files(None)
            self.do_wipe_submissions(None)
            self.do_wipe_errors(None)
            self.do_wipe_results(None)
            self.do_wipe_alerts(None)
            self.do_wipe_emptyresult(None)
            self.do_wipe_filescore(None)
            self.do_commit_all_index(None)

        self.do_restore("/tmp/riak_cli_backup.tmp")

    def do_wipe_results(self, _):
        self.datastore.wipe_results()

    def do_wipe_alerts(self, _):
        self.datastore.wipe_alerts()

    def do_wipe_submissions(self, _):
        self.datastore.wipe_submissions()

    def do_wipe_errors(self, _):
        self.datastore.wipe_errors()

    def do_wipe_files(self, _):
        self.datastore.wipe_files()

    def do_wipe_users(self, _):
        self.datastore.wipe_users()

    def do_wipe_signatures(self, _):
        self.datastore.wipe_signatures()

    def do_wipe_profiles(self, _):
        self.datastore.wipe_profiles()

    def do_wipe_emptyresult(self, _):
        self.datastore.wipe_emptyresults()

    def do_wipe_filescore(self, _):
        self.datastore.wipe_filescores()

    def do_wipe_vm_nodes(self, _):
        self.datastore.wipe_vm_nodes()

    def do_wipe_nodes(self, _):
        self.datastore.wipe_nodes()

    def do_wipe_blob(self, _):
        self.datastore.wipe_blobs()

    #
    # List functions
    #
    def do_list_profiles(self, _):
        pprint(self.datastore.list_profile_keys())

    def do_list_services(self, _):
        for service in self.datastore.list_service_keys():
            print service

    def do_list_nodes(self, _):
        agents = self.datastore.list_node_keys()
        for agent in agents:
            reg = self.datastore.get_node(agent) or {}
            host, ip, enabled = reg.get('hostname', None), reg.get('ip', None), reg.get('enabled', None)
            print '%s (host:%s ip:%s enabled:%s)' % (agent, host, ip, enabled)

    def do_list_users(self, _):
        for u in self.datastore.list_user_keys():
            if "_options" not in u and "_favorites" not in u and "_avatar" not in u:
                print u

    #
    # List functions
    #
    def do_change_signature_status_by_query(self, args):
        valid_statuses = ["TESTING", "STAGING", "DISABLED", "DEPLOYED", "NOISY"]
        pool = multiprocessing.Pool(processes=PROCESSES_COUNT, initializer=init)
        try:
            status, query = args.split(" ", 1)
        except:
            status = raw_input("New status?: ")
            query = raw_input("Query to run: ")

        if status not in valid_statuses:
            print "Status must be one of the following: %s" % ", ".join(valid_statuses)

        try:
            prompt = True
            cont = True
            print "\nNumber of items matching this query: %s\n\n" % \
                self.datastore._search_bucket(self.datastore.get_bucket("signature"),
                                              query, start=0, rows=0)["total"]

            for data in self.datastore.stream_search("signature", query, item_buffer_size=COUNT_INCREMENT):
                if prompt:
                    print "This is an exemple of the data that will be deleted:\n"
                    print data, "\n"
                    cont = raw_input("Are your sure you want to continue? (y/N) ")
                    cont = cont == "y"
                    prompt = False

                if not cont:
                    print "\n**ABORTED**\n"
                    break

                pool.apply_async(update_signature_status, (status, data["_yz_rk"]))
        except KeyboardInterrupt, e:
            print "Interrupting jobs..."
            pool.terminate()
            pool.join()
            raise e
        except Exception, e:
            print "Something when wrong, retry!\n\n %s\n" % e
        else:
            if prompt:
                print "\nNothing matches that query...\n"

            pool.close()
            pool.join()


def print_banner():
    from assemblyline.al.common import banner
    from colors import red
    print red(banner.BANNER)


def shell_main():
    print_banner()
    cli = ALCommandLineInterface()
    cli.cmdloop()


if __name__ == '__main__':
    try:
        shell_main()
    except KeyboardInterrupt:
        exit()
