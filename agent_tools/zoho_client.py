"""
Zoho CRM API client.
Handles OAuth token refresh and contact search/fetch for client data.
"""
import os
import json
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


def _get(path: str, params: dict = None) -> dict:
    """Make an authenticated GET request, retrying once on 401."""
    global _access_token
    if not _access_token:
        _refresh_access_token()

    headers = {"Authorization": f"Zoho-oauthtoken {_access_token}"}
    resp = requests.get(f"{_CRM_BASE}/{path}", headers=headers, params=params)

    if resp.status_code == 401:
        _refresh_access_token()
        headers["Authorization"] = f"Zoho-oauthtoken {_access_token}"
        resp = requests.get(f"{_CRM_BASE}/{path}", headers=headers, params=params)

    resp.raise_for_status()
    return resp.json()


def _record_to_client(r: dict) -> dict:
    """Normalize a Zoho Contact record to our internal client shape."""
    return {
        "client_id":    r.get("Client_ID") or r.get("id"),
        "full_name":    r.get("Full_Name") or f"{r.get('First_Name', '')} {r.get('Last_Name', '')}".strip(),
        "email":        r.get("Email"),
        "phone":        r.get("Phone"),
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

    # Build COQL query (Zoho's SQL-like query language)
    conditions = ["Client_ID is not null"]

    if name_contains:
        conditions.append(f"Full_Name like '%{name_contains}%'")
    if risk_profile:
        conditions.append(f"Risk_Profile = '{risk_profile}'")
    if advisor_id:
        conditions.append(f"Advisor_ID = '{advisor_id}'")
    if min_aum is not None:
        conditions.append(f"AUM >= {min_aum}")
    if max_aum is not None:
        conditions.append(f"AUM <= {max_aum}")

    where = " and ".join(conditions)
    coql = (
        f"select Client_ID, Full_Name, First_Name, Last_Name, Email, Phone, "
        f"Risk_Profile, AUM, Advisor_ID "
        f"from Contacts where {where} limit {limit}"
    )

    resp = requests.post(
        f"{_CRM_BASE}/coql",
        headers={
            "Authorization": f"Zoho-oauthtoken {_get_token()}",
            "Content-Type": "application/json",
        },
        json={"select_query": coql},
    )

    if resp.status_code == 401:
        _refresh_access_token()
        resp = requests.post(
            f"{_CRM_BASE}/coql",
            headers={
                "Authorization": f"Zoho-oauthtoken {_access_token}",
                "Content-Type": "application/json",
            },
            json={"select_query": coql},
        )

    resp.raise_for_status()
    data = resp.json()
    records = data.get("data", [])
    return [_record_to_client(r) for r in records]


def get_contacts_by_client_ids(client_ids: list[str]) -> dict[str, dict]:
    """
    Fetch multiple contacts by their Client_ID values.
    Returns a dict keyed by client_id for easy lookup.
    """
    if not client_ids:
        return {}

    id_list = ", ".join(f"'{cid}'" for cid in client_ids)
    coql = (
        f"select Client_ID, Full_Name, First_Name, Last_Name, Email, Phone, "
        f"Risk_Profile, AUM, Advisor_ID "
        f"from Contacts where Client_ID in ({id_list}) limit 50"
    )

    resp = requests.post(
        f"{_CRM_BASE}/coql",
        headers={
            "Authorization": f"Zoho-oauthtoken {_get_token()}",
            "Content-Type": "application/json",
        },
        json={"select_query": coql},
    )

    if resp.status_code == 401:
        _refresh_access_token()
        resp = requests.post(
            f"{_CRM_BASE}/coql",
            headers={
                "Authorization": f"Zoho-oauthtoken {_access_token}",
                "Content-Type": "application/json",
            },
            json={"select_query": coql},
        )

    resp.raise_for_status()
    records = resp.json().get("data", [])
    clients = [_record_to_client(r) for r in records]
    return {c["client_id"]: c for c in clients if c["client_id"]}


def _get_token() -> str:
    global _access_token
    if not _access_token:
        _refresh_access_token()
    return _access_token
