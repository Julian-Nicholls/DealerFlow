from pathlib import Path

from django.conf import settings
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from .models import SimulationRun
from .services import build_replay_payload, inspect_entity, persist_scenario_run


def index(request):
    return render(
        request,
        "dashboard/index.html",
        {"runs": SimulationRun.objects.select_related("scenario").all()[:20]},
    )


@require_POST
def create_baseline_run(request):
    run = persist_scenario_run(
        Path(settings.DEALERFLOW_SCENARIO_DIR) / "quota_year_baseline.yaml"
    )
    return redirect("dashboard:run-detail", pk=run.pk)


def run_detail(request, pk: int):
    run = get_object_or_404(
        SimulationRun.objects.select_related("scenario"),
        pk=pk,
    )
    return render(request, "dashboard/run_detail.html", {"run": run})


@require_GET
def run_replay_api(request, pk: int):
    run = get_object_or_404(
        SimulationRun.objects.select_related("scenario"),
        pk=pk,
        status=SimulationRun.Status.COMPLETE,
    )
    return JsonResponse(build_replay_payload(run))


@require_GET
def run_inspect_api(request, pk: int):
    run = get_object_or_404(
        SimulationRun.objects.select_related("scenario"),
        pk=pk,
        status=SimulationRun.Status.COMPLETE,
    )

    entity_type = request.GET.get("type", "")
    entity_id = request.GET.get("id", "")
    if entity_type not in {"shipment", "location", "vin"} or not entity_id:
        return HttpResponseBadRequest("type must be shipment/location/vin and id is required")

    try:
        day = float(request.GET.get("day", "0"))
    except ValueError:
        return HttpResponseBadRequest("day must be numeric")

    duration = (run.end_date - run.start_date).days
    day = max(0.0, min(float(duration), day))
    return JsonResponse(inspect_entity(run, day, entity_type, entity_id))
