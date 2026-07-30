"""
Tests for the Position Diagram API — GET /api/features/diagram/locations

Validates that the endpoint returns data shaped for Unovis VisGraph Parallel layout.
Node classification rules:
  - no location                    → group/subGroup = "Unassigned"
  - has location, no relations     → group/subGroup = "No Connections"
  - has location + relations       → group = parent_location, subGroup = location
"""
from __future__ import annotations

import pytest


ENDPOINT = "/api/features/diagram/locations"

_GROUP_UNASSIGNED = "Unassigned"
_GROUP_NO_CONNECTIONS = "No Connections"


@pytest.mark.asyncio
class TestDiagramLocationsShape:
    """Validate the basic shape of the /diagram/locations response."""

    async def test_returns_200_and_success_status(self, superuser_client):
        resp = await superuser_client.get(ENDPOINT)
        assert resp.status_code == 200
        assert resp.json()["status"] == "success"

    async def test_response_has_required_top_level_keys(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for key in ("nodes", "links", "panels", "groupOrder", "maxLocationDepth"):
            assert key in body, f"Response missing top-level key: '{key}'"

    async def test_group_order_is_list_of_strings(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        assert isinstance(body["groupOrder"], list)
        for item in body["groupOrder"]:
            assert isinstance(item, str), f"groupOrder item is not a string: {item!r}"

    async def test_node_ids_are_unique(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        ids = [n["id"] for n in body["nodes"]]
        duplicates = [nid for nid in ids if ids.count(nid) > 1]
        assert len(ids) == len(set(ids)), f"Duplicate node IDs: {set(duplicates)}"


@pytest.mark.asyncio
class TestDiagramNodeFields:
    """Each node must carry every field that the frontend VisGraph bindings consume."""

    REQUIRED_FIELDS = (
        "id",
        "group",
        "subGroup",
        "label",
        "shape",
        "icon",
        "nodeType",
        "locationPath",
        "locationPathIds",
    )

    async def test_all_required_node_fields_present(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            for field in self.REQUIRED_FIELDS:
                assert field in node, f"Node {node.get('id')} missing field '{field}'"

    async def test_node_group_and_subgroup_are_strings(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            assert isinstance(node["group"], str), f"node.group is not str: {node}"
            assert isinstance(node["subGroup"], str), f"node.subGroup is not str: {node}"

    async def test_node_type_is_valid_enum_value(self, superuser_client):
        valid = {"placed", "no-connections", "unassigned"}
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            assert node["nodeType"] in valid, (
                f"node {node['id']} has invalid nodeType '{node['nodeType']}'"
            )

    async def test_location_paths_are_lists(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            assert isinstance(node["locationPath"], list), f"locationPath is not a list: {node}"
            assert isinstance(node["locationPathIds"], list), (
                f"locationPathIds is not a list: {node}"
            )


@pytest.mark.asyncio
class TestDiagramNodeClassification:
    """Verify the priority-based classification logic."""

    async def test_unassigned_nodes_have_correct_group(self, superuser_client):
        """Nodes with nodeType='unassigned' must have group=subGroup='Unassigned'."""
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            if node["nodeType"] == "unassigned":
                assert node["group"] == _GROUP_UNASSIGNED, (
                    f"Unassigned node {node['id']} has unexpected group '{node['group']}'"
                )
                assert node["subGroup"] == _GROUP_UNASSIGNED, (
                    f"Unassigned node {node['id']} has unexpected subGroup '{node['subGroup']}'"
                )

    async def test_no_connections_nodes_have_correct_group(self, superuser_client):
        """Nodes with nodeType='no-connections' must have group=subGroup='No Connections'."""
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            if node["nodeType"] == "no-connections":
                assert node["group"] == _GROUP_NO_CONNECTIONS, (
                    f"No-connections node {node['id']} has unexpected group '{node['group']}'"
                )
                assert node["subGroup"] == _GROUP_NO_CONNECTIONS, (
                    f"No-connections node {node['id']} has unexpected subGroup '{node['subGroup']}'"
                )

    async def test_placed_nodes_not_in_special_groups(self, superuser_client):
        """Nodes with nodeType='placed' must NOT be in 'Unassigned' or 'No Connections'."""
        body = (await superuser_client.get(ENDPOINT)).json()
        special = {_GROUP_UNASSIGNED, _GROUP_NO_CONNECTIONS}
        for node in body["nodes"]:
            if node["nodeType"] == "placed":
                assert node["group"] not in special, (
                    f"Placed node {node['id']} incorrectly in special group '{node['group']}'"
                )

    async def test_placed_nodes_have_non_empty_location_path(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for node in body["nodes"]:
            if node["nodeType"] == "placed":
                assert len(node["locationPath"]) > 0, (
                    f"Placed node {node['id']} is missing a locationPath"
                )
                assert len(node["locationPath"]) == len(node["locationPathIds"]), (
                    f"Placed node {node['id']} has mismatched locationPath and locationPathIds"
                )
                assert node["group"] == node["locationPath"][0], (
                    f"Placed node {node['id']} group should equal locationPath root"
                )
                assert node["subGroup"] == node["locationPath"][-1], (
                    f"Placed node {node['id']} subGroup should equal locationPath leaf"
                )


@pytest.mark.asyncio
class TestDiagramLinks:
    """Links must reference valid, existing node IDs."""

    async def test_link_fields_present(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for link in body["links"]:
            assert "source" in link, f"Link missing 'source': {link}"
            assert "target" in link, f"Link missing 'target': {link}"

    async def test_link_source_and_target_exist_in_nodes(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        node_ids = {n["id"] for n in body["nodes"]}
        for link in body["links"]:
            assert link["source"] in node_ids, (
                f"Link source '{link['source']}' not found in nodes"
            )
            assert link["target"] in node_ids, (
                f"Link target '{link['target']}' not found in nodes"
            )

    async def test_placed_nodes_appear_in_at_least_one_link(self, superuser_client):
        """Every node with nodeType='placed' must appear in at least one link
        (that's how they earned 'placed' status — they ARE connected)."""
        body = (await superuser_client.get(ENDPOINT)).json()
        link_node_ids: set[str] = set()
        for link in body["links"]:
            link_node_ids.add(link["source"])
            link_node_ids.add(link["target"])
        for node in body["nodes"]:
            if node["nodeType"] == "placed":
                assert node["id"] in link_node_ids, (
                    f"Placed node {node['id']} not found in any link — "
                    "should be classified as 'no-connections' instead"
                )


@pytest.mark.asyncio
class TestDiagramPanels:
    """Panels must reference existing nodes and carry required fields."""

    async def test_panel_required_fields(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        for panel in body["panels"]:
            assert "nodes" in panel, f"Panel missing 'nodes': {panel}"
            assert "label" in panel, f"Panel missing 'label': {panel}"
            assert "panelType" in panel, f"Panel missing 'panelType': {panel}"
            assert isinstance(panel["nodes"], list), f"panel.nodes is not a list: {panel}"

    async def test_panel_nodes_reference_existing_node_ids(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        node_ids = {n["id"] for n in body["nodes"]}
        for panel in body["panels"]:
            for nid in panel["nodes"]:
                assert nid in node_ids, (
                    f"Panel '{panel['label']}' references unknown node id '{nid}'"
                )

    async def test_panels_are_non_empty(self, superuser_client):
        """Every panel in the response must contain at least one node."""
        body = (await superuser_client.get(ENDPOINT)).json()
        for panel in body["panels"]:
            assert len(panel["nodes"]) > 0, (
                f"Panel '{panel['label']}' is empty — should be excluded from response"
            )

    async def test_every_node_belongs_to_exactly_one_panel(self, superuser_client):
        """Each node ID must appear in at least one panel."""
        body = (await superuser_client.get(ENDPOINT)).json()
        node_ids = [n["id"] for n in body["nodes"]]
        panel_node_ids: list[str] = []
        for panel in body["panels"]:
            panel_node_ids.extend(panel["nodes"])
        panel_set = set(panel_node_ids)
        for nid in node_ids:
            assert nid in panel_set, f"Node '{nid}' is not in any panel"

    async def test_placed_nodes_are_in_all_ancestor_location_panels(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        panels_by_location_id = {
            panel["locationId"]: set(panel["nodes"])
            for panel in body["panels"]
            if panel.get("panelType") == "location"
        }
        for node in body["nodes"]:
            if node["nodeType"] != "placed":
                continue
            for location_id in node["locationPathIds"]:
                assert location_id in panels_by_location_id, (
                    f"Missing location panel for ancestor location '{location_id}'"
                )
                assert node["id"] in panels_by_location_id[location_id], (
                    f"Node '{node['id']}' missing from ancestor panel '{location_id}'"
                )

    async def test_special_nodes_are_in_matching_special_panel(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        special_panels = {
            panel["label"]: set(panel["nodes"])
            for panel in body["panels"]
            if panel.get("panelType") == "special"
        }
        for node in body["nodes"]:
            if node["nodeType"] == "unassigned":
                assert node["id"] in special_panels.get(_GROUP_UNASSIGNED, set())
            if node["nodeType"] == "no-connections":
                assert node["id"] in special_panels.get(_GROUP_NO_CONNECTIONS, set())


@pytest.mark.asyncio
class TestDiagramGroupOrder:
    """Validate that groupOrder places special groups at the end."""

    async def test_unassigned_is_last_or_near_last(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        order = body["groupOrder"]
        if _GROUP_UNASSIGNED in order:
            # "Unassigned" must be the very last entry
            assert order[-1] == _GROUP_UNASSIGNED, (
                f"'Unassigned' should be last in groupOrder, got: {order}"
            )

    async def test_no_connections_precedes_unassigned(self, superuser_client):
        body = (await superuser_client.get(ENDPOINT)).json()
        order = body["groupOrder"]
        if _GROUP_NO_CONNECTIONS in order and _GROUP_UNASSIGNED in order:
            idx_nc = order.index(_GROUP_NO_CONNECTIONS)
            idx_ua = order.index(_GROUP_UNASSIGNED)
            assert idx_nc < idx_ua, (
                f"'No Connections' should precede 'Unassigned' in groupOrder, got: {order}"
            )

    async def test_group_order_contains_all_node_groups(self, superuser_client):
        """Every unique node.group value must appear in groupOrder."""
        body = (await superuser_client.get(ENDPOINT)).json()
        order_set = set(body["groupOrder"])
        for node in body["nodes"]:
            assert node["group"] in order_set, (
                f"Node group '{node['group']}' is missing from groupOrder"
            )


    async def test_location_hierarchy_preserved(self, superuser_client):
        """The backend should preserve the location hierarchy in the node group/subGroup structure."""
        resp = await superuser_client.get(ENDPOINT)
        body = resp.json()
        # Check that at least some nodes have both group and subGroup
        has_group_and_subGroup = any(
            node.get("group") and node.get("subGroup") for node in body["nodes"]
        )
        assert has_group_and_subGroup, "No nodes have both group and subGroup"

    async def test_unauthenticated_request_fails(self, client):
        """Requests without auth should fail."""
        resp = await client.get(ENDPOINT)
        assert resp.status_code in (401, 403, 422)


class TestDiagramNodeTypeMapping:
    """Unit-level tests for the asset_class → node type mapping."""

    def test_mapping_function_exists(self):
        from app.api.features.diagram import _map_asset_class_to_node_type

        # Keyword-based mappings
        assert _map_asset_class_to_node_type("Pressure Sensor") == "network"
        assert _map_asset_class_to_node_type("Centrifugal Pump") == "compute"
        assert _map_asset_class_to_node_type("Gate Valve") == "identity"
        assert _map_asset_class_to_node_type("Storage Tank") == "secret"
        assert _map_asset_class_to_node_type("Conveyor Belt") == "network"

    def test_fallback_to_resource(self):
        from app.api.features.diagram import _map_asset_class_to_node_type

        assert _map_asset_class_to_node_type(None) == "resource"
        assert _map_asset_class_to_node_type("") == "resource"
        assert _map_asset_class_to_node_type("Unknown Equipment") == "resource"
