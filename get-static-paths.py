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
    sandbox_mo_dir.logout()

    # write static paths to a CSV file
    create_spath_csv_file(static_paths, "static_paths.csv", "w")


def aci_login(apic, username, password):
    """
    Create and return an ACI MoDirectery session object.

    Args:
        apic (str): FQDN or IP address of the APIC
        username (str): APIC username
        password (str): APIC password

    Returns:
        obj: MoDirectory login session object
    """
    # create session
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    session = LoginSession(f"https://{apic}", username, password)
    mo_dir = MoDirectory(session)

    # login and return object
    mo_dir.login()
    return mo_dir


def get_port_channels(mo_dir):
    """
    Return a dict of port channel dicts.

    Args:
        mo_dir (obj): ACI MoDirectory session object

    Returns:
        dict: Dict of port channel dicts whose outer keys are the port
        selector names and inner keys are ifp, port_sel_name, from_port,
        and to_port.
    """
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
    """
    Return a list of dicts of static path data.

    Args:
        mo_dir (obj): ACI MoDirectory session object
        port_channels (dict): Dict of port channel dicts

    Returns:
        list: List of static path binding data dicts whose keys are epg, vlan,
        mode, node, interface, and port-channel.
    """
    # create empty list of static path bindings
    static_paths = []

    # get all static paths
    paths = mo_dir.lookupByClass("fvRsPathAtt")

    # iterate over paths and get epg, vlan encapsulation, mode, node,
    # and interface as dicts.
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

        # add path data to static_paths list. If there's a "/" in the interface
        # name, add it immediately. Else, look up the port selector in the list
        # of port channels and add the physical interfaces to the list.
        if "/" in path_data["intf"]:
            path_data["port-channel"] = "none"
            static_paths.append(path_data)
        else:
            physical_paths = get_path_interfaces(path_data, port_channels)
            for path in physical_paths:
                static_paths.append(path)

    return static_paths


def get_path_interfaces(po_path_data, port_channels):
    """
    Return a list of dicts of static path data.

    Args:
        po_path_data (dict): Dict of static path binding data whose interface
            is a port selector name rather than a physical interface.
        port_channels (dict): Dict of port channel dicts

    Returns:
        list: List of indidivual physical interface static path binding data
        for the port channel provided in po_path_data.
    """
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
                    "port-channel": port_channels[po_path_data["intf"]][
                        "port_sel_name"
                    ],
                }
            )
    # if vPC...
    else:
        # This will fail if there's no port selector for the spath
        try:
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"][:3],
                    "intf": f"eth1/{port_channels[po_path_data['intf']]['from_port']}",
                    "port-channel": port_channels[po_path_data["intf"]][
                        "port_sel_name"
                    ],
                }
            )
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"][-3:],
                    "intf": f"eth1/{port_channels[po_path_data['intf']]['from_port']}",
                    "port-channel": port_channels[po_path_data["intf"]][
                        "port_sel_name"
                    ],
                }
            )
        except KeyError:
            # If there's a static path without a corresponding port selector,
            # a lookup will result in a key error in the port_channels dict.
            print("This spath is bogus:", po_path_data)

    return physical_static_paths


def create_spath_csv_file(static_paths, file_name, mode):
    """
    Create a CSV file of static path data or append to an existing file.

    Args:
        static_paths (list): List of static path dicts whose keys are epg,
            vlan, mode, node, interface, and port-channel.
        file_name (str): Name of file to create or append to.
        mode (str): Mode for opening the file.
    """
    with open(file_name, mode, newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "epg",
                "VLAN",
                "mode",
                "node",
                "interface",
                "port-channel",
            ],
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
                    "port-channel": path["port-channel"],
                }
            )


if __name__ == "__main__":
    main()
