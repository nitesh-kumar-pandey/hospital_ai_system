from app.services.db_services import allocate_resource


def optimizer_node(state: dict) -> dict:
    """Assign bed and doctor based on priority and availability."""

    if state.get("errors"):
        return state

    priority = state.get("priority_level", "Medium")
    icu_beds = state.get("available_icu_beds", 0)
    gen_beds = state.get("available_beds", 0)
    doctors  = state.get("available_doctors", 0)

    if priority == "Critical":
        if icu_beds > 0:
            bed, doctor = allocate_resource("icu")
            state["assigned_bed"]             = bed
            state["assigned_doctor"]          = doctor
            state["estimated_wait_minutes"]   = 0
            state["status"]                   = "Assigned - ICU"
        else:
            state["assigned_bed"]             = None
            state["assigned_doctor"]          = None
            state["estimated_wait_minutes"]   = _estimate_wait(priority, gen_beds)
            state["status"]                   = "Waiting - ICU Full"

    elif priority == "High":
        if gen_beds > 0:
            bed, doctor = allocate_resource("general")
            state["assigned_bed"]             = bed
            state["assigned_doctor"]          = doctor
            state["estimated_wait_minutes"]   = 5
            state["status"]                   = "Assigned - General Ward"
        else:
            state["assigned_bed"]             = None
            state["assigned_doctor"]          = None
            state["estimated_wait_minutes"]   = _estimate_wait(priority, gen_beds)
            state["status"]                   = "Waiting - No Beds"

    elif priority == "Medium":
        if gen_beds > 0 and doctors > 0:
            bed, doctor = allocate_resource("general")   # Fixed typo: was "genral"
            state["assigned_bed"]             = bed
            state["assigned_doctor"]          = doctor
            state["estimated_wait_minutes"]   = 15
            state["status"]                   = "Assigned - General Ward"
        else:
            state["status"]                   = "Waiting - Queue"
            state["estimated_wait_minutes"]   = _estimate_wait(priority, gen_beds)

    else:  # Low
        state["status"]                   = "Waiting - Outpatient"
        state["estimated_wait_minutes"]   = _estimate_wait(priority, gen_beds)

    return state


def _estimate_wait(priority: str, available: int) -> int:
    base = {"Critical": 0, "High": 10, "Medium": 30, "Low": 60}.get(priority, 30)
    if available == 0:
        base += 45
    return base