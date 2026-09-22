from pathlib import Path
from django.core.management.base import BaseCommand,CommandError
from dealerflow_web.dashboard.services import persist_scenario_run
class Command(BaseCommand):
    help="Run a DealerFlow YAML scenario and persist its events/KPIs."
    def add_arguments(self,parser): parser.add_argument("scenario",type=Path)
    def handle(self,*args,**options):
        path=options["scenario"]
        if not path.exists(): raise CommandError(f"Scenario not found: {path}")
        run=persist_scenario_run(path)
        self.stdout.write(self.style.SUCCESS(f"Run #{run.pk}: {run.event_count} events, digest {run.event_digest}"))
