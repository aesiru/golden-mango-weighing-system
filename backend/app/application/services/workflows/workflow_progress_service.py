from typing import Any, Optional

from app.meta.registry import MetaRegistry


class WorkflowProgressService:
    def __init__(self, workflow_repo, entity_repo):
        self.workflow_repo = workflow_repo
        self.entity_repo = entity_repo

    async def get_progress(self, entity: str, record_id: str) -> dict[str, Any]:
        record = await self.entity_repo.get_by_id(entity, record_id)
        if not record:
            raise ValueError(f"Record '{record_id}' not found for entity '{entity}'")

        node = await self._build_node(entity, record)
        return {
            "entity": entity,
            "record_id": record_id,
            "title": node.get("title"),
            "summary": node.get("summary"),
            "node": node,
        }

    async def _build_node(self, entity: str, record: Any) -> dict[str, Any]:
        workflow_def = await self._get_workflow_definition(entity)
        record_id = getattr(record, "id", None)
        title = self._get_record_title(entity, record)
        current_state = self._normalize_state(
            getattr(record, "workflow_state", None) or workflow_def.get("initial_state")
        )
        transitions_from_current = [
            t for t in workflow_def["transitions"] if t["from_state"] == current_state
        ]
        next_actions = [
            {
                "action": t["action"],
                "label": t["action_label"],
                "target_state": t["to_state"],
                "target_label": self._state_label(workflow_def, t["to_state"]),
                "description": self._transition_description(entity, t["action"], t["to_state"]),
            }
            for t in transitions_from_current
        ]

        children: list[dict[str, Any]] = []
        summary: Optional[str] = None

        return {
            "entity": entity,
            "record_id": record_id,
            "label": MetaRegistry.get(entity).label if MetaRegistry.get(entity) else entity.replace("_", " ").title(),
            "title": title,
            "current_state": current_state,
            "current_state_label": self._state_label(workflow_def, current_state),
            "next_actions": next_actions,
            "steps": self._build_steps(entity, workflow_def, current_state),
            "summary": summary,
            "children": children,
        }

    async def _get_workflow_definition(self, entity: str) -> dict[str, Any]:
        workflow = await self.workflow_repo.get_workflow(entity)
        if workflow:
            return {
                "initial_state": next((sl.state.slug for sl in workflow.state_links if sl.is_initial), None),
                "states": [
                    {
                        "slug": sl.state.slug,
                        "label": sl.state.label,
                        "sort_order": sl.sort_order,
                    }
                    for sl in sorted(workflow.state_links, key=lambda item: item.sort_order)
                ],
                "transitions": [
                    {
                        "from_state": t.from_state.slug,
                        "to_state": t.to_state.slug,
                        "action": t.action_ref.slug,
                        "action_label": t.action_ref.label,
                        "sort_order": t.sort_order,
                    }
                    for t in sorted(workflow.transitions, key=lambda item: item.sort_order)
                ],
            }

        meta = MetaRegistry.get(entity)
        workflow_meta = getattr(meta, "workflow", None) if meta else None
        if not workflow_meta or not getattr(workflow_meta, "enabled", False):
            raise ValueError(f"No workflow configured for entity '{entity}'")

        states: list[dict[str, Any]] = []
        for index, state in enumerate(getattr(workflow_meta, "states", []) or []):
            if isinstance(state, dict):
                slug = self._normalize_state(state.get("slug") or state.get("name") or state.get("label"))
                label = state.get("label") or state.get("name") or slug
            else:
                slug = self._normalize_state(state)
                label = str(state)
            states.append({"slug": slug, "label": label, "sort_order": index})

        transitions: list[dict[str, Any]] = []
        for index, transition in enumerate(getattr(workflow_meta, "transitions", []) or []):
            if not isinstance(transition, dict):
                continue
            from_state = transition.get("from") or transition.get("from_state")
            to_state = transition.get("to") or transition.get("to_state")
            action = transition.get("action")
            transitions.append(
                {
                    "from_state": self._normalize_state(from_state),
                    "to_state": self._normalize_state(to_state),
                    "action": self._normalize_state(action),
                    "action_label": transition.get("label") or str(action),
                    "sort_order": index,
                }
            )

        return {
            "initial_state": self._normalize_state(getattr(workflow_meta, "initial_state", None) or getattr(workflow_meta, "default_state", None)),
            "states": sorted(states, key=lambda item: item["sort_order"]),
            "transitions": sorted(transitions, key=lambda item: item["sort_order"]),
        }

    def _build_steps(self, entity: str, workflow_def: dict[str, Any], current_state: str) -> list[dict[str, Any]]:
        states = self._filter_states_for_display(workflow_def["states"], current_state)
        current_index = next(
            (index for index, state in enumerate(states) if state["slug"] == current_state),
            0,
        )
        steps: list[dict[str, Any]] = []

        for index, state in enumerate(states):
            outgoing = [
                t for t in workflow_def["transitions"] if t["from_state"] == state["slug"]
            ]
            incoming = [
                t for t in workflow_def["transitions"] if t["to_state"] == state["slug"]
            ]
            status = "upcoming"
            if index < current_index:
                status = "completed"
            elif state["slug"] == current_state:
                status = "current"

            if status == "current":
                if outgoing:
                    next_text = "; ".join(
                        f"{t['action_label']} → {self._state_label(workflow_def, t['to_state'])}"
                        for t in outgoing
                    )
                    description = f"Current step. Next: {next_text}."
                else:
                    description = "Current step. This workflow is at its final step."
            elif status == "completed":
                description = f"Completed step: {state['label']}."
            else:
                if incoming:
                    transition = incoming[0]
                    description = self._transition_description(entity, transition["action"], state["slug"])
                else:
                    description = f"Upcoming step: {state['label']}."

            steps.append(
                {
                    "key": state["slug"],
                    "title": state["label"],
                    "description": description,
                    "status": status,
                    "current": status == "current",
                }
            )

        return steps

    def _filter_states_for_display(self, states: list[dict[str, Any]], current_state: str) -> list[dict[str, Any]]:
        hidden_terminal_states = {"rejected"}
        filtered = [
            state
            for state in states
            if state["slug"] == current_state or state["slug"] not in hidden_terminal_states
        ]
        return filtered or states

    def _state_label(self, workflow_def: dict[str, Any], slug: Optional[str]) -> str:
        if not slug:
            return "Unknown"
        for state in workflow_def["states"]:
            if state["slug"] == slug:
                return state["label"]
        return slug.replace("_", " ").title()

    def _get_record_title(self, entity: str, record: Any) -> str:
        meta = MetaRegistry.get(entity)
        if meta and getattr(meta, "title_field", None):
            value = getattr(record, meta.title_field, None)
            if value:
                return str(value)
        record_id = getattr(record, "id", None)
        return str(record_id or entity)

    def _normalize_state(self, value: Any) -> str:
        if value is None:
            return "unknown"
        return (
            str(value)
            .strip()
            .lower()
            .replace(" ", "_")
        )

    def _transition_description(self, entity: str, action: str, to_state: str) -> str:
        action_key = self._normalize_state(action)
        guide: dict[str, dict[str, str]] = {}
        return guide.get(entity, {}).get(
            action_key,
            f"Move this workflow to {to_state.replace('_', ' ')}.",
        )
