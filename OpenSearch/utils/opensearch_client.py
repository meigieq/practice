from opensearchpy import OpenSearch

def get_client():
    return OpenSearch(
        hosts=[{"host": "43.200.220.6", "port": 9201}], # AWS OpenSearch
        http_auth=("admin","MYPassword1234!"),
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False
    )

