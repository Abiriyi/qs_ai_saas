from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect, render

from core.forms import OrganizationSignupForm, ProjectIntakeForm, UserLoginForm


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


def auth_page(request):
    mode = request.GET.get("mode", "login")
    if mode not in {"login", "signup"}:
        mode = "login"

    login_form = UserLoginForm(request, data=request.POST or None, prefix="login")
    signup_form = OrganizationSignupForm(request.POST or None, prefix="signup")

    if request.method == "POST" and "login_submit" in request.POST:
        if login_form.is_valid():
            user = login_form.get_user()
            login(request, user)
            messages.success(request, "Welcome back to QS AI.")
            return redirect("dashboard")

    if request.method == "POST" and "signup_submit" in request.POST:
        if signup_form.is_valid():
            user = signup_form.save()
            login(request, user)
            messages.success(request, "Your workspace is ready.")
            return redirect("dashboard")

    return render(
        request,
        "auth.html",
        {
            "page_title": "Sign in | QS AI",
            "mode": mode,
            "login_form": login_form,
            "signup_form": signup_form,
        },
    )


def dashboard(request):
    summary_cards = [
        {"label": "Open projects", "value": "12", "delta": "+3 this week"},
        {"label": "AI estimate accuracy", "value": "96.4%", "delta": "+1.8% vs last month"},
        {"label": "Pending reviews", "value": "4", "delta": "2 ready for signoff"},
        {"label": "Monthly spend", "value": "$24.8K", "delta": "Within budget"},
    ]

    projects = [
        {"name": "North Tower Residences", "status": "In review", "status_class": "warning", "last_update": "2 hours ago", "value": "$1.42M"},
        {"name": "Harbor Logistics Hub", "status": "Approved", "status_class": "success", "last_update": "Today", "value": "$2.18M"},
        {"name": "Market Street Retail", "status": "Processing", "status_class": "info", "last_update": "5 hours ago", "value": "$890K"},
    ]

    return render(
        request,
        "dashboard.html",
        {
            "page_title": "Dashboard | QS AI",
            "summary_cards": summary_cards,
            "projects": projects,
        },
    )


def project_workflow(request):
    form = ProjectIntakeForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.warning(request, "Please sign in to create a project.")
            return redirect("login")

        if form.is_valid():
            project = form.save(request.user)
            messages.success(request, f"Project '{project.name}' created.")
            return redirect("dashboard")

    return render(
        request,
        "project_workflow.html",
        {
            "page_title": "Project intake | QS AI",
            "form": form,
        },
    )
