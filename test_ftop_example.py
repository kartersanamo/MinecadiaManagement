"""
Example F-Top Live update payload and test script.
This demonstrates how the Minecraft server should call the endpoint.
"""

import json
import requests
from datetime import datetime


# Example payload that Minecraft server would send
EXAMPLE_FTOP_PAYLOAD = {
    "server": "factions",
    "updatedAt": int(datetime.now().timestamp() * 1000),
    "ftop": [
        {
            "position": 1,
            "name": "Demon_Kings",
            "value": 125450.5,
            "delta": 850.25,
            "previousPosition": 2,
            "positionDelta": 1,
        },
        {
            "position": 2,
            "name": "VortexGang",
            "value": 118200.0,
            "delta": -520.0,
            "previousPosition": 1,
            "positionDelta": -1,
        },
        {
            "position": 3,
            "name": "Ascended",
            "value": 115750.25,
            "delta": 1200.5,
            "previousPosition": None,
            "positionDelta": 0,  # New to board
        },
        {
            "position": 4,
            "name": "Crimson",
            "value": 112300.0,
            "delta": -100.0,
            "previousPosition": 4,
            "positionDelta": 0,
        },
        {
            "position": 5,
            "name": "Phoenix",
            "value": 108500.75,
            "delta": 250.5,
            "previousPosition": 6,
            "positionDelta": 1,
        },
    ],
    "expeditions": [
        {
            "position": 1,
            "name": "Demon_Kings",
            "value": 45000.0,
            "delta": 500.0,
            "previousPosition": 1,
            "positionDelta": 0,
        },
        {
            "position": 2,
            "name": "VortexGang",
            "value": 42500.0,
            "delta": 100.0,
            "previousPosition": 3,
            "positionDelta": -1,
        },
        {
            "position": 3,
            "name": "Ascended",
            "value": 41200.0,
            "delta": 800.0,
            "previousPosition": None,
            "positionDelta": 0,
        },
        {
            "position": 4,
            "name": "Crimson",
            "value": 39800.0,
            "delta": -200.0,
            "previousPosition": 4,
            "positionDelta": 0,
        },
        {
            "position": 5,
            "name": "Phoenix",
            "value": 37500.0,
            "delta": 300.0,
            "previousPosition": 7,
            "positionDelta": 2,
        },
    ],
    "pvp": [
        {
            "position": 1,
            "name": "Crimson",
            "value": 2850.0,
            "delta": 150.0,
            "previousPosition": 2,
            "positionDelta": 1,
        },
        {
            "position": 2,
            "name": "Demon_Kings",
            "value": 2650.0,
            "delta": 50.0,
            "previousPosition": 1,
            "positionDelta": -1,
        },
        {
            "position": 3,
            "name": "Phoenix",
            "value": 2400.0,
            "delta": 200.0,
            "previousPosition": None,
            "positionDelta": 0,
        },
        {
            "position": 4,
            "name": "VortexGang",
            "value": 2200.0,
            "delta": -100.0,
            "previousPosition": 4,
            "positionDelta": 0,
        },
        {
            "position": 5,
            "name": "Ascended",
            "value": 1950.0,
            "delta": 75.0,
            "previousPosition": 6,
            "positionDelta": 1,
        },
    ],
}


def test_ftop_endpoint(
    endpoint_url: str = "http://127.0.0.1:8767/api/ftop-live",
    secret: str = "test_secret_123",
    payload: dict = None,
) -> None:
    """
    Test the F-Top live endpoint.
    
    Args:
        endpoint_url: Base URL of the F-Top endpoint
        secret: Shared secret for authorization
        payload: JSON payload to send (uses EXAMPLE_FTOP_PAYLOAD if None)
    """
    if payload is None:
        payload = EXAMPLE_FTOP_PAYLOAD

    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }

    print(f"📤 Sending F-Top update to {endpoint_url}")
    print(f"   Server: {payload['server']}")
    print(f"   Updated at: {datetime.fromtimestamp(payload['updatedAt'] / 1000)}")
    print(f"   Categories: {len(payload['ftop'])} F-Top, "
          f"{len(payload['expeditions'])} Expeditions, {len(payload['pvp'])} PvP")

    try:
        response = requests.post(
            endpoint_url,
            json=payload,
            headers=headers,
            timeout=5,
        )

        print(f"\n✅ Response: {response.status_code}")
        print(f"   Body: {response.text}")

        if response.status_code == 200:
            print("\n✨ F-Top message updated successfully!")
        elif response.status_code == 401:
            print("\n❌ Authorization failed - check FTOP_LIVE_SECRET")
        else:
            print(f"\n❌ Error: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"\n❌ Failed to connect to {endpoint_url}")
        print("   Make sure the bot is running and FTOP_HTTP_PORT is correct")
    except requests.exceptions.Timeout:
        print("\n❌ Request timed out")
    except Exception as exc:
        print(f"\n❌ Error: {exc}")


def test_invalid_auth(
    endpoint_url: str = "http://127.0.0.1:8767/api/ftop-live",
) -> None:
    """Test that invalid auth returns 401."""
    print("\n🔒 Testing invalid authorization...")

    headers = {
        "Authorization": "Bearer wrong_secret",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint_url,
            json=EXAMPLE_FTOP_PAYLOAD,
            headers=headers,
            timeout=5,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("   ✅ Correctly rejected unauthorized request")
        else:
            print("   ⚠️  Expected 401, got", response.status_code)
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


def test_invalid_payload(
    endpoint_url: str = "http://127.0.0.1:8767/api/ftop-live",
    secret: str = "test_secret_123",
) -> None:
    """Test that invalid payload returns 400."""
    print("\n❓ Testing invalid payload...")

    invalid_payload = {"server": "factions"}  # Missing required fields

    headers = {
        "Authorization": f"Bearer {secret}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint_url,
            json=invalid_payload,
            headers=headers,
            timeout=5,
        )
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            print("   ✅ Correctly rejected invalid payload")
        else:
            print("   ⚠️  Expected 400, got", response.status_code)
    except Exception as exc:
        print(f"   ❌ Error: {exc}")


if __name__ == "__main__":
    print("=" * 60)
    print("F-Top Live Endpoint Test Suite")
    print("=" * 60)

    # Test with valid payload
    test_ftop_endpoint()

    # Test authorization
    test_invalid_auth()

    # Test validation
    test_invalid_payload()

    print("\n" + "=" * 60)
    print("Tests completed!")
    print("=" * 60)
