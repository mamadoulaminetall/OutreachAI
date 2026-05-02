import os
from datetime import datetime, timedelta
from collections import defaultdict


def _client():
    key = os.environ.get("STRIPE_API_KEY", "")
    if not key:
        return None
    try:
        import stripe
        stripe.api_key = key
        return stripe
    except ImportError:
        return None


def get_revenue(days: int = 30) -> dict:
    s = _client()
    if s is None:
        return {"demo": True}

    since = int((datetime.now() - timedelta(days=days)).timestamp())
    try:
        intents = s.PaymentIntent.list(created={"gte": since}, limit=100)
        total = 0.0
        by_day: dict = defaultdict(float)
        recent = []

        for pi in intents.auto_paging_iter():
            if pi.status == "succeeded" and pi.amount:
                amount = pi.amount / 100
                total += amount
                day = datetime.fromtimestamp(pi.created).strftime("%Y-%m-%d")
                by_day[day] += amount
                recent.append({
                    "date": day,
                    "amount": amount,
                    "currency": pi.currency.upper(),
                    "description": pi.description or "—",
                })

        return {
            "total": round(total, 2),
            "by_day": dict(sorted(by_day.items())),
            "recent": recent[:20],
            "demo": False,
        }
    except Exception as exc:
        return {"error": str(exc), "demo": True}


def get_subscriptions() -> dict:
    s = _client()
    if s is None:
        return {"demo": True, "active": 0, "mrr": 0.0}
    try:
        subs = s.Subscription.list(status="active", limit=100)
        mrr = 0.0
        for sub in subs.auto_paging_iter():
            for item in sub["items"]["data"]:
                price = item["price"]
                amount = (price.get("unit_amount") or 0) / 100
                interval = price.get("recurring", {}).get("interval", "month")
                if interval == "year":
                    amount /= 12
                mrr += amount
        return {"active": subs.total_count, "mrr": round(mrr, 2), "demo": False}
    except Exception as exc:
        return {"error": str(exc), "demo": True, "active": 0, "mrr": 0.0}
