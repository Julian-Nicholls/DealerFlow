(() => {
  const root = document.getElementById("replay-root");
  if (!root) return;

  const slider = document.getElementById("day-slider");
  const play = document.getElementById("play-button");
  const speed = document.getElementById("speed-select");
  const dateEl = document.getElementById("replay-date");
  const dayEl = document.getElementById("day-value");
  const activeEl = document.getElementById("active-movements");
  const backlogEl = document.getElementById("network-backlog");
  const quotaEl = document.getElementById("quota-used");
  const eventEl = document.getElementById("event-list");
  const inspector = document.getElementById("inspector");
  const inspectorTitle = document.getElementById("inspector-title");
  const inspectorBody = document.getElementById("inspector-body");
  const inspectorClose = document.getElementById("inspector-close");

  let payload;
  let map;
  let movementLayer;
  let routeLayer;
  let effectLayer;
  let playing = false;
  let day = 0;
  let lastFrame = null;
  let lastRenderedDay = 0;
  let locations = {};
  let dealerMarkers = new Map();

  const iconForMode = {
    OCEAN_RORO: "🚢",
    RAIL_AUTORACK: "🚆",
    TRUCK_CARRIER: "🚚",
  };
  const iconForKind = {
    FACTORY: "🏭",
    EXPORT_PORT: "⚓",
    IMPORT_PORT: "⚓",
    REGIONAL_COMPOUND: "🏗️",
    DEALER: "🏬",
  };
  const colorForMode = {
    OCEAN_RORO: "#6ea8ff",
    RAIL_AUTORACK: "#f3c969",
    TRUCK_CARRIER: "#43d3a3",
  };

  const esc = (value) => String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");

  const waitForLeaflet = () => new Promise((resolve, reject) => {
    let tries = 0;
    const timer = setInterval(() => {
      if (window.L && L.maplibreGL) {
        clearInterval(timer);
        resolve();
      } else if (++tries > 120) {
        clearInterval(timer);
        reject(new Error("Map libraries failed to load"));
      }
    }, 50);
  });

  const dateFor = (value) => {
    const result = new Date(payload.run.start_date + "T00:00:00Z");
    result.setUTCDate(result.getUTCDate() + Math.floor(value));
    return result.toLocaleDateString("en-CA", {
      timeZone: "UTC",
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const backlogAt = (value) => {
    const result = new Map();
    for (const event of payload.pressure_events) {
      if (event.day > value) break;
      result.set(
        event.dealer_id,
        Math.max(0, (result.get(event.dealer_id) || 0) + event.delta),
      );
    }
    return result;
  };

  const quotaAt = (value) => {
    let usage = 0;
    for (const point of payload.quota_series) {
      if (point.day > value) break;
      usage = point.external_usage;
    }
    return usage;
  };

  const fixedIcon = (emoji, kind) => L.divIcon({
    className: "df-fixed-icon",
    html: `<div class="fixed-badge fixed-${kind.toLowerCase()}">${emoji}</div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 16],
  });

  const movingIcon = (emoji, count) => L.divIcon({
    className: "df-moving-icon",
    html: `<div class="moving-badge">${emoji}<span>${count > 1 ? count : ""}</span></div>`,
    iconSize: [42, 42],
    iconAnchor: [21, 21],
  });

  function unwrappedRoute(route) {
    if (!route?.length) return [];
    const output = [[route[0][0], route[0][1]]];
    let previousLng = route[0][1];
    for (let i = 1; i < route.length; i += 1) {
      let lng = route[i][1];
      while (lng - previousLng > 180) lng -= 360;
      while (lng - previousLng < -180) lng += 360;
      output.push([route[i][0], lng]);
      previousLng = lng;
    }
    return output;
  }

  function routePosition(route, progress) {
    const points = unwrappedRoute(route);
    if (!points.length) return null;
    if (points.length === 1) return points[0];

    const segments = [];
    let total = 0;
    for (let i = 1; i < points.length; i += 1) {
      const a = points[i - 1];
      const b = points[i];
      const meanLat = ((a[0] + b[0]) / 2) * Math.PI / 180;
      const dy = b[0] - a[0];
      const dx = (b[1] - a[1]) * Math.cos(meanLat);
      const length = Math.hypot(dx, dy);
      segments.push({ a, b, length });
      total += length;
    }

    let target = Math.max(0, Math.min(1, progress)) * total;
    for (const segment of segments) {
      if (target <= segment.length || segment === segments.at(-1)) {
        const t = segment.length ? target / segment.length : 0;
        return [
          segment.a[0] + (segment.b[0] - segment.a[0]) * t,
          segment.a[1] + (segment.b[1] - segment.a[1]) * t,
        ];
      }
      target -= segment.length;
    }
    return points.at(-1);
  }

  function renderRoute(movement) {
    if (!movement.route?.length) return;
    L.polyline(unwrappedRoute(movement.route), {
      color: colorForMode[movement.mode] || "#8ea3bf",
      weight: movement.mode === "TRUCK_CARRIER" ? 1.2 : 1.8,
      opacity: .28,
      dashArray: movement.mode === "OCEAN_RORO" ? "8 8" : "4 6",
      interactive: false,
    }).addTo(routeLayer);
  }

  function pausePlayback() {
    playing = false;
    lastFrame = null;
    play.textContent = "Play";
  }

  function configurationLabel(item) {
    const config = item.configuration || {};
    return [config.model, config.trim, config.exterior_colour]
      .filter(Boolean)
      .join(" · ") || item.configuration_id || "Unknown configuration";
  }

  function mixTable(rows) {
    if (!rows?.length) return '<p class="subtle">No vehicles present.</p>';
    return `<div class="inspect-table"><div class="inspect-row inspect-head"><span>Configuration</span><strong>Units</strong></div>${rows.map((row) => {
      const config = row.configuration || {};
      const label = [config.model, config.trim, config.exterior_colour]
        .filter(Boolean).join(" · ") || row.configuration_id;
      return `<div class="inspect-row"><span>${esc(label)}</span><strong>${row.count}</strong></div>`;
    }).join("")}</div>`;
  }

  function vehicleRows(rows) {
    if (!rows?.length) return "";
    return `<div class="vehicle-list"><h4>Vehicles</h4>${rows.slice(0, 80).map((item) => `
      <button type="button" class="vin-row" data-vin="${esc(item.vin)}">
        <span class="mono">${esc(item.vin)}</span>
        <small>${esc(configurationLabel(item))}</small>
      </button>`).join("")}</div>`;
  }

  function renderInspector(data) {
    inspector.hidden = false;

    if (data.missing) {
      inspectorTitle.textContent = data.id || "Unavailable";
      inspectorBody.innerHTML = '<p class="subtle">This entity did not exist at the selected simulation time.</p>';
      return;
    }

    if (data.kind === "shipment") {
      const mode = (data.mode || "Shipment").replaceAll("_", " ");
      inspectorTitle.textContent = `${iconForMode[data.mode] || "•"} ${data.id}`;
      inspectorBody.innerHTML = `
        <div class="inspect-summary">
          <div><span>Status</span><strong>${esc(data.status)}</strong></div>
          <div><span>Mode</span><strong>${esc(mode)}</strong></div>
          <div><span>Vehicles</span><strong>${data.vehicle_count}</strong></div>
          <div><span>Destination</span><strong>${esc(locations[data.destination_id]?.name || data.destination_id)}</strong></div>
        </div>
        <h4>Configuration mix</h4>
        ${mixTable(data.configuration_mix)}
        ${vehicleRows(data.vehicles)}
        ${data.vehicle_list_truncated ? '<p class="subtle">Vehicle list truncated for display.</p>' : ""}
      `;
      return;
    }

    if (data.kind === "location") {
      inspectorTitle.textContent = `${iconForKind[data.kind === "location" ? data.kind : data.kind] || iconForKind[data.kind] || iconForKind[data.id] || "📍"} ${data.name}`;
      const dealerStats = data.backlog_units !== undefined ? `
        <div class="inspect-summary">
          <div><span>On hand</span><strong>${data.vehicle_count}</strong></div>
          <div><span>Allocated inbound</span><strong>${data.inbound_allocated}</strong></div>
          <div><span>Open orders</span><strong>${data.open_order_units}</strong></div>
          <div><span>Backlog</span><strong>${data.backlog_units}</strong></div>
        </div>` : `
        <div class="inspect-summary"><div><span>Vehicles present</span><strong>${data.vehicle_count}</strong></div></div>`;
      inspectorBody.innerHTML = `
        ${dealerStats}
        <h4>Configuration mix</h4>
        ${mixTable(data.configuration_mix)}
        ${vehicleRows(data.vehicles)}
        ${data.vehicle_list_truncated ? '<p class="subtle">Vehicle list truncated for display.</p>' : ""}
      `;
      return;
    }

    if (data.kind === "vin") {
      const config = data.configuration || {};
      inspectorTitle.textContent = data.vin;
      inspectorBody.innerHTML = `
        <button type="button" class="inspector-back">← Back</button>
        <div class="vin-hero">
          <span>${esc(config.model || "Vehicle")}</span>
          <strong>${esc(config.trim || data.configuration_id)}</strong>
          <small>${esc([config.exterior_colour, config.interior_colour].filter(Boolean).join(" / "))}</small>
        </div>
        <div class="inspect-summary">
          <div><span>Physical state</span><strong>${esc(data.logistics_status)}</strong></div>
          <div><span>Allocation</span><strong>${esc(data.allocation_status)}</strong></div>
          <div><span>Dealer</span><strong>${esc(locations[data.allocated_dealer_id]?.name || data.allocated_dealer_id || "Unallocated")}</strong></div>
          <div><span>Location</span><strong>${esc(locations[data.location_id]?.name || data.location_id || data.shipment_id || "In transit")}</strong></div>
        </div>
        <h4>Event history</h4>
        <div class="history-list">${(data.history || []).map((event) => `
          <div><strong>Day ${Number(event.simulation_day).toFixed(1)}</strong><span>${esc(event.event_type.replaceAll("_", " "))}</span></div>
        `).join("") || '<p class="subtle">No history at this point in the run.</p>'}</div>
      `;
    }
  }

  let priorSelection = null;

  async function inspectEntity(type, id, remember = true) {
    pausePlayback();
    if (remember && type !== "vin") priorSelection = { type, id };
    inspector.hidden = false;
    inspectorTitle.textContent = "Loading…";
    inspectorBody.innerHTML = '<p class="subtle">Reconstructing state at this simulation time…</p>';

    const query = new URLSearchParams({
      type,
      id,
      day: day.toFixed(3),
    });
    const response = await fetch(`${root.dataset.inspectUrl}?${query}`);
    if (!response.ok) {
      inspectorTitle.textContent = "Inspector unavailable";
      inspectorBody.textContent = `Request failed: ${response.status}`;
      return;
    }
    renderInspector(await response.json());
  }

  inspectorClose.addEventListener("click", () => {
    inspector.hidden = true;
    priorSelection = null;
  });

  inspectorBody.addEventListener("click", (event) => {
    const vinButton = event.target.closest("[data-vin]");
    if (vinButton) {
      inspectEntity("vin", vinButton.dataset.vin, false);
      return;
    }
    if (event.target.closest(".inspector-back") && priorSelection) {
      inspectEntity(priorSelection.type, priorSelection.id, false);
    }
  });

  function salesBetween(a, b) {
    if (!payload.sales || b <= a) return;
    const counts = new Map();
    for (const sale of payload.sales) {
      if (sale.day <= a) continue;
      if (sale.day > b) break;
      if (!sale.dealer_id) continue;
      counts.set(sale.dealer_id, (counts.get(sale.dealer_id) || 0) + 1);
    }
    for (const [id, count] of counts) {
      const location = locations[id];
      if (!location) continue;
      const icon = L.divIcon({
        className: "df-sale-icon",
        html: `<div class="sale-burst">${count === 1 ? "$" : `$ × ${count}`}</div>`,
        iconSize: [70, 34],
        iconAnchor: [35, 17],
      });
      const marker = L.marker([location.latitude, location.longitude], {
        icon,
        interactive: false,
      }).addTo(effectLayer);
      setTimeout(() => {
        if (effectLayer.hasLayer(marker)) effectLayer.removeLayer(marker);
      }, 900);
    }
  }

  function render() {
    slider.value = day;
    dayEl.textContent = day.toFixed(1);
    dateEl.textContent = dateFor(day);

    const backlog = backlogAt(day);
    let totalBacklog = 0;
    for (const value of backlog.values()) totalBacklog += value;
    backlogEl.textContent = totalBacklog.toLocaleString();
    quotaEl.textContent = quotaAt(day).toLocaleString();

    for (const [id, marker] of dealerMarkers) {
      const value = backlog.get(id) || 0;
      marker.setTooltipContent(`${locations[id].name}<br>Backlog: ${value}`);
      marker.getElement()?.style.setProperty("--pressure", String(Math.min(1, value / 12)));
    }

    movementLayer.clearLayers();
    let active = 0;
    for (const movement of payload.movements) {
      if (day < movement.start_day || day > movement.end_day) continue;
      const duration = Math.max(.001, movement.end_day - movement.start_day);
      const progress = (day - movement.start_day) / duration;
      const position = routePosition(movement.route, progress);
      if (!position) continue;

      active += movement.count;
      const marker = L.marker(position, {
        icon: movingIcon(iconForMode[movement.mode] || "•", movement.count),
        zIndexOffset: 500,
      })
        .bindTooltip(`${movement.id}<br>${movement.mode.replaceAll("_", " ")} · ${movement.count} vehicles`)
        .on("click", () => inspectEntity("shipment", movement.id))
        .addTo(movementLayer);
      marker._dealerflowMovement = movement;
    }
    activeEl.textContent = active.toLocaleString();

    const visibleMarkers = payload.markers
      .filter((marker) => marker.day <= day)
      .slice(-6)
      .reverse();
    eventEl.innerHTML = visibleMarkers.length
      ? visibleMarkers.map((marker) => `<div class="event-item"><strong>Day ${marker.day.toFixed(1)}</strong>${esc(marker.type.replaceAll("_", " "))}</div>`).join("")
      : '<p class="subtle">No major marker yet.</p>';

    salesBetween(lastRenderedDay, day);
    lastRenderedDay = day;
  }

  function tick(timestamp) {
    if (!playing) return;
    if (lastFrame === null) lastFrame = timestamp;
    day += ((timestamp - lastFrame) / 1000) * Number(speed.value);
    lastFrame = timestamp;

    if (day >= payload.run.duration_days) {
      day = payload.run.duration_days;
      pausePlayback();
    }
    render();
    if (playing) requestAnimationFrame(tick);
  }

  play.addEventListener("click", () => {
    if (day >= payload.run.duration_days) {
      day = 0;
      lastRenderedDay = 0;
    }
    playing = !playing;
    play.textContent = playing ? "Pause" : "Play";
    lastFrame = null;
    if (playing) requestAnimationFrame(tick);
  });

  slider.addEventListener("input", () => {
    pausePlayback();
    day = Number(slider.value);
    lastRenderedDay = day;
    effectLayer.clearLayers();
    render();
  });

  Promise.all([
    waitForLeaflet(),
    fetch(root.dataset.apiUrl).then((response) => {
      if (!response.ok) throw new Error(`Replay API ${response.status}`);
      return response.json();
    }),
  ]).then(([, data]) => {
    payload = data;
    locations = Object.fromEntries(data.locations.map((item) => [item.id, item]));

    map = L.map("map", { worldCopyJump: true }).setView([50, -103], 4);
    L.maplibreGL({
      style: "https://tiles.openfreemap.org/styles/liberty",
    }).addTo(map);

    routeLayer = L.layerGroup().addTo(map);
    movementLayer = L.layerGroup().addTo(map);
    effectLayer = L.layerGroup().addTo(map);

    const bounds = [];
    for (const location of data.locations) {
      const emoji = iconForKind[location.kind] || "•";
      const marker = L.marker(
        [location.latitude, location.longitude],
        { icon: fixedIcon(emoji, location.kind), zIndexOffset: 200 },
      )
        .bindTooltip(location.name)
        .on("click", () => inspectEntity("location", location.id))
        .addTo(map);

      if (location.kind === "DEALER") dealerMarkers.set(location.id, marker);
      if (location.longitude < -40) bounds.push([location.latitude, location.longitude]);
    }

    for (const movement of data.movements) renderRoute(movement);
    if (bounds.length) map.fitBounds(bounds, { padding: [30, 30] });

    slider.max = data.run.duration_days;
    slider.disabled = false;
    play.disabled = false;
    speed.disabled = false;
    render();
  }).catch((error) => {
    dateEl.textContent = "Replay unavailable";
    eventEl.textContent = error.message;
  });
})();
