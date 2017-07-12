#!/usr/bin/env python

# Suppress all warnings
import warnings
warnings.filterwarnings("ignore")

import cmd
import inspect
import sys
import multiprocessing
import os
import re
import signal
import time

from pprint import pprint

from assemblyline.common.importing import module_attribute_by_name
from assemblyline.common.net import get_mac_address
from assemblyline.al.common import forge, log as al_log
from assemblyline.al.common.backupmanager import DistributedBackup
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
def update_signature_status(status, key, datastore=None):
    try:
        global DATASTORE
        if not DATASTORE:
            DATASTORE = datastore
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

    def __init__(self, show_prompt=True):
        cmd.Cmd.__init__(self)
        self.local_mac = get_mac_address()
        self.mac = self.local_mac  # the mac we are currently targetting.
        self.queue = None
        self.prompt = ""
        self.intro = ""
        self.datastore = forge.get_datastore()
        self.controller_client = ControllerClient(async=False)
        self.vmm_client = VmmAgentClient(async=False)
        self.svc_client = ServiceAgentClient(async=False)
        self.config = forge.get_config()
        if show_prompt:
            self._update_context()

    def _update_context(self):
        label = 'local' if self.mac == self.local_mac else 'remote'
        self.prompt = '%s (%s)> ' % (self.mac, label)
        self.queue = NamedQueue(self.mac)
        self.intro = 'AL 3.1 - Console. (type help).'

    def _send_agent_cmd(self, command, args=None):
        self.queue.push(AgentRequest(self.mac, command, body=args))

    def _send_agent_rpc(self, command, args=None):
        return send_rpc(AgentRequest(self.mac, command, body=args))

    def _parse_args(self, s, platform='this'):
        """Multi-platform variant of shlex.split() for command-line splitting.
        For use with subprocess, for argv injection etc. Using fast REGEX.

        platform: 'this' = auto from current platform;
                  1 = POSIX;
                  0 = Windows/CMD
                  (other values reserved)
        """
        if platform == 'this':
            platform = (sys.platform != 'win32')
        if platform == 1:
            cmd_lex = r'''"((?:\\["\\]|[^"])*)"|'([^']*)'|(\\.)|(&&?|\|\|?|\d?\>|[<])|([^\s'"\\&|<>]+)|(\s+)|(.)'''
        elif platform == 0:
            cmd_lex = r'''"((?:""|\\["\\]|[^"])*)"?()|(\\\\(?=\\*")|\\")|(&&?|\|\|?|\d?>|[<])|([^\s"&|<>]+)|(\s+)|(.)'''
        else:
            raise AssertionError('unkown platform %r' % platform)

        args = []
        accu = None  # collects pieces of one arg
        for qs, qss, esc, pipe, word, white, fail in re.findall(cmd_lex, s):
            if word:
                pass  # most frequent
            elif esc:
                word = esc[1]
            elif white or pipe:
                if accu is not None:
                    args.append(accu)
                if pipe:
                    args.append(pipe)
                accu = None
                continue
            elif fail:
                raise ValueError("invalid or incomplete shell string")
            elif qs:
                word = qs.replace('\\"', '"').replace('\\\\', '\\')
                if platform == 0:
                    word = word.replace('""', '"')
            else:
                word = qss  # may be even empty; must be last

            accu = (accu or '') + word

        if accu is not None:
            args.append(accu)

        return args

    def _print_error(self, msg):
        stack_func = None
        stack = inspect.stack()
        for item in stack:
            if 'cli.py' in item[1] and '_print_error' not in item[3]:
                stack_func = item[3]
                break

        if msg:
            print "ERROR: " + msg + "\n"

        if stack_func:
            function_doc = inspect.getdoc(getattr(self, stack_func))
            if function_doc:
                print "Usage:\n" + function_doc + "\n"

    #
    # Exit actions
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
    # Backup actions
    #
    def do_backup(self, args):
        """
        backup <destination_file>
               <destination_file> <bucket_name> [follow] [force] <query>
        """
        args = self._parse_args(args)

        follow = False
        if 'follow' in args:
            follow = True
            args.remove('follow')

        force = False
        if 'force' in args:
            force = True
            args.remove('force')

        if len(args) == 1:
            dest = args[0]
            system_backup = True
            bucket = None
            follow = False
            query = None
        elif len(args) == 3:
            dest, bucket, query = args
            system_backup = False
        else:
            self._print_error("Wrong number of arguments for backup command.")
            return

        if system_backup:
            backup_manager = DistributedBackup(dest, worker_count=5)
            backup_manager.backup(["blob", "node", "profile", "signature", "user"])
        else:
            data = self.datastore._search_bucket(self.datastore.get_bucket(bucket), query, start=0, rows=1)

            if not force:
                print "\nNumber of items matching this query: %s\n\n" % data["total"]

                if data['total'] > 0:
                    print "This is an exemple of the data that will be backuped:\n"
                    print data['items'][0], "\n"
                    if self.prompt:
                        cont = raw_input("Are your sure you want to continue? (y/N) ")
                        cont = cont == "y"
                    else:
                        print "You are not in interactive mode therefor the backup was not executed. " \
                              "Add 'force' to your commandline to execute the backup."
                        cont = False
                else:
                    cont = False

                if not cont:
                    print "\n**ABORTED**\n"
                    return

            total = data['total']
            if follow:
                total *= 100

            try:
                if not os.path.exists(dest):
                    os.makedirs(dest)
            except:
                print "Cannot make %s folder. Make sure you can write to this folder. " \
                      "Maybe you should write your backups in /tmp ?" % dest
                return

            backup_manager = DistributedBackup(dest, worker_count=max(1, min(total / 1000, 50)))
            backup_manager.backup([bucket], follow_keys=follow, query=query)

    def do_restore(self, args):
        """
        restore <backup_directory>
        """
        args = self._parse_args(args)

        if len(args) not in [1]:
            self._print_error("Wrong number of arguments for restore command.")
            return

        path = args[0]
        if not path:
            self._print_error("You must specify an input folder.")
            return

        workers = len([x for x in os.listdir(path) if '.part' in x])
        backup_manager = DistributedBackup(path, worker_count=workers)
        backup_manager.restore()

    #
    # Seed actions
    #
    def do_reseed(self, args):
        """
        reseed    current
                  previous
                  module <python_path_of_seed> [<destination_blob>]
        """
        args = self._parse_args(args)

        if len(args) not in [1, 2, 3]:
            self._print_error("Wrong number of arguments for reseed command.")
            return

        action_type = args[0]

        if action_type == 'current':
            seed_path = self.datastore.get_blob('seed_module')
            target = 'seed'
        elif action_type == 'previous':
            cur_seed = self.datastore.get_blob('seed')
            self.datastore.save_blob('seed', self.datastore.get_blob('previous_seed'))
            self.datastore.save_blob('previous_seed', cur_seed)
            print "Current and previous seed where swapped."
            return
        elif action_type == 'module':
            if len(args) == 2:
                seed_path = args[1]
                target = 'seed'
            elif len(args) == 3:
                seed_path, target = args[1:]
            else:
                self._print_error("Wrong number of arguments for reseed command.")
                return
        else:
            self._print_error("Invalid reseed action '%s' must be one of current, previous or module.")
            return

        try:
            seed = module_attribute_by_name(seed_path)
        except:
            print "Unable to load seed form path: %s" % seed_path
            return

        services_to_register = seed['services']['master_list']

        for service, svc_detail in services_to_register.iteritems():
            classpath = svc_detail.get('classpath', "al_services.%s.%s" % (svc_detail['repo'],
                                                                           svc_detail['class_name']))
            config_overrides = svc_detail.get('config', {})

            new_srv_registration = register_service.register(classpath, config_overrides=config_overrides,
                                                             store_config=False,
                                                             enabled=svc_detail.get('enabled', True))
            seed['services']['master_list'][service].update(new_srv_registration)

        if target == "seed":
            cur_seed = self.datastore.get_blob('seed')
            self.datastore.save_blob('previous_seed', cur_seed)
            print "Current seed was copied to previous_seed key."

        self.datastore.save_blob(target, seed)
        print "Module '%s' was loaded into blob '%s'." % (seed_path, target)

    #
    # Delete actions
    #
    def do_delete(self, args):
        """
        delete <bucket> [full] [force] <query>
        """
        valid_buckets = self.datastore.INDEXED_BUCKET_LIST + self.datastore.ADMIN_INDEXED_BUCKET_LIST
        args = self._parse_args(args)

        if 'full' in args:
            full = True
            args.remove('full')
        else:
            full = False

        if 'force' in args:
            force = True
            args.remove('force')
        else:
            force = False

        if len(args) != 2:
            self._print_error("Wrong number of arguments for delete command.")
            return

        bucket, query = args

        if bucket not in valid_buckets:
            self._print_error("\nInvalid bucket specified: %s\n\n"
                              "Valid buckets are:\n%s" % (bucket, "\n".join(valid_buckets)))
            return

        pool = multiprocessing.Pool(processes=PROCESSES_COUNT, initializer=init)
        try:
            cont = force
            test_data = self.datastore._search_bucket(self.datastore.get_bucket(bucket), query, start=0, rows=1)
            if not test_data["total"]:
                print "Nothing matches the query."
                return

            if not force:
                print "\nNumber of items matching this query: %s\n\n" % test_data["total"]
                print "This is an example of the data that will be deleted:\n"
                print test_data['items'][0], "\n"
                if self.prompt:
                    cont = raw_input("Are your sure you want to continue? (y/N) ")
                    cont = cont == "y"

                    if not cont:
                        print "\n**ABORTED**\n"
                        return
                else:
                    print "You are not in interactive mode therefor the delete was not executed. " \
                          "Add 'force' to your commandline to execute the delete."
                    return

            if cont:
                for data in self.datastore.stream_search(bucket, query, fl="_yz_rk", item_buffer_size=COUNT_INCREMENT):
                    if full and bucket == 'submission':
                        func = submission_delete_tree
                        func_args = (data["_yz_rk"],)
                    else:
                        func = bucket_delete
                        func_args = (bucket, data["_yz_rk"])

                    pool.apply_async(func, func_args, callback=action_done)

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
            self.datastore.commit_index(bucket)
            print "Data of bucket '%s' matching query '%s' has been deleted." % (bucket, query)

    #
    # bucket actions
    #
    def do_node(self, args):
        """
        node list
             show    <id>
             disable <id>
             enable  <id>
             remove  <id>
        """
        valid_actions = ['list', 'show', 'disable', 'enable', 'remove']
        args = self._parse_args(args)

        if len(args) == 1:
            action_type = args[0]
            item_id = None
        elif len(args) == 2:
            action_type, item_id = args
        else:
            self._print_error("Wrong number of arguments for node command.")
            return

        if action_type not in valid_actions:
            self._print_error("Invalid action for node command.")
            return

        if action_type == 'list':
            for key in self.datastore.list_node_keys():
                print key
        elif action_type == 'show' and item_id:
            pprint(self.datastore.get_node(item_id))
        elif action_type == 'disable' and item_id:
            item = self.datastore.get_node(item_id)
            if item:
                item['enabled'] = False
                self.datastore.save_node(item_id, item)
                print "%s was disabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'enable' and item_id:
            item = self.datastore.get_node(item_id)
            if item:
                item['enabled'] = True
                self.datastore.save_node(item_id, item)
                print "%s was enabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'remove' and item_id:
            self.datastore.delete_node(item_id)
        else:
            self._print_error("Invalid command parameters")

    def do_profile(self, args):
        """
        profile list
                show    <id>
                remove  <id>
        """
        valid_actions = ['list', 'show', 'remove']
        args = self._parse_args(args)

        if len(args) == 1:
            action_type = args[0]
            item_id = None
        elif len(args) == 2:
            action_type, item_id = args
        else:
            self._print_error("Wrong number of arguments for profile command.")
            return

        if action_type not in valid_actions:
            self._print_error("Invalid action for profile command.")
            return

        if action_type == 'list':
            for key in self.datastore.list_profile_keys():
                print key
        elif action_type == 'show' and item_id:
            pprint(self.datastore.get_profile(item_id))
        elif action_type == 'remove' and item_id:
            self.datastore.delete_profile(item_id)
        else:
            self._print_error("Invalid command parameters")

    def do_service(self, args):
        """
        service list
                show    <id>
                disable <id>
                enable  <id>
                remove  <id>
        """
        valid_actions = ['list', 'show', 'disable', 'enable', 'remove']
        args = self._parse_args(args)

        if len(args) == 1:
            action_type = args[0]
            item_id = None
        elif len(args) == 2:
            action_type, item_id = args
        else:
            self._print_error("Wrong number of arguments for service command.")
            return

        if action_type not in valid_actions:
            self._print_error("Invalid action for service command.")
            return

        if action_type == 'list':
            for key in self.datastore.list_service_keys():
                print key
        elif action_type == 'show' and item_id:
            pprint(self.datastore.get_service(item_id))
        elif action_type == 'disable' and item_id:
            item = self.datastore.get_service(item_id)
            if item:
                item['enabled'] = False
                self.datastore.save_service(item_id, item)
                print "%s was disabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'enable' and item_id:
            item = self.datastore.get_service(item_id)
            if item:
                item['enabled'] = True
                self.datastore.save_service(item_id, item)
                print "%s was enabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'remove' and item_id:
            self.datastore.delete_service(item_id)
        else:
            self._print_error("Invalid command parameters")

    def do_signature(self, args):
        """
        signature show          <id>
                  change_status by_id    [force] <status_value> <id>
                  change_status by_query [force] <status_value> <query>
                  remove        <id>
        """
        valid_actions = ['show', 'change_status', 'remove']
        args = self._parse_args(args)

        if 'force' in args:
            force = True
        else:
            force = False

        if len(args) == 2:
            action_type, item_id = args
            id_type = status = None
        elif len(args) == 4:
            action_type, id_type, status, item_id = args
        else:
            self._print_error("Wrong number of arguments for signature command.")
            return

        if action_type not in valid_actions:
            self._print_error("Invalid action for signature command.")
            return

        if action_type == 'show' and item_id:
            pprint(self.datastore.get_signature(item_id))
        elif action_type == 'change_status' and item_id and id_type and status:
            if status not in YaraParser.STATUSES:
                self._print_error("\nInvalid status for action 'change_status' of signature command."
                                  "\n\nValid statuses are:\n%s" % "\n".join(YaraParser.STATUSES))
                return

            if id_type == 'by_id':
                update_signature_status(status, item_id, datastore=self.datastore)
                print "Signature '%s' was changed to status %s." % (item_id, status)
            elif id_type == 'by_query':
                pool = multiprocessing.Pool(processes=PROCESSES_COUNT, initializer=init)
                try:
                    cont = force
                    test_data = self.datastore._search_bucket(self.datastore.get_bucket("signature"),
                                                              item_id, start=0, rows=1)
                    if not test_data["total"]:
                        print "Nothing matches the query."
                        return

                    if not force:
                        print "\nNumber of items matching this query: %s\n\n" % test_data["total"]
                        print "This is an exemple of the signatures that will change status:\n"
                        print test_data['items'][0], "\n"
                        if self.prompt:
                            cont = raw_input("Are your sure you want to continue? (y/N) ")
                            cont = cont == "y"

                            if not cont:
                                print "\n**ABORTED**\n"
                                return
                        else:
                            print "You are not in interactive mode therefor the status change was not executed. " \
                                  "Add 'force' to your commandline to execute the status change."
                            return

                    if cont:
                        for data in self.datastore.stream_search("signature", item_id, fl="_yz_rk",
                                                                 item_buffer_size=COUNT_INCREMENT):
                            pool.apply_async(update_signature_status, (status, data["_yz_rk"]))
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
                    print "Signatures matching query '%s' were changed to status '%s'." % (item_id, status)
            else:
                self._print_error("Invalid action parameters for action 'change_status' of signature command.")

        elif action_type == 'remove' and item_id:
            self.datastore.delete_signature(item_id)
        else:
            self._print_error("Invalid command parameters")

    def do_user(self, args):
        """
        user list
             show        <id>
             disable     <id>
             enable      <id>
             set_admin   <id>
             unset_admin <id>
             remove      <id>
        """
        valid_actions = ['list', 'show', 'disable', 'enable', 'remove', 'set_admin', 'unset_admin']
        args = self._parse_args(args)

        if len(args) == 1:
            action_type = args[0]
            item_id = None
        elif len(args) == 2:
            action_type, item_id = args
        else:
            self._print_error("Wrong number of arguments for user command.")
            return

        if action_type not in valid_actions:
            self._print_error("Invalid action for user command.")
            return

        if action_type == 'list':
            for key in [x for x in self.datastore.list_user_keys() if '_options' not in x and '_avatar' not in x]:
                print key
        elif action_type == 'show' and item_id:
            pprint(self.datastore.get_user(item_id))
        elif action_type == 'disable' and item_id:
            item = self.datastore.get_user(item_id)
            if item:
                item['is_active'] = False
                self.datastore.save_user(item_id, item)
                print "%s was disabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'enable' and item_id:
            item = self.datastore.get_user(item_id)
            if item:
                item['is_active'] = True
                self.datastore.save_user(item_id, item)
                print "%s was enabled" % item_id
            else:
                print "%s does not exist" % item_id
        elif action_type == 'set_admin' and item_id:
                item = self.datastore.get_user(item_id)
                if item:
                    item['is_admin'] = True
                    self.datastore.save_user(item_id, item)
                    print "%s was added admin priviledges" % item_id
                else:
                    print "%s does not exist" % item_id
        elif action_type == 'unset_admin' and item_id:
                item = self.datastore.get_user(item_id)
                if item:
                    item['is_admin'] = False
                    self.datastore.save_user(item_id, item)
                    print "%s was removed admin priviledges" % item_id
                else:
                    print "%s does not exist" % item_id
        elif action_type == 'remove' and item_id:
            self.datastore.delete_user(item_id)
        else:
            self._print_error("Invalid command parameters")

    #
    # Index actions
    #
    def do_index(self, args):
        """
        index commit   [<bucket>]
              reindex  [<bucket>]
              reset

        """
        _reindex_map = {
            "alert": [self.datastore.list_alert_debug_keys, self.datastore.get_alert, self.datastore.save_alert,
                      None, None],
            "error": [self.datastore.list_error_debug_keys, self.datastore._get_bucket_item,
                      self.datastore._save_bucket_item, self.datastore.errors, None],
            "file": [self.datastore.list_file_debug_keys, self.datastore._get_bucket_item,
                     self.datastore._save_bucket_item, self.datastore.files, None],
            "filescore": [self.datastore.list_filescore_debug_keys, self.datastore._get_bucket_item,
                          self.datastore._save_bucket_item, self.datastore.filescores, None],
            "node": [self.datastore.list_node_debug_keys, self.datastore.get_node, self.datastore.save_node,
                     None, None],
            "profile": [self.datastore.list_profile_debug_keys, self.datastore.get_profile, self.datastore.save_profile,
                        None, None],
            "result": [self.datastore.list_result_debug_keys, self.datastore._get_bucket_item,
                       self.datastore._save_bucket_item, self.datastore.results, None],
            "signature": [self.datastore.list_signature_debug_keys, self.datastore.get_signature,
                          self.datastore.save_signature, None, None],
            "submission": [self.datastore.list_submission_debug_keys, self.datastore.get_submission,
                           self.datastore.save_submission, None, ["_tree", "_summary"]],
            "user": [self.datastore.list_user_debug_keys, self.datastore.get_user, self.datastore.save_user,
                     None, None],
            "workflow": [self.datastore.list_workflow_debug_keys, self.datastore.get_workflow,
                         self.datastore.save_workflow, None, None]
        }

        valid_buckets = sorted(self.datastore.INDEXED_BUCKET_LIST + self.datastore.ADMIN_INDEXED_BUCKET_LIST)
        valid_actions = ['commit', 'reindex', 'reset']

        args = self._parse_args(args)

        if len(args) == 1:
            action_type = args[0]
            bucket = None
        elif len(args) == 2:
            action_type, bucket = args
        else:
            self._print_error("Wrong number of arguments for delete command.")
            return

        if action_type not in valid_actions:
            self._print_error("\nInvalid action specified: %s\n\n"
                              "Valid actions are:\n%s" % (action_type, "\n".join(valid_actions)))
            return

        if bucket and bucket not in valid_buckets:
            self._print_error("\nInvalid bucket specified: %s\n\n"
                              "Valid buckets are:\n%s" % (bucket, "\n".join(valid_buckets)))
            return

        if action_type == 'reindex':
            if bucket:
                reindex_args = _reindex_map[bucket]
                _reindex_template(bucket, reindex_args[0], reindex_args[1],
                                  reindex_args[2], reindex_args[3], reindex_args[4])
            else:
                for bucket in valid_buckets:
                    reindex_args = _reindex_map[bucket]
                    _reindex_template(bucket, reindex_args[0], reindex_args[1],
                                      reindex_args[2], reindex_args[3], reindex_args[4])
        elif action_type == 'commit':
            if bucket:
                self.datastore.commit_index(bucket)
                print "Index %s was commited." % bucket.upper()
            else:
                print "Forcing commit procedure for all indexes..."
                for bucket in valid_buckets:
                    print "    Index %s was commited." % bucket.upper()
                    self.datastore.commit_index(bucket)
                print "All indexes commited."
        elif action_type == 'reset':
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

    #
    # Host functions
    #
    def do_old_host_stop(self, _):
        pprint(self.controller_client.stop(self.mac))

    def do_old_host_start(self, _):
        pprint(self.controller_client.start(self.mac))

    def do_old_host_restart(self, _):
        pprint(self.controller_client.restart(self.mac))

    def do_old_host_status(self, _):
        pprint(self.controller_client.status(self.mac))

    def do_old_host_heartbeat(self, _):
        pprint(self.controller_client.heartbeat(self.mac))

    #
    # Node Jump
    #
    def do_old_change_node(self, mac):
        if not mac:
            print "You must provide a mac to switch to"
            return

        if mac not in self.datastore.list_node_keys():
            print 'Warning. (%s) is not a registered agent.' % mac
            return

        self.mac = mac
        self._update_context()

    #
    # Dispatcher functions
    #
    def do_old_dispatcher_get_time(self, dispatcher):
        if not dispatcher:
            dispatcher = '0'
        pprint(DispatchClient.get_system_time(dispatcher))

    def do_old_dispatcher_list_services(self, dispatcher):
        if not dispatcher:
            dispatcher = '0'
        pprint(DispatchClient.list_service_info(dispatcher))

    def do_old_dispatcher_outstanding(self, dispatcher):
        if not dispatcher:
            for dispatcher in range(int(self.config.core.dispatcher.shards)):
                pprint(DispatchClient.list_outstanding(dispatcher))
            return
        pprint(DispatchClient.list_outstanding(dispatcher))

    def do_old_dispatcher_services(self, sid):
        if not sid:
            print "You must provide a SID"
            return

        pprint(DispatchClient.get_outstanding_services(sid))

    def do_old_dispatcher_explain_state(self, sid):
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
    # Wipe functions
    #
    def do_old_wipe_non_essential(self, _):
        self.do_old_wipe_files(None)
        self.do_old_wipe_submissions(None)
        self.do_old_wipe_errors(None)
        self.do_old_wipe_results(None)
        self.do_old_wipe_alerts(None)
        self.do_old_wipe_emptyresult(None)
        self.do_old_wipe_filescore(None)

    def do_old_wipe_data_except_alerts(self, _):
        self.do_old_wipe_submissions(None)
        self.do_old_wipe_files(None)
        self.do_old_wipe_errors(None)
        self.do_old_wipe_results(None)
        self.do_old_wipe_emptyresult(None)
        self.do_old_wipe_filescore(None)

    def do_old_data_reset(self, full):
        self.do_old_backup("/tmp/riak_cli_backup.tmp")

        self.do_old_wipe_nodes(None)
        self.do_old_wipe_profiles(None)
        self.do_old_wipe_signatures(None)
        self.do_old_wipe_users(None)
        self.do_old_wipe_blob(None)

        if full == "full":
            self.do_old_wipe_files(None)
            self.do_old_wipe_submissions(None)
            self.do_old_wipe_errors(None)
            self.do_old_wipe_results(None)
            self.do_old_wipe_alerts(None)
            self.do_old_wipe_emptyresult(None)
            self.do_old_wipe_filescore(None)
            self.do_old_commit_all_index(None)

        self.do_old_restore("/tmp/riak_cli_backup.tmp")

    def do_old_wipe_results(self, _):
        self.datastore.wipe_results()

    def do_old_wipe_alerts(self, _):
        self.datastore.wipe_alerts()

    def do_old_wipe_submissions(self, _):
        self.datastore.wipe_submissions()

    def do_old_wipe_errors(self, _):
        self.datastore.wipe_errors()

    def do_old_wipe_files(self, _):
        self.datastore.wipe_files()

    def do_old_wipe_users(self, _):
        self.datastore.wipe_users()

    def do_old_wipe_signatures(self, _):
        self.datastore.wipe_signatures()

    def do_old_wipe_profiles(self, _):
        self.datastore.wipe_profiles()

    def do_old_wipe_emptyresult(self, _):
        self.datastore.wipe_emptyresults()

    def do_old_wipe_filescore(self, _):
        self.datastore.wipe_filescores()

    def do_old_wipe_vm_nodes(self, _):
        self.datastore.wipe_vm_nodes()

    def do_old_wipe_nodes(self, _):
        self.datastore.wipe_nodes()

    def do_old_wipe_blob(self, _):
        self.datastore.wipe_blobs()




def print_banner():
    from assemblyline.al.common import banner
    from colors import red
    print red(banner.BANNER)


def shell_main():
    show_prompt = False
    if sys.stdin.isatty():
        print_banner()
        show_prompt = True
    cli = ALCommandLineInterface(show_prompt)
    cli.cmdloop()


if __name__ == '__main__':
    try:
        shell_main()
    except KeyboardInterrupt:
        exit()
