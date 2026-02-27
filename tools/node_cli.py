#!/usr/bin/env python3
"""Simple CLI to start/standby/isolate nodes via the admin API."""

import json
import sys
import urllib.request
import urllib.error
from getpass import getpass

API_BASE = "http://localhost:9000"


def api_request(method, path, token=None, payload=None):
    url = f"{API_BASE}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return {"error": body, "status": e.code}
        except Exception:
            return {"error": str(e), "status": e.code}
    except Exception as e:
        return {"error": str(e), "status": "request_failed"}


def login():
    while True:
        username = input("Admin username [admin]: ").strip() or "admin"
        password = getpass("Admin password [hidden]: ")
        result = api_request("POST", "/auth/login", payload={
            "username": username,
            "password": password
        })
        if result.get("success"):
            print("Login OK.")
            return result.get("token")
        print(f"Login failed: {result.get('error') or result}")


def list_nodes(token):
    result = api_request("GET", "/nodes", token=token)
    if isinstance(result, dict) and result.get("error"):
        print(f"Error fetching nodes: {result}")
        return []
    return result or []


def print_nodes(nodes):
    if not nodes:
        print("No nodes found.")
        return
    print("\nNodes:")
    for n in nodes:
        node_id = n.get("node_id")
        node_type = n.get("node_type")
        node_state = n.get("node_state") or n.get("latest_telemetry", {}).get("node_state") or n.get("status")
        power = n.get("latest_telemetry", {}).get("active_power_mw")
        power_str = f"{power:.1f} MW" if isinstance(power, (int, float)) else "--"
        print(f"- {node_id} ({node_type}) state={node_state} power={power_str}")


def prompt_action():
    print("\nActions: start | standby | isolate | refresh | exit")
    action = input("Action: ").strip().lower()
    if action == "stop":
        action = "standby"
    return action


def main():
    token = login()
    nodes = list_nodes(token)
    print_nodes(nodes)

    while True:
        action = prompt_action()
        if action in {"exit", "quit"}:
            print("Bye.")
            return
        if action == "refresh":
            nodes = list_nodes(token)
            print_nodes(nodes)
            continue
        if action not in {"start", "standby", "isolate"}:
            print("Unknown action.")
            continue

        node_id = input("Node ID: ").strip().upper()
        if not node_id:
            print("Node ID required.")
            continue

        if action == "start":
            payload = {"reason": "CLI start"}
            path = f"/nodes/{node_id}/start"
        elif action == "standby":
            payload = {"reason": "CLI standby", "duration_minutes": 60}
            path = f"/nodes/{node_id}/standby"
        else:
            payload = {"reason": "CLI isolate", "force": True}
            path = f"/nodes/{node_id}/isolate"

        result = api_request("POST", path, token=token, payload=payload)
        if result.get("status") in {"success", True}:
            print(f"OK: {result.get('message') or result}")
        else:
            print(f"Failed: {result}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(0)
