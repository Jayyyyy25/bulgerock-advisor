"""
Zoho CRM API client.
Handles OAuth token refresh and contact search/fetch for client data.
Uses the standard Contacts search endpoint (scope: ZohoCRM.modules.contacts.READ).
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
_CRM_BASE  = "https://www.zohoapis.com/crm/v2"

_access_token: str | None = None


def _refresh_access_token() -> str:
    global _access_token
    resp = requests.post(_TOKEN_URL, data={
        "grant_type":    "refresh_token",
        "client_id":     os.environ["ZOHO_CLIENT_ID"],
        "client_secret": os.environ["ZOHO_CLIENT_SECRET"],
        "refresh_token": os.environ["ZOHO_REFRESH_TOKEN"],
    })
    resp.raise_for_status()
    _access_token = resp.json()["access_token"]
    return _access_token


def _get_token() -> str:
    global _access_token
    if not _access_token:
        _refresh_access_token()
    return _access_token


def _get(path: str, params: dict = None) -> dict:
    """Authenticated GET with one automatic token refresh on 401."""
    headers = {"Authorization": f"Zoho-oauthtoken {_get_token()}"}
    resp = requests.get(f"{_CRM_BASE}/{path}", headers=headers, params=params)
    if resp.status_code == 401:
        headers["Authorization"] = f"Zoho-oauthtoken {_refresh_access_token()}"
        resp = requests.get(f"{_CRM_BASE}/{path}", headers=headers, params=params)
    resp.raise_for_status()
    return resp.json()


def _post(path: str, payload: dict) -> dict:
    """Authenticated POST with one automatic token refresh on 401."""
    headers = {
        "Authorization": f"Zoho-oauthtoken {_get_token()}",
        "Content-Type": "application/json",
    }
    resp = requests.post(f"{_CRM_BASE}/{path}", headers=headers, json=payload)
    if resp.status_code == 401:
        headers["Authorization"] = f"Zoho-oauthtoken {_refresh_access_token()}"
        resp = requests.post(f"{_CRM_BASE}/{path}", headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()


def create_contact(
    first_name: str,
    last_name: str,
    email: str = None,
    phone: str = None,
    client_id: str = None,
    risk_profile: str = None,
    aum: float = None,
    investment_objectives: str = None,
    last_meeting_date: str = None,
) -> dict:
    """Create a single Contact in Zoho CRM. Returns the created record."""
    record = {
        "First_Name": first_name,
        "Last_Name":  last_name,
    }
    if email:                 record["Email"]                  = email
    if phone:                 record["Phone"]                  = phone
    if client_id:             record["Client_ID"]              = client_id
    if risk_profile:          record["Risk_Profile"]           = risk_profile
    if aum is not None:       record["AUM"]                    = aum
    if investment_objectives: record["Investment_Objectives"]  = investment_objectives
    if last_meeting_date:     record["Last_Meeting_Date"]      = last_meeting_date

    result = _post("Contacts", {"data": [record]})
    return result.get("data", [{}])[0]


def find_contact_by_client_id(client_id: str) -> dict | None:
    """Return the Zoho Contact with matching Client_ID, or None if not found."""
    try:
        data = _get("Contacts/search", params={"criteria": f"(Client_ID:equals:{client_id})", "per_page": 1})
        records = data.get("data", [])
        return _record_to_client(records[0]) if records else None
    except Exception:
        return None


def upsert_contact(client_id: str, **kwargs) -> dict:
    """
    Create a Zoho contact if Client_ID doesn't exist yet.
    Skips creation if already present (Zoho doesn't support upsert on custom fields).
    Returns the result data dict.
    """
    existing = find_contact_by_client_id(client_id)
    if existing:
        return {"status": "skipped", "client_id": client_id, "zoho_id": existing.get("zoho_id")}
    return create_contact(client_id=client_id, **kwargs)


def _record_to_client(r: dict) -> dict:
    """Normalize a Zoho Contact record to our internal client shape."""
    return {
        "client_id":    r.get("Client_ID") or r.get("id"),
        "full_name":    r.get("Full_Name") or f"{r.get('First_Name', '')} {r.get('Last_Name', '')}".strip(),
        "email":        r.get("Email"),
        "phone":        r.get("Phone") or r.get("Mobile"),
        "risk_profile": (r.get("Risk_Profile") or "").lower(),
        "advisor_id":   r.get("Advisor_ID"),
        "aum":          r.get("AUM"),
        "zoho_id":      r.get("id"),
    }


def search_contacts(
    name_contains: str = None,
    risk_profile: str = None,
    advisor_id: str = None,
    min_aum: float = None,
    max_aum: float = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search Zoho CRM Contacts with optional filters.
    Returns a list of normalized client dicts.
    """
    limit = min(limit, 50)

    # Build criteria string for the search endpoint
    # Format: (field:operator:value)AND(field:operator:value)
    criteria_parts = []

    if name_contains:
        criteria_parts.append(f"(Full_Name:contains:{name_contains})")
    if risk_profile:
        criteria_parts.append(f"(Risk_Profile:equals:{risk_profile})")
    if advisor_id:
        criteria_parts.append(f"(Advisor_ID:equals:{advisor_id})")

    if criteria_parts:
        criteria = "AND".join(criteria_parts)
        params = {"criteria": criteria, "per_page": limit}
        data = _get("Contacts/search", params=params)
    else:
        # No filters — fetch all contacts
        data = _get("Contacts", params={"per_page": limit})

    records = data.get("data", [])
    clients = [_record_to_client(r) for r in records]

    # Apply AUM filters client-side (Zoho search doesn't support numeric range on custom fields)
    if min_aum is not None:
        clients = [c for c in clients if c["aum"] is not None and c["aum"] >= min_aum]
    if max_aum is not None:
        clients = [c for c in clients if c["aum"] is not None and c["aum"] <= max_aum]

    return clients


def get_contacts_by_client_ids(client_ids: list[str]) -> dict[str, dict]:
    """
    Fetch multiple contacts by their Client_ID values.
    Returns a dict keyed by client_id for easy lookup.
    """
    if not client_ids:
        return {}

    # Fetch each client_id with OR criteria
    criteria = "OR".join(f"(Client_ID:equals:{cid})" for cid in client_ids)
    params = {"criteria": criteria, "per_page": min(len(client_ids), 50)}
    data = _get("Contacts/search", params=params)

    records = data.get("data", [])
    clients = [_record_to_client(r) for r in records]
    return {c["client_id"]: c for c in clients if c["client_id"]}
