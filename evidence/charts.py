"""Accessible chart geometry built from source values, with explicit series boundaries."""

import hashlib
from collections import OrderedDict
from decimal import Decimal, InvalidOperation

MEASURE_LABELS = {
    "production": "Production",
    "yield": "Yield",
    "improved_seeds": "Improved seed use",
    "inorganic_fertilizer": "Inorganic fertilizer use",
}


def bar_chart(title, unit, points, description="", scale_max=None):
    """Zero-baseline horizontal bars. Never mix units or turn missing data into zero."""
    bars = []
    for point in points:
        if point["unit"] != unit:
            raise ValueError("A chart cannot mix units")
        row = dict(point)
        try:
            number = (
                Decimal(str(point["value"])) if point.get("available", True) else None
            )
        except InvalidOperation:
            number = None
        if number is not None and (not number.is_finite() or number < 0):
            number = None
        row["number"] = number
        row["display"] = format(number, ",.2f") if number is not None else "Unavailable"
        row["state"] = (
            "MOCKED · Synthetic / illustrative — not official statistics."
            if row.get("mocked")
            else "Observed" if number is not None else "Unavailable"
        )
        bars.append(row)
    maximum = max(
        (b["number"] for b in bars if b["number"] is not None), default=Decimal(0)
    )
    if scale_max is not None:
        maximum = max(maximum, Decimal(str(scale_max)))
    scale = maximum or Decimal(1)
    for index, row in enumerate(bars):
        row["y"] = 28 + index * 42
        row["text_y"] = row["y"] + 17
        row["width"] = (
            float(row["number"] / scale * 430) if row["number"] is not None else 0
        )
        row["percent"] = row["width"] / 430 * 100
        row["zero"] = row["number"] == 0
        row["available"] = row["number"] is not None
        del row["number"]
    return dict(
        uid=hashlib.sha256((title + unit + description).encode()).hexdigest()[:12],
        title=title,
        unit=unit,
        description=description,
        bars=bars,
        height=75 + 42 * len(bars),
        axis_y=35 + 42 * len(bars),
        scale_label=format(maximum, ",.2f"),
        has_mock=any(r.get("mocked") for r in bars),
        numeric_count=sum(r["available"] for r in bars),
    )


def seasonal_charts(rows, max_series=4):
    """Compare years within the same season, crop, measure, population and unit."""
    groups = OrderedDict()
    # Prefer maize in broad selections; the chart title always names its scope.
    ordered = sorted(
        rows,
        key=lambda r: (
            r["crop"] != "Maize",
            r["indicator"],
            r["crop"],
            r["population"],
            r["period"],
        ),
    )
    for row in ordered:
        season = row["period"].split()[-1]
        key = (row["indicator"], row["crop"], row["population"], row["unit"], season)
        groups.setdefault(key, []).append(row)
    scales = {}
    for (indicator, crop, population, unit, season), series in groups.items():
        key = (indicator, crop, population, unit)
        for row in series:
            if row["status"] != "observed" and not row.get("mocked"):
                continue
            try:
                value = Decimal(str(row["value"]))
            except InvalidOperation:
                continue
            if value.is_finite() and value >= 0:
                scales[key] = max(scales.get(key, Decimal(0)), value)
    charts = []
    for (indicator, crop, population, unit, season), series in list(groups.items())[
        :max_series
    ]:
        points = [
            dict(
                label=r["period"].split()[0],
                value=r["value"],
                unit=unit,
                available=r["status"] == "observed" or r.get("mocked", False),
                mocked=r.get("mocked", False),
                source=("Synthetic / illustrative — not official statistics. Generated for APASA interface demonstration; original unavailable cell: " if r.get("mocked") else "") + f"{r['source_workbook']} · {r['source_sheet']}!{r['source_cell']}",
            )
            for r in series
        ]
        charts.append(
            bar_chart(
                f"{crop} · {MEASURE_LABELS[indicator]} · Season {season}",
                unit,
                points,
                f"Rwanda · {population.split(';')[0]}. " + ("Mixed view: published observations and separately labelled synthetic examples; source details below." if any(r.get("mocked") for r in series) else "Published observations; source details below."),
                scale_max=scales.get((indicator, crop, population, unit)),
            )
        )
    return charts, len(groups) > max_series


def grouped_season_chart(rows):
    """Front faces use a common zero baseline; decorative facets stay inside each bar."""
    if not rows:
        return None
    scope = {(r["crop"], r["indicator"], r["population"], r["unit"]) for r in rows}
    if len(scope) != 1:
        raise ValueError(
            "A seasonal comparison must have one crop, measure, population and unit"
        )
    crop, indicator, population, unit = next(iter(scope))
    years = sorted({r["period"].split()[0] for r in rows})
    seasons = sorted({r["period"].split()[-1] for r in rows})
    points = [
        dict(
            label=r["period"],
            value=r["value"],
            unit=unit,
            available=r["status"] == "observed",
            source=("Synthetic / illustrative — not official statistics. Generated for APASA interface demonstration; original unavailable cell: " if r.get("mocked") else "") + f"{r['source_workbook']} · {r['source_sheet']}!{r['source_cell']}",
            period=r["period"],
            season=r["period"].split()[-1],
        )
        for r in rows
    ]
    chart = bar_chart(
        f"{crop} production by season",
        unit,
        points,
        f"Rwanda · {population}. Published seasonal observations, not policy progress.",
    )
    maximum = max(
        (Decimal(str(r["value"])) for r in rows if r["status"] == "observed"),
        default=Decimal(0),
    )
    # Decimal ceiling produces legible axis ticks without changing observed values.
    from decimal import ROUND_CEILING

    desired = (maximum / 6) if maximum else Decimal("0.2")
    magnitude = Decimal(10) ** desired.adjusted()
    step = next(
        Decimal(n) * magnitude
        for n in (1, 2, 5, 10)
        if Decimal(n) * magnitude >= desired
    )
    divisions = max(1, int((maximum / step).to_integral_value(rounding=ROUND_CEILING)))
    limit = step * divisions
    for bar in chart["bars"]:
        year = bar["period"].split()[0]
        center = 90 + (years.index(year) + 0.5) * 740 / len(years)
        width = min(70, 600 / max(1, len(years) * len(seasons)))
        x = center + (seasons.index(bar["season"]) - len(seasons) / 2) * (width + 8) + 4
        height = (
            float(Decimal(str(bar["value"])) / limit * 280) if bar["available"] else 0
        )
        y = 320 - height
        facet = min(6, height)
        bar.update(
            percent=height / 280 * 100,
            x=x,
            column_y=y,
            column_width=width,
            column_height=height,
            value_y=max(21, y - 10),
            center=x + width / 2,
            top_face=f"{x},{y+facet} {x+facet},{y} {x+width},{y} {x+width-facet},{y+facet}",
            side_face=f"{x+width-facet},{y+facet} {x+width},{y} {x+width},320 {x+width-facet},320",
            season_class="season-" + str(seasons.index(bar["season"])),
        )
    chart["scale_label"] = format(limit, ",.2f")
    chart["ticks"] = [
        {
            "y": 320 - i * 280 / divisions,
            "label": format(step * i, ",.0f" if step >= 1 else ",.2f"),
        }
        for i in range(divisions + 1)
    ]
    chart["years"] = [
        {"x": 90 + (i + 0.5) * 740 / len(years), "label": y}
        for i, y in enumerate(years)
    ]
    chart["seasons"] = seasons
    return chart
