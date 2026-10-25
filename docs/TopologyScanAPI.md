# Topology Scan REST API

The REST contract behind the network visualisation, specified in
[#2106](https://github.com/zigbeefordomoticz/Domoticz-Zigbee/issues/2106) and
consumed by [Domoticz-Zigbee-UI#167](https://github.com/zigbeefordomoticz/Domoticz-Zigbee-UI/issues/167).

Base path, as for every other endpoint: `/rest-z4d/1/`.

> `/topologie` is unchanged and stays supported. It is what the two older WebUI
> charts consume, and its payload is read positionally, so nothing may be added
> to it. `/topology-scan` is a second, richer contract beside it, not a
> replacement. Nothing in this document affects `/topologie`.

---

## 1. Endpoints

| Verb | Path | Answers |
|---|---|---|
| GET | `/topology-scan` | [list of scan summaries](#3-get-topology-scan) |
| GET | `/topology-scan/<timestamp>` | [one whole scan](#4-get-topology-scantimestamp) |
| GET | `/topology-scan/<timestamp>/nodes` | the same envelope, `nodes` only |
| GET | `/topology-scan/<timestamp>/neighbours` | the same envelope, `neighbours` only |
| GET | `/topology-scan/<timestamp>/routes` | the same envelope, `routes` only |
| DELETE | `/topology-scan` | removes every stored scan |
| DELETE | `/topology-scan/<timestamp>` | removes one stored scan |
| GET | `/zigpy-topology-raw` | [the zigpy report file, untouched](#7-get-zigpy-topology-raw) |

**Build the graph from `GET /topology-scan/<timestamp>`.** It answers nodes,
neighbours and routes in one response. Three separate calls means three round
trips and three chances to render a half-built graph; the sub-resources exist for
other tooling, not for the graph.

Starting a scan is unchanged: `GET /req-topologie`, as today.

On a zigpy installation, that scan has two halves: zigpy collects the neighbour
and route tables, then — when `ZigpyTopologyAssociatedDevices` is enabled — the
plugin collects each router's associated device list itself (§6.1.2). The whole
thing is filed as one scan under one timestamp, and `/plugin-health` reports
`"Topology": "In Progress"` for both halves, so a scan is not finished when
zigpy's half is. The second half adds a few minutes; nothing is readable through
these endpoints until it ends.

---

## 2. Concepts

### 2.1 A scan is addressed by its timestamp

Integer seconds, as a JSON **number**, everywhere — never a float, never a
string, never a JSON object key. Multiply by 1000 for a JavaScript `Date`.

`/topology-scan/<timestamp>` accepts digits only. `1791824584.1646256` is a
`400`, not a scan id.

### 2.2 `source` — which backend wrote this scan

The plugin has three topology backends. The endpoint hides which one is active,
and tells you honestly which one produced each scan:

| `source` | Backend |
|---|---|
| `zigpy` | `Classes/ZigpyTopology.py`, report file `Zigpy-Topology-XX.json` |
| `topologyv2` | `Modules/zb_tables_management.py`, tables inside the device database |
| `legacy` | `Classes/NetworkMap.py`, report file `NetworkTopology-v3-XX.json` |

`source` is a property **of the scan, not of the plugin**: do not cache "this
installation is a zigpy installation" off one scan.

**The listing holds one source at a time** — the backend the plugin is currently
running. An inactive backend is not enumerated, because it does not hold scans
so much as residue. TopologyV2 is the case that forced this: it has no report
file, so a scan has to be inferred from the distinct `Time` values left across
every device's `Neighbours`, `RoutingTable` and `AssociatedDevices` lists. Those
entries are created empty by `start_new_table_scan()` and only filled by
`finish_scan()`, are pruned per device per table rather than per scan, and are
written by code paths that are not a topology scan at all. On a zigpy setup —
where `/req-topologie` sends `ZIGPY-TOPOLOGY-SCAN` and never starts a NetworkMap
scan — enumerating them listed scans that had never been run, several with no
neighbour row in them, interleaved with the real zigpy reports.

Not listed is not gone. `GET /topology-scan/<timestamp>` still answers a scan
written by any backend, so a report on disk from a setup's previous backend
stays readable by id, and `DELETE /topology-scan` still clears every backend. It
was the enumeration that was never trustworthy, not the scan.

### 2.3 `tables` — what this scan collected

| `source` | `tables` |
|---|---|
| `zigpy` | `["neighbours", "routes"]` or `["neighbours", "routes", "associated_devices"]` |
| `topologyv2` | `["neighbours", "routes", "associated_devices"]` |
| `legacy` | `["neighbours"]` |

A table **listed but empty** means the backend asked and got nothing — that is a
finding worth showing. A table **not listed** means this scan does not carry it
at all — grey the control out instead of showing an empty result.

Concretely: when `"routes"` is absent from `tables`, disable the
neighbours/routes filter. When `"associated_devices"` is absent, every node's
`associated_devices` is `null`, which is not the same statement as `[]`.

**Read `tables` per scan, not per source.** `zigpy` is the one backend whose
answer varies between two scans of the same installation: zigpy itself collects
only neighbours and routes, and the associated device list is collected by the
plugin afterwards, under the `ZigpyTopologyAssociatedDevices` setting (see
§6.1.2). A scan stored before that collection existed, one run with the setting
off, and one whose collection was cut short by a radio restart all come back
without the table. The other two backends fill all of their tables on every
scan.

### 2.4 `null` means "no value", not zero

A backend that genuinely has no reading sends `null`, never `0` or `""`. Show
"unknown"; do not render a null as a measurement. `0` **is** a real reading — a
neighbour with `"lqi": 0` was heard at LQI 0, and a real report contains them.

### 2.5 Vocabulary

One vocabulary, whatever the backend. The legacy and TopologyV2 spellings
(`"Former Child"`, `"End Device"`, `"Rx-On"`, `"Active (0)"`) are translated by
the plugin, and the legacy raw hex LQI is converted, so the UI never sees them.

| Field | Values |
|---|---|
| `relationship` | `parent` · `child` · `sibling` · `none_of_above` · `previous_child` · `unknown` |
| `device_type`, `logical_type` | `coordinator` · `router` · `end_device` · `unknown` |
| `rx_on_when_idle`, `permit_joining` | `on` · `off` · `unknown` |
| route `status` | `active` · `discovery_underway` · `discovery_failed` · `inactive` · `validation_underway` · `unknown` |
| `scan_status` | `ok` · `timeout` · `not_supported` · `not_scanned` |

`unknown` is common and is not a plugin failure: some radios answer
`permit_joining` with "unknown" for every neighbour of every scan. Treat these as
closed sets, but fall back gracefully on a value you do not recognise rather than
dropping the record.

---

## 3. GET `/topology-scan`

The report list. Enough to label each entry without fetching it.

```json
[
  {
    "timestamp": 1791824584,
    "source": "zigpy",
    "tables": ["neighbours", "routes"],
    "nodes": 32,
    "neighbours": 74,
    "routes": 21,
    "scan": {"requested": 32, "answered": 4, "timeout": 0, "not_scanned": 28}
  }
]
```

| Field | |
|---|---|
| `timestamp` | integer seconds; the scan id |
| `source` | §2.2 |
| `tables` | §2.3 |
| `nodes`, `neighbours`, `routes` | the length of each collection in the full scan |
| `scan` | the same object as in the full scan, §5 |

Ordered **oldest first**. `[]` when nothing is stored. A scan still being
collected is not listed; it appears once it finishes. Only the active backend's
scans are listed, so every entry carries the same `source` — see §2.2.

---

## 4. GET `/topology-scan/<timestamp>`

```json
{
  "timestamp": 1791824584,
  "source": "zigpy",
  "coordinator": "0000",
  "tables": ["neighbours", "routes"],
  "scan": {"requested": 32, "answered": 4, "timeout": 0, "not_scanned": 28},
  "nodes": [ ... ],
  "neighbours": [ ... ],
  "routes": [ ... ]
}
```

`coordinator` is the coordinator's nwkid, `"0000"`. It is there so the graph has
a root without hardcoding one.

`404` when there is no scan with that timestamp.

---

## 5. `scan` — how much of the mesh this picture covers

```json
{"requested": 32, "answered": 4, "timeout": 0, "not_scanned": 28}
```

| Field | |
|---|---|
| `requested` | nodes that could be scanned; `answered` + `timeout` + `not_scanned` |
| `answered` | reported a neighbour or a routing table |
| `timeout` | was asked and never answered |
| `not_scanned` | has a neighbour table in principle, but this scan never reached it |

A node that cannot be scanned at all (`scan_status: "not_supported"`) is **not**
counted in `requested`.

**This is worth surfacing.** The example above is real: 4 nodes out of 32
contributed to that graph. Drawing it without a warning silently misrepresents
the network. A banner along the lines of *"4 of 32 nodes answered this scan — the
picture is incomplete"* whenever `answered < requested` is the point of this
object.

All three backends distinguish `timeout` from `not_scanned`. On `zigpy` the
difference is whether the scanner listed the node at all: a node it asked and
got nothing back from is a `timeout`, a node it never asked — because it has no
node descriptor, or is not a router — is `not_scanned`.

A `timeout` on a `zigpy` scan is worth surfacing for a second reason: a node
that does not answer costs the scan roughly 40 seconds of retries, on every
scan, and zigpy only stops asking a node that *refuses* — not one that stays
silent. So `timeout` is both a gap in the picture and an ongoing cost.

---

## 6. The three collections

### 6.1 `nodes`

```json
{
  "nwkid": "1a2b",
  "ieee": "680ae2fffe7aca89",
  "name": "Repeater",
  "logical_type": "router",
  "rx_on_when_idle": "on",
  "scan_status": "ok",
  "health": "Live",
  "model": "TRADFRI Signal Repeater",
  "lqi": 196,
  "rssi": null,
  "battery": null,
  "associated_devices": null
}
```

| Field | |
|---|---|
| `nwkid` | **the node's identity.** Unique within a scan; the key to join `neighbours` and `routes` on |
| `ieee` | stable identity across rejoins and renames; `null` for a node the plugin does not know |
| `name` | **display only.** `null` when the device has no name — fall back to the `nwkid` yourself |
| `logical_type` | the node's own type, from the device database; §2.5 |
| `rx_on_when_idle` | from the device's MAC capability, else from what a neighbour reported about it |
| `scan_status` | §6.1.1 |
| `health`, `model`, `lqi`, `rssi`, `battery` | the same values `/zdevice-name` returns, for this node, **now** — not as of the scan |
| `associated_devices` | list of nwkids of this node's direct children, or `null` when this scan does not carry the table; §6.1.2 |

**Use `nwkid` as the node key and `ieee` as the stable id. Never `name`.** Two
devices can share a name, a rename breaks comparison against older reports, and
a name cannot be linked to a device page. `name` is a label to draw, nothing
more.

`nodes` lists **every device the plugin knows, plus every node the scan
mentioned** — not only nodes with links. That is deliberate:

- a router that answered nothing is visible, instead of silently absent
- a node seen only as a route destination or a next hop is present, with
  `ieee: null` and `logical_type: "unknown"`
- there is nothing left to join against `/zdevice-name`; ieee, model and health
  are already here

An isolated node with no entry in `neighbours` is therefore normal and
meaningful; `scan_status` says why.

#### 6.1.1 `scan_status`

| Value | Meaning | Suggested rendering |
|---|---|---|
| `ok` | answered this scan | normal |
| `timeout` | asked, never answered | distinct — this is a finding, not a leaf |
| `not_supported` | has no neighbour table to ask for (an end device) | normal; expected |
| `not_scanned` | scannable, but this scan did not reach it | muted or flagged |

Before this field existed, a node that timed out looked exactly like a leaf with
no neighbours. Distinguishing `timeout`/`not_scanned` from `not_supported` is the
single most useful thing the UI can do with this payload.

#### 6.1.2 `associated_devices` — the children a router declares

A node's `associated_devices` is the list of nwkids that node reported as its
own children. It is the one table that reports a **sleepy end device's parent**:
the parent answers for it, so a battery device that never answers anything is
still placed in the tree. A Lumi/Aqara sensor typically appears here and nowhere
else.

It is not a `Mgmt_*` table. It rides on the extended address response —
`NWK_addr_req` with `RequestType 0x01`, answered with `NumAssocDev`,
`StartIndex` and `NWKAddrAssocDevList` — which only a coordinator or a router is
asked for.

Reading it:

- **`null` is not `[]`.** `null` means this scan does not carry the table at all;
  check `tables` (§2.3) before offering a parent/child view. `[]` means that node
  was asked and declared no children.
- **An entry is a parent → child edge**, nothing more. There is no LQI, no
  relationship and no depth on it, unlike a `neighbours` row.
- **The nwkids are not resolved for you.** Join them against `nodes` to get an
  ieee, a name and a type; a child that is not in `nodes` is a device the plugin
  does not know.
- **A node absent from the table is not distinguishable from one that answered
  nothing.** The table is flat — `{nwkid: [children]}` — so a coordinator or
  router that was asked but timed out reads as `[]`, exactly like one with no
  children. `scan_status` answers that question for the *neighbour* request
  only. Known limitation; do not present `[]` as proof a router has no children.
- **On a zigpy scan the rows lag the neighbour rows.** The scan's `timestamp` is
  the moment zigpy's neighbour and route tables were read; the associated device
  lists are collected over the following minutes. A device that joined in between
  can appear as a child of a router whose neighbour table predates it.

### 6.2 `neighbours`

One entry per neighbour-table row, as the reporting node reported it.

```json
{
  "reporter": "0000",
  "neighbor": "cbc4",
  "relationship": "child",
  "device_type": "router",
  "lqi": 204,
  "depth": null,
  "rx_on_when_idle": "on",
  "permit_joining": "unknown"
}
```

| Field | |
|---|---|
| `reporter` | the node whose neighbour table this row came from |
| `neighbor` | the node that row is about |
| `relationship` | `neighbor`'s relationship **to** `reporter`; §2.5 |
| `device_type` | what `reporter` believes `neighbor` is — may differ from `neighbor`'s own `logical_type` |
| `lqi` | 0–255, **as measured by `reporter`** |
| `depth` | `neighbor`'s depth in the tree, or `null` when the backend did not collect it |
| `rx_on_when_idle`, `permit_joining` | as `reporter` reported them about `neighbor` |

Three things to get right:

**`reporter` is not a direction of travel.** `lqi` is read out of `reporter`'s own
neighbour table, so it is a measurement made **by** `reporter` **about**
`neighbor`. The old payload called this `Father`/`Child`, which is why the
current UI needs a footnote. A label like *"0000 hears cbc4 at 204"* needs no
footnote.

**Both directions are sent, and they are not deduplicated.** `(A,B)` and `(B,A)`
are two separate entries with two separate LQIs, because A and B usually report
different values for the same radio link. That asymmetry is diagnostically
interesting — it is often how a node that hears well but is not heard gets
spotted. If you want one line per link, collapse them in the UI, keeping both
values; if you want to show the asymmetry, it is already here. Be aware a link
may be reported from one side only.

**Nothing is filtered.** `none_of_above` and `previous_child` are present, and so
are nodes absent from the device database. The plugin used to drop all of those;
deciding what to draw is the UI's call now. A reasonable default is to draw
`parent`/`child`/`sibling` and offer the rest as a toggle.

**`depth` is unreliable in practice — do not lay a tree out with it.** Zigbee
caps the tree depth at 15, and a radio with no depth to give for a row answers
with a sentinel rather than omitting the field. A value outside 0–15 is reported
as `null`, because it is not a reading. A value of exactly `15` is passed
through, since it is legal — but a radio may well be using it as a sentinel too,
and the plugin cannot tell those apart.

What that looks like on a real ZNP scan of 48 neighbour rows:

| `depth` | rows | |
|---|---|---|
| `0`, `1`, `2` | 7 | genuine, on the parent/child rows |
| `15` | 22 | legal, almost certainly a sentinel |
| `null` | 19 | was `255` — out of range, so not reported as a reading |

The pattern follows `relationship`: this radio tracks depth for parent/child
rows and not for siblings. Treat a `depth` on a `sibling` row with suspicion.

`depth` is also `null` for every `legacy` scan, and for any `zigpy` report
written by a plugin older than this API — the value was being discarded at
collection time. So expect `null` from reports already on disk at upgrade time
and a number from scans run afterwards.

### 6.3 `routes`

One entry per routing-table row.

```json
{
  "reporter": "0000",
  "destination": "77f0",
  "next_hop": "6fc0",
  "status": "active",
  "many_to_one": false,
  "memory_constrained": false,
  "route_record_required": false
}
```

| Field | |
|---|---|
| `reporter` | the node whose routing table this row came from |
| `destination` | where the route leads |
| `next_hop` | **the node the frame is handed to next** |
| `status` | §2.5 |
| `many_to_one`, `memory_constrained`, `route_record_required` | booleans, as reported |

**`next_hop` is what makes routes worth drawing.** A yes/no route flag only
answers "is there a route". `next_hop` lets you draw the path a frame actually
takes, hop by hop, which is the question people are really asking of a mesh
diagram: *why is this device slow, and what is it going through?*

`next_hop == destination` is a direct one-hop route and is common.

`routes` is `[]` on a `legacy` scan, which has no routing table at all — check
`tables`, not the length.

Routes and neighbours are different questions about the same mesh: a link can
carry a route without being a neighbour-table row, and vice versa. A
neighbours/routes/both filter wants `tables` to know whether to offer the routes
option at all.

---

## 7. GET `/zigpy-topology-raw`

`Zigpy-Topology-XX.json` exactly as it is on disk, for diagnostics and bug
reports. Backend-specific on purpose, and **not** what the graph consumes: its
shape is an internal detail and may change without notice.

`[]` on any non-zigpy setup.

---

## 8. DELETE

| Request | |
|---|---|
| `DELETE /topology-scan/<timestamp>` | removes that one scan |
| `DELETE /topology-scan` | removes every stored scan |

```json
{"Name": "Topology scan 1791824584 removed", "sources": ["zigpy"]}
```

`sources` lists the backends the scan was removed from. It can hold more than one
entry: a single scan is sometimes written by two backends at once, and all copies
are removed, so a re-list never brings the report back.

Both deletes reach **every** backend, not only the listed one. `DELETE
/topology-scan` is the way to clear an inactive backend's leftovers, which §2.2
no longer enumerates.

`404` for an unknown timestamp. `400` when the timestamp belongs to a scan still
being collected — it cannot be deleted until it finishes.

---

## 9. Errors

| Status | When |
|---|---|
| `200 OK` | fine. An empty result is a `200` with `[]` |
| `400 BAD REQUEST` | timestamp not integer seconds, unknown sub-resource, trailing path element, deleting a running scan |
| `404 NOT FOUND` | no scan with that timestamp |
| `500 INTERNAL SERVER ERROR` | unhandled plugin-side failure |

`400` and `404` carry a JSON body with a message meant to be shown as-is:

```json
{"BE_Error": "no topology scan with timestamp 1234567890"}
```

A `500` body is plain text, as for every other endpoint.

---

## 10. Payload size

Measured end to end, raw and gzipped as the plugin sends it:

| Mesh | neighbours | routes | raw | gzip | build |
|---|---|---|---|---|---|
| real, 32 nodes (ZNP) | 74 | 21 | 24 KB | 1.7 KB | < 1 ms |
| synthetic, 59 nodes | 1250 | 225 | 255 KB | 9.2 KB | 2 ms |

Fetch the whole scan and filter client-side. The plugin gzips when the request
carries `Accept-Encoding: gzip`, which takes a large mesh to well under 10 KB, so
there is no reason to page or to split the call.

---

## 11. Suggested UI reading order

1. `GET /topology-scan` → the report picker, each entry labelled with its
   timestamp, its `source`, and a warning when `answered < requested`.
2. `GET /topology-scan/<timestamp>` → everything needed for the graph.
3. Nodes from `nodes`, keyed on `nwkid`; shape from `logical_type`; label from
   `name` falling back to `nwkid`; link to the device page via `ieee`;
   `scan_status` for the "did not answer" state.
4. Edges from `neighbours`, keyed on `(reporter, neighbor)`; colour by `lqi`;
   style by `relationship`; keep both directions, and surface the asymmetry when
   both are present.
5. Route overlay from `routes`, drawn `reporter` → `next_hop` → … →
   `destination`, offered only when `"routes"` is in `tables`.
6. `associated_devices` for a parent/child tree view, offered only when
   `"associated_devices"` is in `tables` — per scan, not per source (§2.3). It is
   the only view that places a sleepy end device under its parent (§6.1.2).

Do not join anything by `name`, and do not assume a node in `nodes` has an edge.

---

## 12. Fake mode

With no radio configured, `/topology-scan` answers a small built-in scan — a
four-node mesh with an asymmetric link, a node that timed out, a sleepy end
device with no links, and a two-hop route. It exercises every branch above
without hardware, which is what to develop the UI against before testing on a
real mesh.
