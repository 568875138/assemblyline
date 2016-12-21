def make_vm_dict(name, ram_gb, vcpus, revert_every, virtual_disk_url,
                 os_type, os_variant, num_workers=1):  # pylint: disable=R0913
    return {
        'num_workers': num_workers,
        'cfg': {
            'enabled': True,
            'name': name,
            'os_type': os_type,
            'os_variant': os_variant,
            'ram': ram_gb,
            'revert_every': revert_every,
            'vcpus': vcpus,
            'virtual_disk_url': virtual_disk_url,
        }
    }


DEFAULT_SEED = {
    'auth': {
        'internal': {
            'enabled': True,
            'failure_ttl': 60,
            'max_failures': 5,
            'strict_requirements': True,
            'users': {
                'user': {
                    'uname': 'user',
                    'name': 'Test User',
                    'password': 'changeme',
                    'groups': ['ADMIN', 'USERS'],
                    'is_admin': True,
                    'classification': 'UNRESTRICTED',
                },
            },
        },
        'login_method': 'assemblyline.ui.site_specific.internal_authenticator',
    },

    'core': {
        'nodes': ['localhost'],
        'alerter': {
            'create_alert': 'assemblyline.al.common.alerting.create_alert',
            "constant_alert_fields": ["event_id", "filename", "md5", "sha1", "sha256", "size", "ts"],
            "default_group_field": "md5",
            "filtering_group_fields": ["filename", "status"],
            'metadata_fields': {},
            'metadata_aliases': {},
            "non_filtering_group_fields": ["md5", "sha1", "sha256"],
            'shards': 2
        },
        'dispatcher': {
            'max': {
                'depth': 5,
                'files': 512,
                'inflight': 1000,
                'retries': 1,
            },
            'shards': 2,
            'timeouts': {
                'child': 60,
                'watch_queue': 86400,
            }
        },
        'expiry': {
            'journal': {
                'directory': '/opt/al/var/expiry',
                'ttl': 15,
            },
            'workers': 10,
            'delete_storage': True
        },
        "metricsd": {
            "extra_metrics": {}
        },
        'middleman': {
            'classification': 'UNRESTRICTED',
            'default_prefix': 'Bulk',
            'dropper_threads': 2,
            'expire_after': 15 * 24 * 60 * 60,
            'incomplete_expire_after': 60 * 60,
            'incomplete_stale_after': 30 * 60,
            'ingester_threads': 8,
            'max_extracted': 100,
            'max_supplementary': 100,
            'max_value_size': 4096,
            'shards': 2,
            'stale_after': 1 * 24 * 60 * 60,
            'submitter_threads': 4,
            'user': 'user',
        },
        'redis': {
            'nonpersistent': {
                'db': 6,
                'host': 'localhost',
                'port': 6379,
            },
            'persistent': {
                'db': 5,
                'host': 'localhost',
                'port': 6380,
            },
        },
        'bulk': {
            'compute_notice_field': 'assemblyline.common.null.compute_notice_field',
            'get_whitelist_verdict': 'assemblyline.al.common.signaturing.drop',
            'is_low_priority': 'assemblyline.common.null.is_low_priority',
            'whitelist': 'assemblyline.common.null.whitelist',
        },

    },

    'datasources': {
        'Alert': {
            'classpath': 'assemblyline.al.datasource.alert.Alert',
            'config': {}
        },
        'Beaver': {
            'classpath': 'assemblyline.al.datasource.beaver.Beaver',
            'config': 'services.master_list.Beaver.config'
        },
        'CFMD': {
            'classpath': 'assemblyline.al.datasource.cfmd.CFMD',
            'config': 'services.master_list.CFMD.config'
        },
        'NSRL': {
            'classpath': 'assemblyline.al.datasource.nsrl.NSRL',
            'config': 'services.master_list.NSRL.config'
        },
        'AL': {
            'classpath': 'assemblyline.al.datasource.al.AL',
            'config': {}
        }
    },

    'datastore': {
        'hosts': ['localhost'],
        'port': 8087,
        'solr_port': 8093,
        'stream_port': 8098,
        'default_timeout': 60,
        'riak': {
            'nodes': ['localhost'],
            'ring_size': 128,
            'nvals': {
                'low': 1,
                'med': 2,
                'high': 3
            },
            'solr': {
                'heap_min_gb': 1,
                'heap_max_gb': 4,
                'gc': '-XX:+UseConcMarkSweepGC -XX:CMSInitiatingOccupancyFraction=80',
            },
            'tweaks': {
                '10gnic': False,
                'disableswap': True,
                'jetty': False,
                'fs': True,
                'net': True,
                'noop_scheduler': True,
                'tuned_solr_configs': True,
            },
        },
    },

    'filestore': {
        'ftp_password': 'Ch@ang3thisPassword',  # The FTP user password
        'ftp_root': '/opt/al/var',
        'ftp_user': 'ssftp',
        'ftp_ip_restriction': None,
        'support_urls': ['ftp://alftp:Ch@ang3thisPassword@localhost/opt/al/var/support'],
        'urls': ['ftp://alftp:Ch@ang3thisPassword@localhost/opt/al/var/storage'],
    },

    'logging': {
        'directory': '/opt/al/var/log',
        'log_to_console': True,
        'log_to_file': True,
        'log_to_syslog': False,
        'logserver': {
            'node': None,
            'kibana': {
                'extra_viz': [],
                'extra_indices': [],
                'url': '',
                'dashboards': [
                    "AL-Logs",
                    "AL-Metrics",
                    "Riak-Cluster-Health",
                    "SOLR-Shard-Statistics",
                    "UI-Audit-Logs"
                ],
                'password': 'changeme',
            },
            'elasticsearch': {
                'heap_size': 2,
                'index_ttl': {
                    'audit': 30,
                    'riak': 15,
                    'logs': 7,
                    'solr': 15,
                    'al_metrics': 30,
                    'system_metrics': 7,
                }
            },
            'ssl': {
                'crt': None,
                'key': None
            }
        },
    },

    'monitoring': {
        'harddrive': True
    },

    'services': {
        'categories': [
            'Antivirus',
            'Extraction',
            'Filtering',
            'Networking',
            'Static Analysis',
            'System'
        ],
        'flex_blacklist': ['Sync'],
        'limits': {
            'max_extracted': 500,
            'max_supplementary': 500,
        },
        'stages': [
            'SETUP', 'FILTER', 'EXTRACT', 'CORE', 'SECONDARY', 'POST', 'TEARDOWN'
        ],
        'system_category': 'System',
        'timeouts': {
            'default': 60,
        },
        'master_list': {
            'APKaye': {
                'classpath': 'assemblyline.al.service.apkaye.APKaye',
                'config': {},
                'install_by_default': True
            },
            'Avg': {
                'classpath': 'assemblyline.al.service.avg.Avg',
                'config': {},
                'install_by_default': False
            },
            'Beaver': {
                'classpath': 'assemblyline.al.service.beaver.Beaver',
                'config': {},
                'install_by_default': True
            },
            'BitDefender': {
                'classpath': 'assemblyline.al.service.bitdefender.BitDefender',
                'config': {},
                'install_by_default': False
            },
            'CFMD': {
                'classpath': 'assemblyline.al.service.cfmd.CFMD',
                'config': {},
                'install_by_default': True
            },
            'Characterize': {
                'classpath': 'assemblyline.al.service.characterize.Characterize',
                'config': {},
                'install_by_default': True
            },
            'Cleaver': {
                'classpath': 'assemblyline.al.service.cleaver.Cleaver',
                'config': {},
                'install_by_default': True
            },
            'ConfigDecoder': {
                'classpath': 'assemblyline.al.service.configdecoder.ConfigDecoder',
                'config': {},
                'install_by_default': True
            },
            'Espresso': {
                'classpath': 'assemblyline.al.service.espresso.Espresso',
                'config': {},
                'install_by_default': True
            },
            'Extract': {
                'classpath': 'assemblyline.al.service.extract.Extract',
                'config': {},
                'install_by_default': True
            },
            'FrankenStrings': {
                'classpath': 'assemblyline.al.service.frankenstrings.FrankenStrings',
                'config': {},
                'install_by_default': True
            },
            'FSecure': {
                'classpath': 'assemblyline.al.service.fsecure.FSecure',
                'config': {},
                'install_by_default': True
            },
            'KasperskyIcap': {
                'classpath': 'assemblyline.al.service.kaspersky.KasperskyIcap',
                'config': {},
                'install_by_default': True
            },
            'McAfee': {
                'classpath': 'assemblyline.al.service.mcafee.McAfee',
                'config': {},
                'install_by_default': False
            },
            'MetaPeek': {
                'classpath': 'assemblyline.al.service.metapeek.MetaPeek',
                'config': {},
                'install_by_default': True
            },
            'MetaDefender': {
                'classpath': 'assemblyline.al.service.metadefender.MetaDefender',
                'config': {},
                'install_by_default': True
            },
            'NSRL': {
                'classpath': 'assemblyline.al.service.nsrl.NSRL',
                'config': {},
                'install_by_default': True
            },
            'Oletools': {
                'classpath': 'assemblyline.al.service.oletools_al.Oletools',
                'config': {},
                'install_by_default': True
            },
            'PDFId': {
                'classpath': 'assemblyline.al.service.pdfid.PDFId',
                'config': {},
                'install_by_default': True
            },
            'PeePDF': {
                'classpath': 'assemblyline.al.service.peepdf_al.PeePDF',
                'config': {},
                'install_by_default': True
            },
            'PEFile': {
                'classpath': 'assemblyline.al.service.pefile.PEFile',
                'config': {},
                'install_by_default': True
            },
            'SigCheck': {
                'classpath': 'assemblyline.al.service.sigcheck.SigCheck',
                'config': {},
                'install_by_default': False
            },
            'Suricata': {
                'classpath': 'assemblyline.al.service.suricata.Suricata',
                'config': {},
                'install_by_default': True
            },            
            'Swiffer': {
                'classpath': 'assemblyline.al.service.swiffer.Swiffer',
                'config': {},
                'install_by_default': True
            },
            'Symantec': {
                'classpath': 'assemblyline.al.service.symantec.Symantec',
                'config': {},
                'install_by_default': True
            },
            'Sync': {
                'classpath': 'assemblyline.al.service.sync.Sync',
                'config': {},
                'install_by_default': True
            },
            'TagCheck': {
                "classpath": "assemblyline.al.service.tagcheck.TagCheck",
                "config": {},
                'install_by_default': True
            },
            'TorrentSlicer': {
                "classpath": "assemblyline.al.service.torrentslicer.TorrentSlicer",
                "config": {},
                'install_by_default': True
            },
            'Unpacker': {
                'classpath': 'assemblyline.al.service.unpacker.Unpacker',
                'config': {},
                'install_by_default': True
            },
            'VirusTotalDynamic': {
                "classpath": "assemblyline.al.service.virustotal_dynamic.VirusTotalDynamic",
                "config": {},
                'install_by_default': True
            },
            'VirusTotalStatic': {
                "classpath": "assemblyline.al.service.virustotal_static.VirusTotalStatic",
                "config": {},
                'install_by_default': True
            },
            'Yara': {
                'classpath': 'assemblyline.al.service.yara.Yara',
                'config': {},
                'install_by_default': True
            },
        },
    },

    'statistics': {
        'submission_meta_fields': [
            'submission.submitter'
        ],
        'alert_statistics_fields': [
            'filename',
            'md5',
            'owner',
            'al_attrib',
            'al_av',
            'al_domain',
            'al_ip',
            'summary',
            'yara'
        ]
    },

    'submissions': {
        'decode_file': 'assemblyline.al.common.codec.decode_file',
        'max': {
            'priority': 10000,
            'size': 104857600,
        },
        'password': 'al_pass',
        'ttl': 15,  # Days.
        'url': "https://localhost:443",
        'user': 'al',
        'working_dir': '/opt/al/tmp/submission',
    },

    'system': {
        'classification': {
            'engine': 'assemblyline.al.common.classification.Classification',
            'definition': {
                "levels": [
                    {
                        "name": "UNRESTRICTED",
                        "lvl": 100,
                        "short_name": "U",
                        "aliases": [],
                        "description": "Default UNRESTRICTED classification.",
                        "css": {
                            "banner": "alert-default",
                            "label": "label-default",
                            "text": "text-muted"
                        }
                    },
                    {
                        "name": "RESTRICTED",
                        "lvl": 200,
                        "short_name": "R",
                        "aliases": [],
                        "description": "Default RESTRICTED classification.",
                        "css": {
                            "banner": "alert-danger",
                            "label": "label-danger",
                            "text": "text-danger"
                        }
                    },

                ],
                "required": [],
                "groups": [],
                "subgroups": [],
                "unrestricted": "U",
                "restricted": "R",
                "enforce": False
            }
        },
        'constants': 'assemblyline.common.constants',
        'country_code_map': 'assemblyline.common.null.CountryCodeMap',
        'load_config_from_riak': True,
        'name': 'default',
        'organisation': 'ACME',
        'password': None,
        'repositories': {
            'assemblyline': {
                'url': 'http://localhost/git/assemblyline',
                'branch': 'master'
            }
        },
        'root': '/opt/al',
        'update_interval': 5,
        'use_proxy': True,
        'user': 'al',  # The system (linux) user AL runs as.
        'yara_importer': "assemblyline.common.yara.YaraImporter",
        'yara_parser': 'assemblyline.common.yara.YaraParser',
    },

    'ui': {
        'allow_raw_downloads': True,
        'allowed_checkout_range': "0.0.0.0/0",
        'audit': True,
        'context': 'assemblyline.ui.site_specific.context',
        'debug': False,
        'download_encoding': 'cart',
        'email': None,
        'enforce_quota': False,
        'fqdn': 'assemblyline.localhost',  # import if you are using SSL/certs
        'install_path': '/opt/al/pkg',
        'secret_key': '<put your own key here!>',
        'ssl': {
            'enabled': True,
            'certs': {
                'autogen': True,  # autogenerate self signed certs
                'ca': None,
                'crl': None,
                'crt': None,
                'key': None
            }
        },
        'tos': None,
        'tos_lockout': False
    },

    'workers': {
        'default_profile': 'al-worker-default',
        'install_kvm': True,
        'nodes': ['localhost'],
        'proxy_redis': True,
        'virtualmachines': {
            'disk_root': '/opt/al/vmm/disks',
            'use_parent_as_datastore': False,
            'use_parent_as_queue': False,
            'master_list': {
                'BitDefender': make_vm_dict('BitDefender', 2048, 2, 43200,
                                            "multiav.001.qcow2", 'linux', 'ubuntuprecise', 4),
                'McAfee': make_vm_dict('McAfee', 2048, 2, 86400,
                                       "multiav.001.qcow2", 'linux', 'ubuntuprecise', 3),
            }

        },
    },

    'installation': {
        'docker': {
            'apt_repo_info': 'deb https://apt.dockerproject.org/repo ubuntu-trusty main',
            'apt_repo_key_url': 'https://get.docker.com/gpg',
        },
        'hooks': {
            'ui_pre': [],
            'riak_pre': [],
            'core_pre': [],
        },
        'external_packages': {
            'assemblyline': {
                'transport': 's3',
                'args': {
                    'base': '/opt/al/var/support',
                    'accesskey': 'AKIAIIESFCKMSXUP6KWQ',
                    'secretkey': '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',
                    's3_bucket': 'assemblyline-support',
                    'aws_region': 'us-east-1'
                }
            }
        },
        # global apt or pip packages to install on every node that are not really
        # dependencies but are useful to have.
        'supplementary_packages': {
            'apt': [
                'iotop',
                'sysstat',
                'byobu',
            ],
            'pip': [
                'ipython'
            ],
        },
        'pip_index_url': ''
    },

    # any site specifc / custom config can be stored in this dictionary
    # as long as it is json serializable
    'sitespecific': {},
}


# noinspection PyPep8Naming
def DefaultSeed():
    return DEFAULT_SEED.copy()


def dump_to_stdout(seed):
    import json
    print(json.dumps(seed, indent=4))


if __name__ == '__main__':
    dump_to_stdout(DefaultSeed())
