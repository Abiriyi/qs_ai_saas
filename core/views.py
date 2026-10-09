from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

from core.forms import OrganizationSignupForm, ProjectIntakeForm, UserLoginForm
from projects.models import Project


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


@login_required(login_url="login")
def dashboard(request):
    projects = (
        Project.objects.filter(organization=request.user.organization)
        .order_by("-updated_at")
        .only("id", "name", "status", "updated_at", "created_at")
    )

    status_map = {
        "draft": ("Draft", "warning"),
        "processing": ("Processing", "info"),
        "completed": ("Completed", "success"),
        "archived": ("Archived", "info"),
    }
    project_rows = []
    for project in projects:
        label, css_class = status_map.get(project.status, ("Draft", "warning"))
        project_rows.append(
            {
                "id": project.id,
                "name": project.name,
                "status": label,
                "status_class": css_class,
                "last_update": project.updated_at.strftime("%d %b %Y"),
                "value": "$0",
            }
        )

    open_projects = projects.filter(status__in=["draft", "processing"]).count()
    completed_projects = projects.filter(status="completed").count()
    summary_cards = [
        {"label": "Open projects", "value": str(open_projects), "delta": f"{completed_projects} completed"},
        {"label": "Workspace", "value": request.user.organization.name[:18], "delta": request.user.organization.subscription_plan.title()},
        {"label": "Recent reviews", "value": str(min(4, len(project_rows))), "delta": "Ready for signoff"},
        {"label": "Projects", "value": str(projects.count()), "delta": "Across this tenant"},
    ]

    return render(
        request,
        "dashboard.html",
        {
            "page_title": "Dashboard | QS AI",
            "summary_cards": summary_cards,
            "projects": project_rows,
            "workspace_name": request.user.organization.name,
        },
    )


@login_required(login_url="login")
def project_workflow(request):
    form = ProjectIntakeForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            project = form.save(request.user)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": True,
                        "project_id": str(project.id),
                        "project_name": project.name,
                    }
                )
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
