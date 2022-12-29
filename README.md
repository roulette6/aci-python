# Cisco ACI Python
This repo uses ACI Cobra and ACI model to query ACI and to create objects. The wheels for these modules must be obtained from a production APIC (sandboxes don't have them).

## Getting data
__get-static-paths.py:__ This script creates a CSV of all static path bindings. __TODO: create the CSV of values in eth_paths__

* __`eth_paths`:__ List of static paths for single interfaces. This is reflected by interfaces named `eth1/\d{1,2}`.
* __`aggregate_paths`:__ List of static paths for port channels. Since static paths to port channels (both direct and vPC) show the port selector name instead of the physical interfaces, the script looks at all port selectors whose name matches the interfaces in this list and adds the physical interfaces in their port blocks to the list of `eth_paths`.

Sample data in the above lists

```python
# [epg name, encapsulation, mode, node, interface]

eth_paths = [
    ["DD_epg", "666", "access", "201", "eth1/2"],
    ["DD_epg", "666", "access", "202", "eth1/2"],
    ["Cobra_epg", "677", "access", "201", "eth1/3"],
    ["Cobra_epg", "677", "access", "202", "eth1/3"],
    ["Fox_epg", "688", "access", "201", "eth1/4"],
    ["Fox_epg", "688", "access", "202", "eth1/4"],
]

aggregate_paths = [
    ["DD_epg", "666", "trunk", "201", "eth1_1_core-fw01"],
    ["DD_epg", "666", "trunk", "201", "eth1_1_core-rt01"],
    ["Cobra_epg", "677", "trunk", "201", "eth1_1_core-fw01"],
    ["Cobra_epg", "677", "trunk", "201", "eth1_1_core-rt01"],
    ["Fox_epg", "688", "trunk", "201", "eth1_1_core-fw01"],
    ["Fox_epg", "688", "trunk", "201", "eth1_1_core-rt01"],
    ["Cobra_epg", "667", "trunk", "201", "single-sw-po"],
]
```