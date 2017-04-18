import datetime
import linecache
import logging
import os
import re
import shutil
import subprocess
import tempfile

from assemblyline_client import Client


class YaraValidator(object):

    def __init__(self, data, externals=None, logger=None):
        if not logger:
            from assemblyline.al.common import log as al_log
            al_log.init_logging('YaraValidator')
            logger = logging.getLogger('assemblyline.YaraValidator')
            logger.setLevel(logging.WARNING)
        self.log = logger
        self.data = data
        self.externals = externals

    def _clean(self, rule_file, line, message):
        while True:
            rule_start = re.compile(r'^(global|private|"")[ ]?(private|"")[ ]? rule \{')
            line = linecache.getline(rule_file, line)

            invalid_rule = ''
            rule_line = 0
            error_message = "Yara rule '{0}' removed because of an error at line {1} [{2}]." \
                .format(invalid_rule, rule_line, message)
            self.log(error_message)
            break

        return rule_file, invalid_rule

    def paranoid_rule_check(self, rule_path):
        # Run rules seperately on command line to ensure there are no errors
        print_val = "--==Rules_validated++__"
        cmd = "python -c " \
              "\"import yara\n" \
              "try: " \
              "yara.compile('%s', externals=%s).match(data='');" \
              "print '%s'\n" \
              "except yara.SyntaxError as e:" \
              "print 'yara.SyntaxError.{}' .format(e)\""
        p = subprocess.Popen(cmd % (rule_path, self.externals, print_val), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True, cwd="/tmp")

        stdout, stderr = p.communicate()

        if print_val not in stdout:
            if stdout.startswith('yara.SyntaxError'):
                raise Exception(stdout)
            else:
                raise Exception("YaraValidator has failed! " + stderr)

    def validate_rules(self, rules_txt, datastore=None):
        tmp_dir = tempfile.mkdtemp(dir='/tmp')
        valid_file = False
        while not valid_file:
            try:
                rules_file = os.path.join(tmp_dir, 'rules.yar')
                with open(rules_file, 'w') as f:
                    f.write(rules_txt)
                try:
                    self.paranoid_rule_check(rules_file)
                    valid_file = True
                # If something goes wrong, clean rules until valid file given
                except Exception as e:
                    if e.message.startswith('yara.SyntaxError'):

                        e_line = int(e.message.split('):', 1)[0].split("(", -1)[1])
                        e_message = e.message.split("): ", 1)[1]
                        rules_txt, invalid_rule = self._clean(rules_txt, e_line, e_message)

                        # If datastore object given, change status of signature to INVALID in Riak
                        if datastore:
                            config = datastore.get_config()
                            signature_url = config.services.masterlist.Yara.config.SIGNATURE_URL
                            signature_user = config.services.masterlist.Yara.config.SIGNATURE_USER
                            signature_pass = config.services.masterlist.Yara.config.SIGNATURE_PASS
                            sigdata = datastore.get_signature(invalid_rule)
                            # Check this in case someone already marked it as invalid
                            if sigdata['meta']['al_status'] == 'INVALID':
                                continue
                            # Get the offending sig ID
                            update_client = Client(signature_url, auth=(signature_user, signature_pass))
                            sig_query = "name:{} AND meta.al_status:(DEPLOYED OR NOISY)".format(invalid_rule)
                            # Mark and update Riak
                            for sig in update_client.search.stream.signature(sig_query):
                                sigsid = sig['_yz_rk']
                                sigdata['meta']['al_status'] = 'INVALID'
                                today = datetime.date.today().isoformat()
                                sigdata['meta']['al_state_change_date'] = today
                                sigdata['meta']['al_state_change_user'] = signature_user
                                sigdata['comments'].append("AL ERROR MSG:{}".format(e_message))
                                datastore.save_signature(sigsid, sigdata)

                    else:
                        raise e

                    continue


                    # lines = rules_txt.split("\n")
                    #
                    # original_idx = int(e.message.split("(")[1].split(")")[0])
                    # idx = original_idx
                    # while idx != -1:
                    #     idx -= 1
                    #     line = lines[idx]
                    #
                    #     parts = line.split("rule ", 1)
                    #     if len(parts) < 2:
                    #         continue
                    #
                    #     if parts[0] in ('', 'global ', 'global private ', 'private '):
                    #         offending_rule = parts[1].split(":")[0].replace(" ", "").replace("{", "")
                    #         error_message = "Yara rule '{0}' could not be loaded because of an error at line {1} [{2}]." \
                    #             .format(offending_rule, original_idx - idx, e.message.split(": ")[1])
                    #         self.log.error("{}. Marking rule as INVALID.".format(error_message))
                    #
                    #         # If datastore passed, mark the signature as INVALID in database
                    #         if datastore:
                    #             try:
                    #                 # Get the offending sig ID
                    #                 update_client = Client(self.signature_url, auth=(self.signature_user, self.signature_pass))
                    #                 sig_query = "name:{} AND meta.al_status:(DEPLOYED OR NOISY)".format(offending_rule)
                    #                 for sig in update_client.search.stream.signature(sig_query):
                    #                     sigsid = sig['_yz_rk']
                    #                     print sigsid
                    #                     # Change status to INVALID in Riak and append error message to comments
                    #                     sigdata = datastore.get_signature(sigsid)
                    #                     # Check this in case another worker already marked rule
                    #                     if sigdata['meta']['al_status'] == 'INVALID':
                    #                         continue
                    #                     sigdata['meta']['al_status'] = 'INVALID'
                    #                     today = datetime.date.today().isoformat()
                    #                     sigdata['meta']['al_state_change_date'] = today
                    #                     sigdata['meta']['al_state_change_user'] = self.signature_user
                    #                     sigdata['comments'].append("AL ERROR MSG:{}".format(error_message))
                    #                     ds.save_signature(sigsid, sigdata)
                    #             except Exception as e:
                    #                 self.log.warning(e)

            finally:
                if tmp_dir:
                    shutil.rmtree(tmp_dir)
                return rules_txt

from assemblyline.common.yara.YaraParser import YaraParser
from assemblyline.common.yara.yara_importer import YaraImporter
from assemblyline.common.yara.YaraValidator import YaraValidator
