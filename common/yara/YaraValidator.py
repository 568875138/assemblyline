import datetime
import logging
import re
import subprocess
from assemblyline_client import Client


class YaraValidator(object):

    def __init__(self, rulefile, externals=None, logger=None):
        if not logger:
            from assemblyline.al.common import log as al_log
            al_log.init_logging('YaraValidator')
            logger = logging.getLogger('assemblyline.YaraValidator')
            logger.setLevel(logging.WARNING)
        if not externals:
            externals = {'dummy': ''}
        self.log = logger
        self.rulefile = rulefile
        self.externals = externals
        self.rulestart = re.compile(r'^(?:global )?(?:private )?(?:private )?rule ', re.MULTILINE)
        self.rulename = re.compile('rule ([^{^:]+)')

    def clean(self, eline, message):

        with open(self.rulefile, 'r') as f:
            f_lines = f.readlines()
        # List will start at 0 not 1
        error_line = eline - 1

        # First loop to find start of rule
        start_idx = 0
        while True:
            find_start = error_line - start_idx
            if find_start == -1:
                raise Exception("Yara Validator failed to find invalid rule start. "
                                "Yara Error: {0} Line: {1}" .format(message, eline))
            line = f_lines[find_start]
            if re.match(self.rulestart, line):
                # Add extra '1' so that rule starts at line 1 and not 0
                rule_error_line = error_line - find_start + 1
                rule_start = find_start - 1
                invalid_rule_name = re.search(self.rulename, line).group(1).strip()

                # Second loop to find end of rule
                end_idx = 0
                while True:
                    find_end = error_line + end_idx
                    if line > len(f_lines):
                        raise Exception("Yara Validator failed to find invalid rule end. "
                                        "Yara Error: {0} Line: {1}" .format(message, eline))
                    line = f_lines[find_end]
                    if re.match(self.rulestart, line):
                        rule_end = find_end - 1
                        # Now we have the start and end, strip from file
                        rule_file_lines = []
                        rule_file_lines.extend(f_lines[0:rule_start])
                        rule_file_lines.extend(f_lines[rule_end:])
                        with open(self.rulefile, 'w') as f:
                            f.writelines(rule_file_lines)
                        break
                    end_idx += 1
                # Send the error output to AL logs
                error_message = "Yara rule '{0}' removed from rules file because of an error at line {1} [{2}]." \
                    .format(invalid_rule_name, rule_error_line, message)
                self.log(error_message)
                break
            start_idx += 1

        return invalid_rule_name

    def paranoid_rule_check(self):
        # Run rules separately on command line to ensure there are no errors
        print_val = "--==Rules_validated++__"
        cmd = "python -c " \
              "\"import yara\n" \
              "try: " \
              "yara.compile('%s', externals=%s).match(data='');" \
              "print '%s'\n" \
              "except yara.SyntaxError as e:" \
              "print 'yara.SyntaxError.{}' .format(e)\""
        p = subprocess.Popen(cmd % (self.rulefile, self.externals, print_val), stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, shell=True, cwd="/tmp")

        stdout, stderr = p.communicate()

        if print_val not in stdout:
            if stdout.startswith('yara.SyntaxError'):
                raise Exception(stdout)
            else:
                raise Exception("YaraValidator has failed! " + stderr)

    def validate_rules(self, datastore=False):
        valid_file = False
        while not valid_file:
            try:
                self.paranoid_rule_check()
                valid_file = True
            # If something goes wrong, clean rules until valid file given
            except Exception as e:
                if e.message.startswith('yara.SyntaxError'):

                    e_line = int(e.message.split('):', 1)[0].split("(", -1)[1])
                    e_message = e.message.split("): ", 1)[1]
                    try:
                        invalid_rule = self.clean(e_line, e_message)
                    except Exception as ve:
                        raise ve

                    # If datastore object given, change status of signature to INVALID in Riak
                    if datastore:
                        from assemblyline.al.common import forge
                        config = forge.get_config()
                        signature_url = config.services.masterlist.Yara.config.SIGNATURE_URL
                        signature_user = config.services.masterlist.Yara.config.SIGNATURE_USER
                        signature_pass = config.services.masterlist.Yara.config.SIGNATURE_PASS
                        # Get the offending sig ID
                        update_client = Client(signature_url, auth=(signature_user, signature_pass))
                        sig_query = "name:{} AND meta.al_status:(DEPLOYED OR NOISY)".format(invalid_rule)
                        # Mark and update Riak
                        store = forge.get_datastore()
                        for sig in update_client.search.stream.signature(sig_query):
                            sigsid = sig['_yz_rk']
                            sigdata = store.get_signature(sigsid)
                            # Check this in case someone already marked it as invalid
                            try:
                                if sigdata['meta']['al_status'] == 'INVALID':
                                    continue
                            except KeyError:
                                pass
                            sigdata['meta']['al_status'] = 'INVALID'
                            today = datetime.date.today().isoformat()
                            sigdata['meta']['al_state_change_date'] = today
                            sigdata['meta']['al_state_change_user'] = signature_user
                            sigdata['comments'].append("AL ERROR MSG:{}".format(e_message))
                            store.save_signature(sigsid, sigdata)

                else:
                    raise e

                continue



