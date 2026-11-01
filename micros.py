"""
Extra Cronometer tools: vitamins, minerals and other nutrients eaten on a day.

Sums every diary entry's food nutrients (per 100 g) scaled by its grams, and pairs
each nutrient with Cronometer's RDI. The "check" block compares the summed energy
with the diary's own calorie total so a wrong scale is easy to spot.
"""
from typing import Optional

import cronometer_mcp_server as s

_defs = None
_foods = {}


def _nutrient_defs(c, day):
    global _defs
    if _defs is None:
        data = c.get_nutrients(day)
        _defs = {n["id"]: n for n in data.get("nutrients", []) if "id" in n}
    return _defs


def _food(c, food_id):
    if food_id not in _foods:
        _foods[food_id] = c.get_food(food_id)
    return _foods[food_id]


# The scores endpoint needs a start/end day as well as the day.
s.CronoClient.get_nutrition_scores = lambda self, day: self._v2(
    "get_nutrition_scores", day=day, startDay=day, endDay=day)


@s.mcp.tool()
def get_daily_micros(date: Optional[str] = None) -> str:
    """Vitamins, minerals and other nutrients eaten on a date (YYYY-MM-DD, default today),
    summed from the diary, each with Cronometer's RDI and percent of RDI."""
    try:
        d = s._parse_date(date)
        c = s._get_client()
        diary = c.get_diary(d)
        entries = [e for e in diary.get("entries", []) if e.get("serving_id")]
        defs = _nutrient_defs(c, d)
        totals, debug = {}, {}
        for e in entries:
            f = _food(c, e["food_id"])
            nl = f.get("nutrients", []) or []
            if nl and "nutrient_keys" not in debug:
                debug["nutrient_keys"] = list(nl[0].keys())
                debug["food_keys"] = [k for k in f.keys() if k != "nutrients"]
            for n in nl:
                nid = n.get("nutrientId", n.get("id"))
                amt = n.get("amount", n.get("value"))
                if nid is None or amt is None:
                    continue
                totals[nid] = totals.get(nid, 0.0) + float(amt) * float(e.get("grams", 0)) / 100.0
        out = []
        for nid, amt in totals.items():
            df = defs.get(nid, {})
            rdi = df.get("rdi")
            out.append({
                "id": nid,
                "name": df.get("name", str(nid)),
                "category": df.get("category", ""),
                "unit": df.get("unit", ""),
                "amount": round(amt, 3),
                "rdi": rdi,
                "pct": round(100 * amt / rdi) if rdi else None,
            })
        out.sort(key=lambda x: (x["category"], x["name"]))
        energy = totals.get(208)
        return s._ok({
            "date": d,
            "nutrients": out,
            "check": {
                "computed_kcal": round(energy, 1) if energy is not None else None,
                "diary_kcal": diary.get("energy_summary", {}).get("consumed_kcal"),
            },
            "debug": debug,
        })
    except Exception as e:
        return s._err(e)
