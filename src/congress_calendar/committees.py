"""Static committee data for the 119th Congress (2025-2027)."""

COMMITTEES_119: list[dict[str, str]] = [
    # Senate Standing Committees
    {"name": "Agriculture, Nutrition, and Forestry", "system_code": "ssaf00", "chamber": "senate"},
    {"name": "Appropriations", "system_code": "ssap00", "chamber": "senate"},
    {"name": "Armed Services", "system_code": "ssas00", "chamber": "senate"},
    {"name": "Banking, Housing, and Urban Affairs", "system_code": "ssbk00", "chamber": "senate"},
    {"name": "Budget", "system_code": "ssbu00", "chamber": "senate"},
    {"name": "Commerce, Science, and Transportation", "system_code": "sscm00", "chamber": "senate"},
    {"name": "Energy and Natural Resources", "system_code": "sseg00", "chamber": "senate"},
    {"name": "Environment and Public Works", "system_code": "ssev00", "chamber": "senate"},
    {"name": "Finance", "system_code": "ssfi00", "chamber": "senate"},
    {"name": "Foreign Relations", "system_code": "ssfr00", "chamber": "senate"},
    {
        "name": "Health, Education, Labor, and Pensions",
        "system_code": "sshr00",
        "chamber": "senate",
    },
    {
        "name": "Homeland Security and Governmental Affairs",
        "system_code": "ssga00",
        "chamber": "senate",
    },
    {"name": "Judiciary", "system_code": "ssju00", "chamber": "senate"},
    {"name": "Rules and Administration", "system_code": "ssra00", "chamber": "senate"},
    {"name": "Small Business and Entrepreneurship", "system_code": "sssb00", "chamber": "senate"},
    {"name": "Veterans' Affairs", "system_code": "ssva00", "chamber": "senate"},
    # Senate Select/Special Committees
    {"name": "Aging (Special)", "system_code": "spag00", "chamber": "senate"},
    {"name": "Ethics (Select)", "system_code": "slet00", "chamber": "senate"},
    {"name": "Indian Affairs", "system_code": "slia00", "chamber": "senate"},
    {"name": "Intelligence (Select)", "system_code": "slin00", "chamber": "senate"},
    {
        "name": "International Narcotics Control (Caucus)",
        "system_code": "scnc00",
        "chamber": "senate",
    },
    # House Standing Committees
    {"name": "Agriculture", "system_code": "hsag00", "chamber": "house"},
    {"name": "Appropriations", "system_code": "hsap00", "chamber": "house"},
    {"name": "Armed Services", "system_code": "hsas00", "chamber": "house"},
    {"name": "Budget", "system_code": "hsbu00", "chamber": "house"},
    {"name": "Education and Workforce", "system_code": "hsed00", "chamber": "house"},
    {"name": "Energy and Commerce", "system_code": "hsif00", "chamber": "house"},
    {"name": "Ethics", "system_code": "hsso00", "chamber": "house"},
    {"name": "Financial Services", "system_code": "hsba00", "chamber": "house"},
    {"name": "Foreign Affairs", "system_code": "hsfa00", "chamber": "house"},
    {"name": "Homeland Security", "system_code": "hshm00", "chamber": "house"},
    {"name": "House Administration", "system_code": "hsha00", "chamber": "house"},
    {"name": "Judiciary", "system_code": "hsju00", "chamber": "house"},
    {"name": "Natural Resources", "system_code": "hsii00", "chamber": "house"},
    {"name": "Oversight and Government Reform", "system_code": "hsgo00", "chamber": "house"},
    {"name": "Rules", "system_code": "hsru00", "chamber": "house"},
    {"name": "Science, Space, and Technology", "system_code": "hssy00", "chamber": "house"},
    {"name": "Small Business", "system_code": "hssm00", "chamber": "house"},
    {"name": "Transportation and Infrastructure", "system_code": "hspw00", "chamber": "house"},
    {"name": "Veterans' Affairs", "system_code": "hsvr00", "chamber": "house"},
    {"name": "Ways and Means", "system_code": "hswm00", "chamber": "house"},
    # House Select Committees
    {"name": "Intelligence (Permanent Select)", "system_code": "hlig00", "chamber": "house"},
    {
        "name": "Strategic Competition with the CCP (Select)",
        "system_code": "hlzs00",
        "chamber": "house",
    },
    {
        "name": "January 6 Investigation (Select Subcommittee)",
        "system_code": "hlqj00",
        "chamber": "house",
    },
]

_BY_CODE = {c["system_code"]: c for c in COMMITTEES_119}


def fallback_committee_name(system_code: str) -> str | None:
    """A display name for a committee code, for records that arrive without one.

    Congress.gov sometimes lists a committee by ``systemCode`` alone. A parent
    code resolves to its own name; a subcommittee code ("hspw07") only tells us
    its parent ("hspw00"), so it is named as a subcommittee of that.
    """
    code = system_code.lower()
    if len(code) < 3:
        return None
    exact = _BY_CODE.get(code)
    if exact is not None:
        return _with_chamber(exact)
    parent = _BY_CODE.get(code[:-2] + "00")
    if parent is not None:
        return f"{_with_chamber(parent)} Subcommittee"
    return None


def _with_chamber(committee: dict[str, str]) -> str:
    # Matches how Congress.gov names committees ("House Education and
    # Workforce"), without doubling up on "House Administration".
    chamber = committee["chamber"].title()
    name = committee["name"]
    return name if name.startswith(chamber) else f"{chamber} {name}"
