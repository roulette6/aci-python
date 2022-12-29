from cobra.mit.session import LoginSession
from cobra.mit.access import MoDirectory
import urllib3
import re

# create session
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
apic, username, pw = ["https://aci.vm.jm", "admin", "1234QWer"]
session = LoginSession(apic, username, pw)
mo_dir = MoDirectory(session)

# login
mo_dir.login()

# create list of port channels dicts for static path lookups
# [ifp, port_sel_name, from_port, to_port]
port_channels = {}
port_blocks = mo_dir.lookupByClass("infraPortBlk")
for blk in port_blocks:
    port_sel_results = re.search(
        r"accportprof-(?P<ifp>.*)/hports-(?P<port_sel>.*)-typ-range", str(blk.parentDn)
    )
    ifp = port_sel_results.group("ifp")
    port_sel_name = port_sel_results.group("port_sel")
    from_port = int(blk.fromPort)
    to_port = int(blk.toPort)
    if from_port != to_port or ("201_202" in ifp):
        port_channels[port_sel_name] = [ifp, from_port, to_port]

# create two lists of static path bindings: one for
# physical interfaces and one for port channels
# [epg, encapsulation, mode, node, interface]
eth_paths = []
aggregate_paths = []
paths = mo_dir.lookupByClass("fvRsPathAtt")

for path in paths:
    path_dn = str(path.dn)
    path_results = re.search(
        r"epg-(?P<epg>\w+)/.*paths-(?P<node>.*)/pathep-\[(?P<intf>.*)]]", path_dn
    )

    epg = path_results.group("epg")
    node = path_results.group("node")
    intf = path_results.group("intf")
    mode = "trunk" if "regular" in path.mode else "access"
    path_data = [epg, path.encap[5:], mode, node, intf]

    # add path data to eth_paths if there'sa "/" in the interface name,
    # which means it's a physical interface, else add to aggregate_paths
    eth_paths.append(path_data) if "/" in path_data[4] else aggregate_paths.append(
        path_data
    )

# look up the port channel members for each aggregate path
# and add them to eth_paths
for path in aggregate_paths:
    # if direct po...
    if "-" not in path[3]:
        for i in range(port_channels[path[4]][1], port_channels[path[4]][2] + 1):
            eth_paths.append([path[0], path[1], path[2], path[3], f"eth1/{i}"])
    # if vPC...
    else:
        eth_paths.append(
            [
                path[0],
                path[1],
                path[2],
                path[3][:3],
                f"eth1/{port_channels[path[4]][1]}",
            ]
        )
        eth_paths.append(
            [
                path[0],
                path[1],
                path[2],
                path[3][-3:],
                f"eth1/{port_channels[path[4]][1]}",
            ]
        )


for path in eth_paths:
    print(path)

mo_dir.logout()
