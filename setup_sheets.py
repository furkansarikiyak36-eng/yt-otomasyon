"""
setup_sheets.py
────────────────
Run ONCE after initial setup to create all required tabs
in the MINDFULLY BRAND Google Sheet with correct headers.

Usage:
    python setup_sheets.py

Sheet: https://docs.google.com/spreadsheets/d/1OoxhsKaWSPLKaIs0O4klzIjHdwZQoQ7fLidkFkNS2Kg
"""

import time
import sys
import gspread
from google.oauth2.service_account import Credentials
from config import Config

SCOPES = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]

# ── Tab definitions: name → [headers] ───────────────────────────
TABS = {
    "video_log": [
        "video_id", "channel_id", "channel_name", "title",
        "publish_date", "views", "likes", "comments",
        "status", "youtube_url", "job_id", "created_at"
    ],
    "trend_data": [
        "date", "source", "topic", "popularity",
        "growth_rate", "competition", "product_potential",
        "related", "used_for_video", "used_for_product"
    ],
    "opportunities": [
        "id", "topic", "score", "status",
        "approval_date", "produced", "channel_id",
        "suggested_video", "suggested_product", "created_at"
    ],
    "email_subscribers": [
        "email_hash", "tags", "source", "product",
        "segment", "created_at", "last_interaction"
    ],
    "sales": [
        "sale_id", "product", "amount", "currency",
        "date", "customer_email_hash", "source", "notes"
    ],
    "segments": [
        "segment_name", "count", "criteria", "updated_at"
    ],
    "channels": [
        "channel_id", "channel_name", "youtube_channel_id",
        "refresh_token", "target_audience", "main_theme",
        "status", "created_at"
    ],
    "content_calendar": [
        "channel_id", "channel_name", "date", "time",
        "topic", "video_type", "status", "job_id", "notes"
    ],
    "errors": [
        "date", "module", "error_type",
        "description", "job_id", "resolved"
    ],
    "user_preferences": [
        "profile_id", "preferred_title_length",
        "preferred_outline_points", "last_updated", "edit_count"
    ],
    "pending_sync": [
        "id", "tab_name", "operation",
        "payload_json", "created_at", "retry_count"
    ],
    "social_log": [
        "log_id", "channel_id", "platform", "content_type",
        "source_video_id", "post_id", "status",
        "views", "likes", "shares", "publish_date", "pipeline"
    ],
    "shopify_products": [
        "product_id", "title", "price", "stock",
        "trend_score", "last_analyzed", "content_produced",
        "social_post_created", "notes"
    ],
    "reklam_verileri": [
        "campaign_id", "platform", "budget",
        "impressions", "clicks", "conversions",
        "cost", "date", "notes"
    ],
}

# ── Color coding per tab ─────────────────────────────────────────
TAB_COLORS = {
    "video_log":          {"red": 0.12, "green": 0.47, "blue": 0.71},   # blue
    "trend_data":         {"red": 0.17, "green": 0.63, "blue": 0.17},   # green
    "opportunities":      {"red": 1.0,  "green": 0.50, "blue": 0.05},   # orange
    "email_subscribers":  {"red": 0.58, "green": 0.40, "blue": 0.74},   # purple
    "sales":              {"red": 0.84, "green": 0.15, "blue": 0.16},   # red
    "segments":           {"red": 0.58, "green": 0.40, "blue": 0.74},   # purple
    "channels":           {"red": 0.55, "green": 0.34, "blue": 0.29},   # brown
    "content_calendar":   {"red": 0.09, "green": 0.75, "blue": 0.81},   # teal
    "errors":             {"red": 0.75, "green": 0.75, "blue": 0.75},   # grey
    "user_preferences":   {"red": 0.17, "green": 0.63, "blue": 0.17},   # green
    "pending_sync":       {"red": 1.0,  "green": 0.85, "blue": 0.0},    # yellow
    "social_log":          {"red": 0.09, "green": 0.75, "blue": 0.81},   # teal
    "shopify_products":    {"red": 0.17, "green": 0.63, "blue": 0.17},   # green
    "reklam_verileri":     {"red": 0.84, "green": 0.15, "blue": 0.16},   # red
}

HEADER_BG = {"red": 0.11, "green": 0.11, "blue": 0.18}  # dark navy
HEADER_FG = {"red": 1.0,  "green": 1.0,  "blue": 1.0}   # white


def setup():
    print(f"\n{'='*60}")
    print(f"  MINDFULLY BRAND — Sheets Setup")
    print(f"  Channels: Fitness | Ambiance | Documentary")
    print(f"  Social: Organic + Shopify Pipeline")
    print(f"  Sheet ID: {Config.GOOGLE_SHEETS_ID}")
    print(f"{'='*60}\n")

    # Connect
    print("Connecting to Google Sheets...")
    creds = Credentials.from_service_account_file(
        Config.GOOGLE_SHEETS_CREDENTIALS, scopes=SCOPES
    )
    gc = gspread.authorize(creds)

    try:
        spreadsheet = gc.open_by_key(Config.GOOGLE_SHEETS_ID)
        print(f"✅ Connected: '{spreadsheet.title}'\n")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print("\nMake sure:")
        print("  1. credentials.json is valid")
        print("  2. Service account email has Editor access to the Sheet")
        print("     (Share the sheet with the service account email)")
        sys.exit(1)

    # Get existing tabs
    existing = {ws.title for ws in spreadsheet.worksheets()}
    print(f"Existing tabs: {existing}\n")

    created = []
    updated = []
    skipped = []

    for tab_name, headers in TABS.items():
        time.sleep(1)  # rate limiting

        if tab_name in existing:
            ws = spreadsheet.worksheet(tab_name)
            # Check if headers already set
            current_headers = ws.row_values(1)
            if current_headers == headers:
                skipped.append(tab_name)
                print(f"  ⏭  {tab_name} — already correct")
                continue
            else:
                # Update headers
                ws.update("A1", [headers])
                updated.append(tab_name)
                print(f"  🔄  {tab_name} — headers updated")
        else:
            # Create new tab
            ws = spreadsheet.add_worksheet(
                title=tab_name,
                rows=1000,
                cols=len(headers) + 2
            )
            ws.append_row(headers)
            created.append(tab_name)
            print(f"  ✅  {tab_name} — created ({len(headers)} columns)")

        # Style header row
        _style_header(spreadsheet, ws, headers, tab_name)
        time.sleep(0.5)

    # Summary
    print(f"\n{'─'*60}")
    print(f"✅ Created:  {len(created)} tabs  → {created}")
    print(f"🔄 Updated:  {len(updated)} tabs  → {updated}")
    print(f"⏭  Skipped:  {len(skipped)} tabs  → {skipped}")
    print(f"\nTotal tabs in sheet: {len(TABS)}")
    print(f"\n🎉 Setup complete!")
    print(f"Sheet URL: https://docs.google.com/spreadsheets/d/{Config.GOOGLE_SHEETS_ID}")


def _style_header(spreadsheet, ws, headers, tab_name):
    """Apply dark navy header styling and tab color."""
    try:
        sheet_id = ws._properties["sheetId"]
        col_count = len(headers)

        requests = [
            # Header row background color (dark navy)
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": 1,
                        "startColumnIndex": 0,
                        "endColumnIndex": col_count,
                    },
                    "cell": {
                        "userEnteredFormat": {
                            "backgroundColor": HEADER_BG,
                            "textFormat": {
                                "foregroundColor": HEADER_FG,
                                "bold": True,
                                "fontSize": 10,
                            },
                        }
                    },
                    "fields": "userEnteredFormat(backgroundColor,textFormat)",
                }
            },
            # Freeze header row
            {
                "updateSheetProperties": {
                    "properties": {
                        "sheetId": sheet_id,
                        "gridProperties": {"frozenRowCount": 1},
                        "tabColorStyle": {
                            "rgbColor": TAB_COLORS.get(tab_name, {"red": 0.5, "green": 0.5, "blue": 0.5})
                        },
                    },
                    "fields": "gridProperties.frozenRowCount,tabColorStyle",
                }
            },
            # Auto-resize columns
            {
                "autoResizeDimensions": {
                    "dimensions": {
                        "sheetId": sheet_id,
                        "dimension": "COLUMNS",
                        "startIndex": 0,
                        "endIndex": col_count,
                    }
                }
            },
        ]

        spreadsheet.batch_update({"requests": requests})

    except Exception as e:
        # Styling is cosmetic — don't fail setup if it errors
        print(f"    (styling skipped: {e})")


if __name__ == "__main__":
    setup()
