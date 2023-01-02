from cobra.mit.session import LoginSession
from cobra.mit.access import MoDirectory
from getpass import getpass
import csv
import re
import urllib3


def main():
    sandbox_mo_dir = aci_login("aci.vm.jm", "admin", "1234QWer")

    # dict of dicts whose outer keys are the port channel names
    # and inner keys are ifp, from_port, to_port
    port_channels = get_port_channels(sandbox_mo_dir)

    # list of dicts whose keys are epg, encapsulation, mode, node, interface
    static_paths = get_static_paths(sandbox_mo_dir, port_channels)

    with open("static_paths.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=["epg", "VLAN", "mode", "node", "interface", "port-channel",]
        )
        writer.writeheader()
        for path in static_paths:
            writer.writerow(
                {
                    "epg": path["epg"],
                    "VLAN": path["vlan"],
                    "mode": path["mode"],
                    "node": path["node"],
                    "interface": path["intf"],
                    "port-channel": path["port-channel"]
                }
            )

    sandbox_mo_dir.logout()


def aci_login(apic, username, password):
    # TODO: write docstring
    # create session
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = LoginSession(f"https://{apic}", username, password)
    mo_dir = MoDirectory(session)

    # login
    mo_dir.login()
    return mo_dir


def get_port_channels(mo_dir):
    # TODO: write docstring
    # create list of port channels dicts for static path lookups
    # [ifp, port_sel_name, from_port, to_port]
    port_channels = {}
    port_blocks = mo_dir.lookupByClass("infraPortBlk")
    for blk in port_blocks:
        port_sel_results = re.search(
            r"accportprof-(?P<ifp>.*)/hports-(?P<port_sel>.*)-typ-range",
            str(blk.parentDn),
        )
        ifp = port_sel_results.group("ifp")
        port_sel_name = port_sel_results.group("port_sel")
        from_port = int(blk.fromPort)
        to_port = int(blk.toPort)
        # a direct port channel will have a to_port that's greater than the
        # for port, and a vPC will be in a leaf interface profile that has
        # a "_" or "ucs" in the name
        if to_port > from_port or "_" in ifp[:-4]:
            port_channels[port_sel_name] = {
                "ifp": ifp,
                "port_sel_name": port_sel_name,
                "from_port": from_port,
                "to_port": to_port,
            }

    return port_channels


def get_static_paths(mo_dir, port_channels):
    # TODO: write docstring
    # create two lists of static path bindings: one for
    # physical interfaces and one for port channels
    # [epg, encapsulation, mode, node, interface]
    static_paths = []
    paths = mo_dir.lookupByClass("fvRsPathAtt")

    for path in paths:
        path_results = re.search(
            r"epg-(?P<epg>.*?)/.*paths-(?P<node>.*)/pathep-\[(?P<intf>.*)]]",
            str(path.dn),
        )

        epg = path_results.group("epg")
        node = path_results.group("node")
        intf = path_results.group("intf")
        mode = "trunk" if "regular" in path.mode else "access"
        path_data = {
            "epg": epg,
            "vlan": path.encap[5:],
            "mode": mode,
            "node": node,
            "intf": intf,
        }

        # add path data to static_paths if there'sa "/" in the interface name,
        # which means it's a physical interface, else add to aggregate_paths
        if "/" in path_data["intf"]:
            path_data["port-channel"] = "none"
            static_paths.append(path_data)
        else:
            physical_paths = get_path_interfaces(path_data, port_channels)
            for path in physical_paths:
                static_paths.append(path)

    return static_paths


def get_path_interfaces(po_path_data, port_channels):
    # TODO: write docstring
    # look up the port channel members for each aggregate path
    # and return static path
    physical_static_paths = []
    # if direct po...
    if "-" not in po_path_data["node"]:
        for i in range(
            port_channels[po_path_data["intf"]]["from_port"],
            port_channels[po_path_data["intf"]]["to_port"] + 1,
        ):
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"],
                    "intf": f"eth1/{i}",
                    "port-channel": port_channels[po_path_data['intf']]["port_sel_name"],
                }
            )
    # if vPC...
    else:
        # this will fail if there's no port selector for the spath
        try:
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"][:3],
                    "intf": f"eth1/{port_channels[po_path_data['intf']]['from_port']}",
                    "port-channel": port_channels[po_path_data['intf']]["port_sel_name"],
                }
            )
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"][-3:],
                    "intf": f"eth1/{port_channels[po_path_data['intf']]['from_port']}",
                    "port-channel": port_channels[po_path_data['intf']]["port_sel_name"],
                }
            )
        except KeyError:
            print("This spath is bogus:", po_path_data)

    return physical_static_paths


if __name__ == "__main__":
    main()
