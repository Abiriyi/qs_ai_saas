from django.shortcuts import render


def home(request):
    features = [
        {
            "title": "Instant BoQ generation",
            "description": "Turn uploaded documents into structured Bill of Quantities in minutes.",
        },
        {
            "title": "AI pricing engine",
            "description": "Use rate libraries and confidence scoring to drive faster, auditable estimates.",
        },
        {
            "title": "Multi-tenant control",
            "description": "Manage organizations, users, and project boundaries with secure tenancy isolation.",
        },
    ]

    stats = [
        {"label": "Projects", "value": "1.2K+"},
        {"label": "Audit coverage", "value": "99.8%"},
        {"label": "Avg. turnaround", "value": "3.4x"},
    ]

    return render(
        request,
        "home.html",
        {
            "page_title": "QS AI SaaS",
            "features": features,
            "stats": stats,
        },
    )
