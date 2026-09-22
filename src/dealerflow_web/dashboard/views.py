from pathlib import Path
from django.conf import settings
from django.http import JsonResponse
from django.shortcuts import get_object_or_404,redirect,render
from django.views.decorators.http import require_POST
from .models import SimulationRun
from .services import build_replay_payload,persist_scenario_run

def index(request):
    return render(request,"dashboard/index.html",{"runs":SimulationRun.objects.select_related("scenario").all()[:20]})

@require_POST
def create_baseline_run(request):
    run=persist_scenario_run(Path(settings.DEALERFLOW_SCENARIO_DIR)/"quota_year_baseline.yaml")
    return redirect("dashboard:run-detail",pk=run.pk)

def run_detail(request,pk:int):
    return render(request,"dashboard/run_detail.html",{"run":get_object_or_404(SimulationRun.objects.select_related("scenario"),pk=pk)})

def run_replay_api(request,pk:int):
    run=get_object_or_404(SimulationRun.objects.select_related("scenario"),pk=pk,status=SimulationRun.Status.COMPLETE)
    return JsonResponse(build_replay_payload(run))
