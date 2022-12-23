from cobra.mit.session import LoginSession
from cobra.mit.access import MoDirectory
from cobra.mit.request import ClassQuery
import urllib3
import re
from pprint import pprint

# create session
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
apic, username, pw = ["https://aci.vm.jm", "admin", "1234QWer"]
session = LoginSession(apic, username, pw)
mo_dir = MoDirectory(session)

# login
mo_dir.login()

# get static path bindings
eth_paths = []
aggregate_paths = []
paths = mo_dir.lookupByClass("fvRsPathAtt")

for path in paths:
    path_dn = str(path.dn)
    path_results = re.search(
        r"epg-(?P<epg>\w+)/.*paths-(?P<node>\d{3}).*pathep-\[(?P<intf>.*)]]", path_dn
    )

    # NOTE: in production, direct PCs and VPCs can be distinguished
    # by their port selector name not having "eth1/\d{1,2}" in it
    epg = path_results.group("epg")
    node = path_results.group("node")
    intf = path_results.group("intf")
    mode = "trunk" if "regular" in path.mode else "access"

    path_data = [epg, path.encap[5:], mode, node, intf]
    eth_paths.append(path_data) if "/" in path_data[4] else aggregate_paths.append(
        path_data
    )
pprint(eth_paths)
pprint(aggregate_paths)

mo_dir.logout()
