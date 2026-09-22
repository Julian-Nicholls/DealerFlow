from __future__ import annotations
from datetime import UTC
from hashlib import sha256
from pathlib import Path
from django.db import transaction
from django.utils import timezone
from dealerflow.config import parse_scenario
from dealerflow.simulation import DealerFlowSimulation
from .models import ScenarioRecord,SimulationEventRecord,SimulationRun

def persist_scenario_run(path:Path)->SimulationRun:
    source=path.read_text(encoding="utf-8"); cfg=parse_scenario(source)
    digest=sha256(source.encode()).hexdigest()
    scenario,_=ScenarioRecord.objects.get_or_create(content_sha256=digest,defaults={"name":cfg.name,"source_path":str(path),"source_yaml":source})
    run=SimulationRun.objects.create(scenario=scenario,status=SimulationRun.Status.RUNNING,seed=cfg.seed,start_date=cfg.start_date,end_date=cfg.end_date)
    try:
        result=DealerFlowSimulation(cfg).run()
        rows=[]
        for e in result.events:
            dt=e.timestamp if e.timestamp.tzinfo else e.timestamp.replace(tzinfo=UTC)
            rows.append(SimulationEventRecord(run=run,sequence=e.event_id,simulation_day=e.simulation_day,occurred_at=dt,event_type=e.event_type,entity_type=e.entity_type,entity_id=e.entity_id,location_id=e.location_id or "",correlation_id=e.correlation_id or "",payload=e.payload))
        with transaction.atomic():
            SimulationEventRecord.objects.bulk_create(rows,batch_size=1000)
            run.status=SimulationRun.Status.COMPLETE; run.event_digest=result.digest; run.event_count=len(rows); run.summary=result.summary; run.finished_at=timezone.now()
            run.save(update_fields=["status","event_digest","event_count","summary","finished_at"])
    except Exception as exc:
        run.status=SimulationRun.Status.FAILED; run.error=f"{type(exc).__name__}: {exc}"; run.finished_at=timezone.now()
        run.save(update_fields=["status","error","finished_at"]); raise
    return run

def build_replay_payload(run:SimulationRun)->dict:
    cfg=parse_scenario(run.scenario.source_yaml)
    locations={f.id:{"id":f.id,"name":f.name,"kind":f.kind,"latitude":f.latitude,"longitude":f.longitude} for f in cfg.facilities}
    for d in cfg.dealers:
        locations[d.id]={"id":d.id,"name":d.name,"kind":"DEALER","city":d.city,"province":d.province,"latitude":d.latitude,"longitude":d.longitude}

    events=list(run.events.order_by("sequence").values("simulation_day","event_type","entity_id","location_id","payload"))
    ocean={}; rail={}; truck={}; movements=[]; pressure=[]; markers=[]; quota=[]
    marker_types={"CHINA_ORDER_RECOMMENDED","VESSEL_ARRIVED","DISTURBANCE_STARTED","DISTURBANCE_ENDED","DISTURBANCE_APPLIED","QUOTA_BLOCKED"}
    for e in events:
        day=float(e["simulation_day"]); typ=e["event_type"]; eid=e["entity_id"]; p=e["payload"] or {}
        if typ=="STARTING_PIPELINE_REGISTERED" and p.get("expected_arrival_day") is not None:
            movements.append({"mode":"OCEAN_RORO","origin_id":"CHINA_EXPORT_PORT","destination_id":"VANCOUVER","start_day":-20.0,"end_day":float(p["expected_arrival_day"]),"count":int(p.get("vin_count",1))})
        elif typ=="VESSEL_DEPARTED": ocean[eid]=e
        elif typ=="VESSEL_ARRIVED" and eid in ocean:
            d=ocean.pop(eid); movements.append({"mode":"OCEAN_RORO","origin_id":d["location_id"] or "CHINA_EXPORT_PORT","destination_id":e["location_id"] or "VANCOUVER","start_day":float(d["simulation_day"]),"end_day":day,"count":int((d["payload"] or {}).get("vin_count",1))})
        elif typ=="RAIL_SHIPMENT_DEPARTED": rail[eid]=e
        elif typ=="RAIL_SHIPMENT_ARRIVED" and eid in rail:
            d=rail.pop(eid); movements.append({"mode":"RAIL_AUTORACK","origin_id":d["location_id"] or "VANCOUVER","destination_id":e["location_id"],"start_day":float(d["simulation_day"]),"end_day":day,"count":1})
        elif typ=="TRUCK_DEPARTED": truck[eid]=e
        elif typ=="VEHICLE_DELIVERED" and eid in truck:
            d=truck.pop(eid); dealer=p.get("dealer_id") or e["location_id"]; movements.append({"mode":"TRUCK_CARRIER","origin_id":d["location_id"],"destination_id":dealer,"start_day":float(d["simulation_day"]),"end_day":day,"count":1})
        elif typ=="BACKLOG_CREATED": pressure.append({"day":day,"dealer_id":eid,"delta":1})
        elif typ=="BACKLOG_FULFILLED": pressure.append({"day":day,"dealer_id":e["location_id"],"delta":-1})
        elif typ=="EXTERNAL_QUOTA_CONSUMED": quota.append({"day":day,"external_usage":int(p.get("external_usage",0))})
        if typ in marker_types: markers.append({"day":day,"type":typ,"entity_id":eid,"location_id":e["location_id"],"payload":p})

    # Aggregate domestic VIN movements into day/origin/destination batches for browser replay.
    grouped={}
    for m in movements:
        key=(m["mode"],int(m["start_day"]),m["origin_id"],m["destination_id"])
        g=grouped.setdefault(key,{**m,"start_sum":0.0,"end_sum":0.0,"count":0})
        c=m["count"]; g["start_sum"]+=m["start_day"]*c; g["end_sum"]+=m["end_day"]*c; g["count"]+=c
    out=[]
    for i,g in enumerate(grouped.values(),1):
        c=g["count"]; out.append({"id":f"MOV-{i:05d}","mode":g["mode"],"origin_id":g["origin_id"],"destination_id":g["destination_id"],"start_day":g["start_sum"]/c,"end_day":g["end_sum"]/c,"count":c})
    out.sort(key=lambda x:x["start_day"])
    return {"run":{"id":run.pk,"scenario":run.scenario.name,"start_date":run.start_date.isoformat(),"end_date":run.end_date.isoformat(),"duration_days":(run.end_date-run.start_date).days,"seed":run.seed,"digest":run.event_digest,"summary":run.summary},"locations":list(locations.values()),"movements":out,"pressure_events":pressure,"markers":markers,"quota_series":quota}
