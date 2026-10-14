# tribunal/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from projects.models import Project
from tribunal.models import TribunalCase, TribunalCaseStatus, TribunalDecision
from tribunal.services import TribunalError, TribunalService


@login_required(login_url="login")
def tribunal_dashboard(request):
    """List all tribunal cases for the current organization."""
    cases = TribunalCase.objects.filter(
        organization=request.user.organization
    ).select_related("project", "boq", "raised_by", "decided_by")

    context = {
        "page_title": "Tribunal | QS AI",
        "cases": cases,
        "open_count": cases.filter(
            status__in=[TribunalCaseStatus.OPEN, TribunalCaseStatus.UNDER_REVIEW]
        ).count(),
        "decided_count": cases.filter(status=TribunalCaseStatus.DECIDED).count(),
    }
    return render(request, "tribunal.html", context)


@login_required(login_url="login")
def tribunal_case_detail(request, pk):
    """Show a single case and handle ruling / withdrawal form posts."""
    case = get_object_or_404(
        TribunalCase.objects.filter(organization=request.user.organization)
        .select_related("project", "boq", "raised_by", "decided_by"),
        id=pk,
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "assign":
            TribunalService.assign(case, request.user)
            messages.info(request, "Case is now under review.")
            return redirect("tribunal_case_detail", pk=case.pk)

        if action == "decide":
            decision = request.POST.get("decision")
            notes = (request.POST.get("decision_notes") or "").strip()
            try:
                TribunalService.decide(
                    case=case,
                    decision=decision,
                    decided_by=request.user,
                    notes=notes,
                )
                messages.success(request, "Ruling recorded.")
            except TribunalError as exc:
                messages.error(request, str(exc))
            return redirect("tribunal_case_detail", pk=case.pk)

        if action == "withdraw":
            try:
                TribunalService.withdraw(case, request.user)
                messages.warning(request, "Case withdrawn.")
            except TribunalError as exc:
                messages.error(request, str(exc))
            return redirect("tribunal_case_detail", pk=case.pk)

    context = {
        "page_title": f"Case {case.reference} | Tribunal",
        "case": case,
        "decisions": TribunalDecision.choices,
    }
    return render(request, "tribunal_case_detail.html", context)
