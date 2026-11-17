"""Seed knowledge for Nova City. Every item is synthetic demo material."""

DOCUMENTS = [
    {
        "id": "NOVA-PLAN-001",
        "title": "Nova City District Planning Brief",
        "domain": "planning",
        "text": (
            "Nova City is a fictional demonstration city with five districts. "
            "Central District has the largest baseline population and the highest commercial share. "
            "East Gardens and West Riverside have comparatively higher green-space shares. "
            "Any expansion proposal should compare demand for transport, water and electricity "
            "before approving additional development. All figures in this brief are synthetic."
        ),
    },
    {
        "id": "NOVA-TRAFFIC-001",
        "title": "Transport Capacity Notes",
        "domain": "traffic",
        "text": (
            "The demo transport model estimates daily vehicle demand from a district baseline. "
            "Population growth and commercial growth increase estimated traffic pressure. "
            "The current prototype does not model road geometry, signal timing, public transport, "
            "peak-hour flows or queue lengths. A higher vehicle estimate is a demand signal, "
            "not proof that a road is congested. Baseline values are synthetic."
        ),
    },
    {
        "id": "NOVA-WATER-001",
        "title": "Water Demand Planning Notes",
        "domain": "water",
        "text": (
            "The prototype estimates daily water demand using district baseline consumption. "
            "Population change is the main driver in the demonstration formula, with a smaller "
            "commercial activity adjustment. The prototype does not model reservoirs, pipe "
            "capacity, leakage, rainfall, groundwater or hourly demand. Estimated demand must "
            "not be interpreted as available supply. All values are synthetic."
        ),
    },
    {
        "id": "NOVA-ENERGY-001",
        "title": "Electricity Demand Planning Notes",
        "domain": "energy",
        "text": (
            "The prototype estimates daily electricity demand using district baseline consumption. "
            "Both population and commercial growth affect the estimate; commercial growth has a "
            "larger demonstration coefficient. The model does not represent generation capacity, "
            "grid topology, storage, outages, weather or time-of-use peaks. Demand estimates "
            "cannot establish whether the grid can supply the projected load. Values are synthetic."
        ),
    },
    {
        "id": "NOVA-METHOD-001",
        "title": "Simulation Assumptions and Limits",
        "domain": "methodology",
        "text": (
            "LifeOS Twin uses explicit deterministic coefficients for its first demonstration. "
            "It does not train a predictive model in this release. The scenario engine calculates "
            "results in Python; retrieval ranks supporting notes and returns source identifiers. "
            "The city and documents are fictional. Results are suitable for software testing and "
            "product demonstration only, not real-world infrastructure decisions."
        ),
    },
]
