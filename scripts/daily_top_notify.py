from scripts.daily_top import fetch_upcoming_with_metrics, build_top_list, format_text
from services.notify import send_telegram  # používame novú funkciu (s chunkingom)

def main():
    rows = fetch_upcoming_with_metrics()
    top_events = build_top_list(rows)
    if not top_events:
        print("Žiadne nadchádzajúce eventy.")
        return
    text = format_text(top_events)
    send_telegram(text, parse_mode="Markdown")  # automaticky fallbackne na plain, ak Markdown zlyhá
    print("✅ Sent to Telegram")

if __name__ == "__main__":
    main()
