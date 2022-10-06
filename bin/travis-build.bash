#!/bin/bash
set -ex

echo "This is travis-build.bash..."

echo "Updating GPG keys..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
curl -L https://packagecloud.io/github/git-lfs/gpgkey | sudo apt-key add -
wget -qO - https://www.mongodb.org/static/pgp/server-3.2.asc | sudo apt-key add -

echo "Adding archive repository for postgres..."
sudo rm /etc/apt/sources.list.d/pgdg*
echo "deb https://apt-archive.postgresql.org/pub/repos/apt trusty-pgdg-archive main" | sudo tee -a /etc/apt/sources.list
echo "deb-src https://apt-archive.postgresql.org/pub/repos/apt trusty-pgdg-archive main" | sudo tee -a /etc/apt/sources.list

echo "Removing old repository for cassandra..."
sudo rm /etc/apt/sources.list.d/cassandra*

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
if [ $CKANVERSION == 'master' ]
then
    echo "CKAN version: master"
else
    CKAN_TAG=$(git tag | grep ^ckan-$CKANVERSION | sort --version-sort | tail -n 1)
    git checkout $CKAN_TAG
    echo "CKAN version: ${CKAN_TAG#ckan-}"
fi

# update pip
pip install --upgrade pip

# install the recommended version of setuptools
if [ -f requirement-setuptools.txt ]
then
    echo "Updating setuptools..."
    pip install -r requirement-setuptools.txt
fi

if [ $CKANVERSION == '2.7' ]
then
    echo "Installing setuptools"
    pip install setuptools==39.0.1
fi

python setup.py develop
if [ -f requirements-py2.txt ]
then
    pip install -r requirements-py2.txt
else
    # To avoid error:
    # Error: could not determine PostgreSQL version from '10.1'
    # we need newer psycopg2 and corresponding exc name change
    sed -i -e 's/psycopg2==2.4.5/psycopg2==2.8.2/' requirements.txt
    sed -i -e 's/except sqlalchemy.exc.InternalError:/except (sqlalchemy.exc.InternalError, sqlalchemy.exc.DBAPIError):/' ckan/config/environment.py
    pip install -r requirements.txt
fi
pip install -r dev-requirements.txt
cd -

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Setting up Solr..."
# Solr is multicore for tests on ckan master, but it's easier to run tests on
# Travis single-core. See https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini
printf "NO_START=0\nJETTY_HOST=127.0.0.1\nJETTY_PORT=8983\nJAVA_HOME=$JAVA_HOME" | sudo tee /etc/default/jetty
sudo cp ckan/ckan/config/solr/schema.xml /etc/solr/conf/schema.xml
sudo service jetty restart

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "Installing ckanext-subscribe and its requirements..."
# use 'pip install -e' instead of 'python setup.py develop' because it manages
# to uninstall ckan's older version of rq, avoiding both installed and a
# conflict error when we run nosetests
pip install -e .
pip install -r dev-requirements.txt

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "travis-build.bash is done."
