#!/usr/bin/env bash

set -e

DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
VE_DIR='python-env'
VE="${DIR}/${VE_DIR}"

# Install system dependencies

SYSTEM_PACKAGES=$(cat "${DIR}/docs/SYSTEM_DEPENDENCIES")

for pkg in "${SYSTEM_PACKAGES[@]}"
do
    if [ $(dpkg-query -W -f='${Status}' "$pkg" 2>/dev/null | grep -c "ok installed") -eq 0 ]
    then
        sudo apt-get -y install $pkg
    fi
done


# Now install Python dependencies
if [ ! -d "$VE" ]
then
    virtualenv "$VE"
fi

if [ -z $VIRTUAL_ENV ]
then
    source "$VE/bin/activate"
fi


#for pkg in $(cat ${DIR}/docs/PYTHON_DEPENDENCIES)
#do
#    pip install $pkg
#done

python "$DIR/setup.py" develop
