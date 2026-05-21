from app.services.db_services import get_resource_snapshot


def resource_node(state: dict) -> dict:
     """Fetch current resource availability from DB/Cache."""

     if state.get("errors"):
          return state
     
     resources = get_resource_snapshot()

     state["available_beds"] = resources["general_beds"]
     state["available_icu_beds"] = resources["icu_beds"]
     state["available_doctors"] = resources["doctors"]

     state["status"] = "Resources Checked"
     return state