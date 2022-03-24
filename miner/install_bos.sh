# installs BraiinsOs onto a miner
#   source documentation: 
#   https://docs.braiins.com/os/20.04/open-source-en/Setup/2_advanced.html#preparing-the-environment

# BraiinsOs image to URI to download
BRAIINS_IMAGE_URI=https://feeds.braiins-os.org/20.04/braiins-os_am1-s9_ssh_2020-04-30-0-259943b5.tar.gz



if [[ $# -eq 0 ]] ; then
    echo '  ! missing miner IPv4 Address!'
    echo 'Usage: ./install_bos.sh [MINER_IP_ADDRESS]'
    exit 0
fi
EXTRACT_DIR=$(echo $BRAIINS_IMAGE_URI | grep -Eo '([0-9]+\.[0-9]+)/braiins([a-z]|[A-Z]|-|_|[0-9])+' | grep -Eo 'braiins.*')

# NOTE
# Make sure your package manager/brew is up to date, and you have the following:
# python3, python3-virtualenv, virtualenv
wget -c $BRAIINS_IMAGE_URI -O - | tar -xz
cd ./$EXTRACT_DIR

if [ ! -f .braiins_venv ]; then
    echo "  ! no python virtual environment for BraiinsOs found, creating one now"
    virtualenv --python=/usr/bin/python3 .braiins_venv
fi

source .braiins_venv/bin/activate
python3 -m pip install -r requirements.txt

# NOTE 
# default password when prompted is 'admin'
python3 upgrade2bos.py $1
