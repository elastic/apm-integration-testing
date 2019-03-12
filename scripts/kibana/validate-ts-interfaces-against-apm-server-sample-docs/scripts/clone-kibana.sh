OWNER=${1:-elastic}
BRANCH=${2:-master}

echo "Cloning Kibana: $OWNER:$BRANCH"

cd ./tmp
git clone --depth 1 -b $BRANCH git@github.com:$OWNER/kibana.git
mv ./kibana/x-pack/plugins/apm/typings/es_schemas ./apm-ui-interfaces
rm -rf kibana
