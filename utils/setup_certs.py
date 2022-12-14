import sys
from create_certs import generate_cert_for_fm


# arg1 : path to fleet_config.toml
# arg2 : path to static dir

print("Will create cert files, ensure fleet_config.toml has all_server_ips")
generate_cert_for_fm(sys.argv[1], sys.argv[2])
