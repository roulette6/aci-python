from cobra.mit.session import LoginSession
from cobra.mit.access import MoDirectory
from getpass import getpass
import json
import re
import urllib3


def main():
    # log in
    sandbox_mo_dir = aci_login("aci.vm.jm", "admin", "1234QWer")

    # get port selector dict of dicts. outer keys are port_selector names and
    # inner keys are ifp, port_selector_name from_port, to_port
    port_selectors = get_port_selectors(sandbox_mo_dir)

    # list of dicts whose keys are epg, encapsulation, mode, node, interface
    static_paths, bogus_static_paths = get_static_paths(sandbox_mo_dir, port_selectors)
    sandbox_mo_dir.logout()

    # create list of interface vlan dicts
    interface_vlans = collate_interface_vlans(static_paths)

    # write static paths to a JSON file
    file_name = "static_paths.json"
    with open(file_name, "w", newline="", encoding="utf-8") as file:
        json.dump(interface_vlans, file, indent=2)

    # write bogus paths to a text file if they exist
    if bogus_static_paths:
        file_name = "bogus_static_paths.txt"
        with open(file_name, "w", newline="", encoding="utf-8") as file:
            for path in bogus_static_paths:
                file.write(f"{path}\n")


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


def get_port_selectors(mo_dir):
    """
    Return a dict of port selector dicts.

    Args:
        mo_dir (obj): ACI MoDirectory session object

    Returns:
        dict: Dict of port selector dicts whose outer keys are the port
        selector names and inner keys are ifp, port_sel_name, from_port,
        and to_port.
    """
    port_selectors = {}
    port_blocks = mo_dir.lookupByClass("infraPortBlk")
    for blk in port_blocks:
        port_sel_results = re.search(
            r"accportprof-(?P<ifp>.*)/hports-(?P<port_sel>.*)-typ-range",
            str(blk.dn),
        )
        ifp = port_sel_results.group("ifp")
        port_sel_name = port_sel_results.group("port_sel")
        from_port = int(blk.fromPort)
        to_port = int(blk.toPort)

        port_selectors[port_sel_name] = {
            "ifp": ifp,
            "port_sel_name": port_sel_name,
            "from_port": from_port,
            "to_port": to_port,
        }

    return port_selectors


def get_static_paths(mo_dir, port_selectors):
    """
    Return a list of dicts of static path data.

    Args:
        mo_dir (obj): ACI MoDirectory session object
        port_selectors (dict): Dict of port channel dicts

    Returns:
        list: List of static path binding data dicts whose keys are epg, vlan,
        mode, node, interface, and port-channel.
    """
    # create empty list of static path bindings with and without corresponding
    # port selectors
    static_paths = []
    bogus_paths = []

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
            # ensure the static path has a corresponding port selector by
            # that name to prevent a key error
            if path_data["intf"] in port_selectors.keys():
                po_physical_paths = get_path_interfaces(path_data, port_selectors)
                for path_data in po_physical_paths:
                    static_paths.append(path_data)
            else:
                bogus_paths.append(
                    f"EPG: {path_data['epg']} Node(s): {path_data['node']} port selector: {path_data['intf']}"
                )
    return static_paths, bogus_paths


def get_path_interfaces(po_path_data, port_selectors):
    """
    Return a list of dicts of static path data.

    Args:
        po_path_data (dict): Dict of static path binding data whose interface
            is a port selector name rather than a physical interface.
        port_selectors (dict): Dict of port channel dicts

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
            port_selectors[po_path_data["intf"]]["from_port"],
            port_selectors[po_path_data["intf"]]["to_port"] + 1,
        ):
            physical_static_paths.append(
                {
                    "epg": po_path_data["epg"],
                    "vlan": po_path_data["vlan"],
                    "mode": po_path_data["mode"],
                    "node": po_path_data["node"],
                    "intf": f"eth1/{i}",
                    "port-channel": port_selectors[po_path_data["intf"]][
                        "port_sel_name"
                    ],
                }
            )
    # if vPC...
    else:
        physical_static_paths.append(
            {
                "epg": po_path_data["epg"],
                "vlan": po_path_data["vlan"],
                "mode": po_path_data["mode"],
                "node": po_path_data["node"][:3],
                "intf": f"eth1/{port_selectors[po_path_data['intf']]['from_port']}",
                "port-channel": port_selectors[po_path_data["intf"]]["port_sel_name"],
            }
        )
        physical_static_paths.append(
            {
                "epg": po_path_data["epg"],
                "vlan": po_path_data["vlan"],
                "mode": po_path_data["mode"],
                "node": po_path_data["node"][-3:],
                "intf": f"eth1/{port_selectors[po_path_data['intf']]['from_port']}",
                "port-channel": port_selectors[po_path_data["intf"]]["port_sel_name"],
            }
        )

    return physical_static_paths


def collate_interface_vlans(static_paths):
    """
    Return a dict of interface VLAN data for netbox.

    Args:
        static_paths (list): List of static path dicts

    Returns:
        dict: Dict of interface VLAN data
    """
    interface_vlans = {}
    for path in static_paths:
        # create a dict for the interface if not exists
        sw_intf = f"{path['node']}__{path['intf']}"
        if sw_intf not in interface_vlans.keys():
            interface_vlans[sw_intf] = {
                "switch": path["node"],
                "intf": path["intf"],
                "tagged": [],
                "untagged": "",
            }
        if path["mode"] == "access":
            interface_vlans[sw_intf]["untagged"] = path["vlan"]
        elif path["mode"] == "trunk":
            interface_vlans[sw_intf]["tagged"].append(path["vlan"])

    return interface_vlans


if __name__ == "__main__":
    main()
