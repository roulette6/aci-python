# Cisco ACI Python
This repo uses ACI Cobra and ACI model to query ACI and to create objects. The wheels for these modules must be obtained from a production APIC (sandboxes don't have them).

## Getting data
__get-static-paths.py:__ Currently a work in progress. This script will create a CSV of all static path bindings. As of now, the script separates static paths into these two lists of lists:

* __`eth_paths`:__ List of static paths for single interfaces. This is reflected by interfaces named `eth1/\d{1,2}`.
* __`aggregate_paths`:__ List of static paths for port channels. Since static paths to port channels (both direct and vPC) show the port selector name instead of the physical interfaces, the script will then look at all port selectors whose name matches the interfaces in this list and get the physical interfaces in their port blocks so we can add them to the list of `eth_paths`. That functionality has not yet been added.

Sample data in the above lists

```python
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