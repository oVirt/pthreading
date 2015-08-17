#!/bin/bash -xe
[[ -d exported-artifacts ]] \
|| mkdir -p exported-artifacts

export RELEASE="0.0.$(date -u +%Y%m%d%H%M%S).git$(git rev-parse --short HEAD)"
export VERSION="$(python -B -c 'import pthreading ; print pthreading.__version__')"

tar cvzf ../pthreading_${VERSION}.orig.tar.gz  --exclude=.git --exclude=.gitignore --exclude=.pybuild --exclude=*.pyc --exclude=*.pyo .
echo "python-pthreading_${VERSION}-${RELEASE}_all.deb python optional" >debian/files
if [ -e /etc/debian_version ] ; then
    dpkg-source -b .
    if [ ! -e /var/cache/pbuilder/base.tgz ] ; then
    sudo /usr/sbin/pbuilder create --debootstrapopts --variant=buildd --buildplace "${WORKSPACE}"
    else
    sudo /usr/sbin/pbuilder update --debootstrapopts --variant=buildd --buildplace "${WORKSPACE}"
    fi
    sudo -E /usr/sbin/pbuilder build --buildplace "${WORKSPACE}" --buildresult ../ ../*.dsc
    cp ../*.deb ../*.dsc ../*.tar.gz ../*.tar.xz exported-artifacts/
fi