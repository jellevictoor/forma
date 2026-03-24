"""Playwright device profiles and page list — used by visual test scripts.

Usage:
    from playwright.config import DEVICES, PAGES, BASE_URL
"""

BASE_URL = "http://localhost:8080"

DEVICES = {
    "mobile": {
        "viewport": {"width": 390, "height": 844},
        "device_scale_factor": 3,
        "is_mobile": True,
        "has_touch": True,
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    },
    "desktop": {
        "viewport": {"width": 1440, "height": 900},
        "device_scale_factor": 2,
        "is_mobile": False,
        "has_touch": False,
    },
}

PAGES = [
    ("/", "dashboard"),
    ("/plan", "plan"),
    ("/goal", "goal"),
    ("/activities/all/1", "activities"),
    ("/analytics/run", "analytics"),
    ("/progress", "progress"),
    ("/profile", "profile"),
]

# Desktop-only pages (skipped in mobile screenshots)
ADMIN_PAGES = [
    ("/admin", "admin"),
    ("/admin?tab=users", "admin-users"),
    ("/admin?tab=prompts", "admin-ai"),
]
