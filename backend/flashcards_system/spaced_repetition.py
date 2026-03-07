from datetime import datetime, timedelta

def update_card(card: dict, quality: int):

    if quality < 3:
        card["repetitions"] = 0
        card["interval"] = 1
    else:
        card["repetitions"] += 1

        if card["repetitions"] == 1:
            card["interval"] = 1
        elif card["repetitions"] == 2:
            card["interval"] = 6
        else:
            card["interval"] = int(card["interval"] * card["ease_factor"])

    card["ease_factor"] += (
        0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
    )

    if card["ease_factor"] < 1.3:
        card["ease_factor"] = 1.3

    card["next_review"] = (
        datetime.now() + timedelta(days=card["interval"])
    ).isoformat()

    return card