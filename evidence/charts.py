"""Accessible chart geometry built from source values, with explicit series boundaries."""

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
            "MOCKED"
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
                source=f"{r['source_workbook']} · {r['source_sheet']}!{r['source_cell']}",
            )
            for r in series
        ]
        charts.append(
            bar_chart(
                f"{crop} · {MEASURE_LABELS[indicator]} · Season {season}",
                unit,
                points,
                f"Rwanda · {population.split(';')[0]}. Published observations; source details below.",
                scale_max=scales.get((indicator, crop, population, unit)),
            )
        )
    return charts, len(groups) > max_series
