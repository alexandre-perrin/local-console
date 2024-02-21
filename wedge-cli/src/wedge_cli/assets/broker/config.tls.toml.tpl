listener ${mqtt_port}

cafile ${ca_crt}
certfile ${server_crt}
keyfile ${server_key}

allow_anonymous false
require_certificate true
use_identity_as_username true
