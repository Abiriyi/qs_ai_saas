def compute_quantity_confidence(entries, context, requires):
    score = 1.0

    # geometry availability
    for r in requires:
        if hasattr(context, r):
            if getattr(context, r) in (None, 0):
                score *= 0.5
        else:
            if not any(e.get(r) for e in entries):
                score *= 0.5

    # context confidence
    score *= min(
        context.scale_confidence or 1.0,
        context.storey_height_confidence or 1.0
    )

    # source confidence
    if context.source == "ai":
        score *= 0.85
    elif context.source == "user":
        score *= 0.95
    elif context.source == "bim":
        score *= 1.0

    return round(score, 2)
