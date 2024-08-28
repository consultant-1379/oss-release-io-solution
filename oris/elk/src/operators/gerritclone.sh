#!/bin/sh
#
# COPYRIGHT Ericsson 2021
#
#
#
# The copyright to the computer program(s) herein is the property of
#
# Ericsson Inc. The programs may be used and/or copied only with written
#
# permission from Ericsson Inc. or in accordance with the terms and
#
# conditions stipulated in the agreement/contract under which the
#
# program(s) have been supplied.
#
#/usr/bin/git --version
/usr/bin/git/pwd
/usr/bin/git --version
/usr/bin/git/ls
[ -e oss-release-io-solution-resources ] && rm -rf oss-release-io-solution-resources
/usr/bin/git clone ssh://ossadmin@gerrit-gamma.gic.ericsson.se:29418/OSS/com.ericsson.oss.internaltools.devops/oss-release-io-solution-resources && scp -p -P 29418 ossadmin@gerrit-gamma.gic.ericsson.se:hooks/commit-msg oss-release-io-solution-resources/.git/hooks/
if [ $? == 0 ]; then
  echo "files cloned"
else
  exit 1
fi
cd oss-release-io-solution-resources

