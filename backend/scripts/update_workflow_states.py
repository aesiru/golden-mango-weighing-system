#!/usr/bin/env python3
"""Update all workflow states to use Nuxt UI colors"""

import asyncio
import aiohttp
import json

# Base URL for the API
BASE_URL = "http://localhost:8000"

# Color mapping based on state semantics
COLOR_MAPPING = {
    # Positive/Completed states
    "acquired": "success",
    "active": "primary", 
    "approved": "success",
    "complete": "success",
    "completed": "success",
    "confirmed": "success",
    "fully_received": "success",
    "inspected": "success",
    "posted": "success",
    
    # Warning/In-progress states
    "awaiting_resources": "warning",
    "in_progress": "warning",
    "partially_received": "warning",
    "under_maintenance": "warning",
    "under_repair": "warning",
    
    # Negative/Error states
    "cancelled": "error",
    "decommissioned": "error",
    "disposed": "error",
    "failed_inspection": "error",
    "rejected": "error",
    
    # Initial/Neutral states
    "draft": "neutral",
    "awarded": "neutral",
    "closed": "neutral",
    "inactive": "neutral",
    "issued": "neutral",
    "on_hold": "neutral",
    "ordered": "neutral",
    "pending_approval": "neutral",
    "pending_review": "neutral",
    "planned": "neutral",
    "ready": "neutral",
    "received": "neutral",
    "release": "neutral",
    "returned": "neutral",
    "review": "neutral",
    "sourcing": "neutral",
    "submitted": "neutral",
    
    # Request/Open states
    "open": "info",
    "requested": "info",
}

async def update_workflow_state(session, state_id, label, color):
    """Update a single workflow state"""
    url = f"{BASE_URL}/api/workflow/states/{state_id}"
    payload = {
        "color": color,
        "label": label
    }
    
    async with session.put(url, json=payload) as response:
        if response.status == 200:
            result = await response.json()
            print(f"✓ Updated '{label}' -> {color}")
            return True
        else:
            print(f"✗ Failed to update '{label}': {response.status}")
            return False

async def main():
    """Main function to update all workflow states"""
    
    # Get current states
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/workflow/states") as response:
            if response.status != 200:
                print(f"Failed to get states: {response.status}")
                return
            
            data = await response.json()
            states = data.get("data", [])
            
    print(f"Found {len(states)} workflow states")
    print("=" * 50)
    
    # Update each state
    success_count = 0
    async with aiohttp.ClientSession() as session:
        for state in states:
            state_id = state["id"]
            label = state["label"]
            current_color = state["color"]
            
            # Determine new color
            new_color = COLOR_MAPPING.get(state_id, "neutral")
            
            # Skip if already has correct color
            if current_color == new_color:
                print(f"⚪ Skipping '{label}' - already has color {new_color}")
                success_count += 1
                continue
            
            # Update the state
            if await update_workflow_state(session, state_id, label, new_color):
                success_count += 1
    
    print("=" * 50)
    print(f"Updated {success_count}/{len(states)} states successfully")
    
    # Show final state
    print("\nFinal workflow states:")
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/api/workflow/states") as response:
            if response.status == 200:
                data = await response.json()
                states = data.get("data", [])
                
                # Group by color
                by_color = {}
                for state in states:
                    color = state["color"]
                    if color not in by_color:
                        by_color[color] = []
                    by_color[color].append(state["label"])
                
                for color in ["primary", "secondary", "success", "info", "warning", "error", "neutral"]:
                    if color in by_color:
                        print(f"\n{color.upper()} ({len(by_color[color])}):")
                        for label in sorted(by_color[color]):
                            print(f"  - {label}")

if __name__ == "__main__":
    asyncio.run(main())
