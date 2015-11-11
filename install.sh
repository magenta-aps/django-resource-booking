#!/usr/bin/env bash

set -e

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
VE_DIR='python-env'
VE="${DIR}/${VE_DIR}"

# Install system dependencies
echo '******************************'
echo 'Installing system dependencies'
echo '******************************'


SYSTEM_PACKAGES=( $(cat "${DIR}/docs/SYSTEM_DEPENDENCIES") )

for pkg in "${SYSTEM_PACKAGES[@]}"
do
    if [ $(dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -c "ok installed") -eq 0 ]
    then
        sudo apt-get -y install $pkg # > ${DIR}/install.log
    fi
done


# Install virtualenv
echo '******************************'
echo 'Installing virtual environment'
echo '******************************'

if [ ! -d "$VE" ]
then
    virtualenv "$VE"
fi

if [ -z $VIRTUAL_ENV ]
then
    source "$VE/bin/activate"
fi

# Install Python package, including dependencies
echo '******************************************'
echo 'Installing Python package and dependencies'
echo '******************************************'

python "$DIR/setup.py" develop # &>>  ${DIR}/install.log


echo ''
echo '**********************'
echo 'Installation complete!'
echo '**********************'
echo ''
echo 'To get started:'
echo ''
echo 'source python-env/bin/activate'
echo ''
echo 'Initiate DB with:'
echo ''
echo 'python manage.py migrate'
echo ''
echo 'For testing etc.:'
echo ''
echo 'python manage.py runserver|test|shell'
echo ''
echo ''
echo 'Check "install.log" for details about the installation process'

