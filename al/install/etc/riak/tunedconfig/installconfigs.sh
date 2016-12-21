#!/bin/sh -x

for bucket in file alert result error filescore submission
do
    cp /var/lib/riak/yz/${bucket}/conf/solrconfig.xml /var/lib/riak/yz/${bucket}/conf/solrconfig.xml.bak
    cp solrconfig.xml.${bucket} /var/lib/riak/yz/${bucket}/conf/solrconfig.xml
done

#YOK_DIR=/usr/lib/riak/lib/yokozuna-2.0.0-34-g122659d/priv/solr/etc/
#cp  ${YOK_DIR}/jetty.xml ${YOK_DIR}/jetty.xml.bak
#cp ./jetty.xml ${YOK_DIR}/jetty.xml


#IBROWSE_DIR=/usr/lib/riak/lib/ibrowse-4.0.1/priv/
#cp ${IBROWSE_DIR}/ibrowse.conf ${IBROWSE_DIR}/ibrowse.conf.bak
#cp ./ibrowse.conf ${IBROWSE_DIR}/ibrowse.conf

