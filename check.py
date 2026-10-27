import os
import sys
import urllib.request

from playwright.sync_api import sync_playwright

# --- Einstellungen -----------------------------------------------------------
URL = (
    "https://shop.weeztix.com/accc4227-c0a8-11f1-8e27-d65b0659bc31/tickets"
    "?shop_code=r6k49zsq"
)

# Teil des Ticketnamens, nach dem auf der Seite gesucht wird (Kleinschreibung)
TICKET_KEYWORD = "last chance"

# Woerter, die bedeuten, dass das Ticket noch NICHT verfuegbar ist
SOLD_OUT_WORDS = [
    "ausverkauft",
    "sold out",
    "uitverkocht",
    "nicht verfügbar",
    "not available",
    "niet beschikbaar",
]

# Wie viele Zeichen nach dem Ticketnamen geprueft werden
SNIPPET_LENGTH = 250
# -----------------------------------------------------------------------------

NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "").strip()
TEST_NOTIFY = os.environ.get("TEST_NOTIFY", "").lower() == "true"


def notify(title: str, message: str) -> None:
    if not NTFY_TOPIC:
        print("FEHLER: Secret NTFY_TOPIC ist nicht gesetzt.")
        sys.exit(1)
    req = urllib.request.Request(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=message.encode("utf-8"),
        headers={
            "Title": title,
            "Priority": "urgent",
            "Tags": "tickets",
            "Click": URL,
        },
    )
    urllib.request.urlopen(req, timeout=15)
    print("Push-Nachricht gesendet.")


def load_page_text() -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(locale="de-DE")
        page.goto(URL, wait_until="load", timeout=60000)
        # Weeztix laedt die Tickets per JavaScript nach
        page.wait_for_timeout(8000)
        text = page.inner_text("body")
        browser.close()
    return text


def main() -> None:
    if TEST_NOTIFY:
        notify("Test: Ticket-Waechter", "Die Benachrichtigung funktioniert!")
        return

    text = load_page_text()
    print("----- Seitentext (Auszug) -----")
    print(text[:3000])
    print("-------------------------------")

    low = text.lower()
    if len(low.strip()) < 30:
        print("WARNUNG: Seite scheint nicht richtig geladen zu sein.")
        sys.exit(1)

    idx = low.find(TICKET_KEYWORD)
    if idx == -1:
        print(f"WARNUNG: '{TICKET_KEYWORD}' nicht auf der Seite gefunden.")
        sys.exit(1)

    snippet = low[idx : idx + SNIPPET_LENGTH]
    print(f"Gepruefter Abschnitt: {snippet!r}")

    if any(word in snippet for word in SOLD_OUT_WORDS):
        print("Status: noch ausverkauft.")
        return

    print("Status: MOEGLICHERWEISE VERFUEGBAR!")
    notify(
        "One Piece Tickets verfügbar!",
        "Beim Last Chance Qualifier steht nicht mehr 'ausverkauft'. "
        "Schnell den Shop öffnen!",
    )


if __name__ == "__main__":
    main()
