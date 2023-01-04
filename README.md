# Cisco ACI Python
This repo uses ACI Cobra and ACI model to query ACI and to create objects. The wheels for these modules must be obtained from a production APIC (sandboxes don't have them).

## Getting data
__get-static-paths.py:__ This script creates a JSON file of all static path binding VLAN encapsulations assigned to physical interfaces. First, the script creates a list of static path binding dicts with the following fields.

* __epg:__ EPG name
* __VLAN:__ EPG VLAN encapsulation
* __mode:__ Mode (access/trunk)
* __node:__ Switch node ID
* __interface:__ Physical interface
* __port-channel:__ If physical interface is part of an aggreaget interface port selector, this field shows the port selector (AKA port channel) name.

The script accomplishes this by doing the following:

1. Creates a dict of all port selectors
2. Creates a list of all static path bindings
    1. If the static path is to a physical interface, it is added as is.
    2. If the static path is to a port selector, it means it's an aggregate interface. The script looks up the respective physical interfaces in the dictionary created in step 1, and then adds the static paths to the corresponding physical interfaces.

The script then iterates through the list and creates a dict of all the VLAN encapsulations assigned to each physical interface. It keeps track of unique switch-to-interface mapping by creating a key that combines the node ID and interface number. The item for this key contains the switch, intf, list of tagged VLANs (empty if an access port), and a single untagged VLAN (empty if not applicable). It then saves the dictionary to a JSON file. Below is a snippet of a JSON file generated by the script:

```json
{
  "201__eth1/5": {
    "switch": "201",
    "intf": "eth1/5",
    "tagged": [],
    "untagged": "666"
  },
  "201__eth1/3": {
    "switch": "201",
    "intf": "eth1/3",
    "tagged": [
      "666",
      "677"
    ],
    "untagged": ""
  },
  "201__eth1/1": {
    "switch": "201",
    "intf": "eth1/1",
    "tagged": [
      "666",
      "677",
      "688"
    ],
    "untagged": ""
  },
  "202__eth1/7": {
    "switch": "202",
    "intf": "eth1/7",
    "tagged": [],
    "untagged": "688"
  }
}
```
