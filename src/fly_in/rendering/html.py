"""Generate an interactive HTML view of a route schedule."""

import json
from pathlib import Path

from fly_in.models import Map
from fly_in.routing import RouteSchedule, Transit


_HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="icon" href="data:,">
  <title>Fly-in Route Visualizer</title>
  <style>
    :root {
      color-scheme: dark;
      font-family: Inter, ui-sans-serif, system-ui, sans-serif;
      background: #07111f;
      color: #e7eef8;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      background:
        radial-gradient(circle at 20% 0%, #17345a 0, transparent 38%),
        #07111f;
    }

    main {
      width: min(1180px, calc(100% - 32px));
      margin: 0 auto;
      padding: 32px 0;
    }

    header {
      display: flex;
      align-items: end;
      justify-content: space-between;
      gap: 24px;
      margin-bottom: 18px;
    }

    h1 {
      margin: 0;
      font-size: clamp(28px, 4vw, 44px);
      letter-spacing: -0.04em;
    }

    .subtitle {
      margin: 6px 0 0;
      color: #91a5be;
    }

    .turn-card {
      min-width: 150px;
      padding: 12px 16px;
      border: 1px solid #29405e;
      border-radius: 14px;
      background: #0d1c2fcc;
      text-align: right;
    }

    #turn-label {
      display: block;
      font-size: 20px;
      font-weight: 700;
    }

    #delivery-label {
      color: #91a5be;
      font-size: 13px;
    }

    .stage {
      overflow: hidden;
      border: 1px solid #29405e;
      border-radius: 22px;
      background: #0a1728e8;
      box-shadow: 0 24px 70px #0008;
    }

    .canvas {
      overflow: auto;
      max-height: 70vh;
      scrollbar-color: #405776 #0a1728;
    }

    svg {
      display: block;
      width: auto;
    }

    .connection {
      stroke: #405776;
      stroke-width: 4;
      stroke-linecap: round;
    }

    .capacity {
      fill: #7790ae;
      font-size: 12px;
      text-anchor: middle;
    }

    .zone {
      stroke: #d9e7f8;
      stroke-width: 3;
      filter: drop-shadow(0 6px 12px #0008);
    }

    .zone.blocked {
      stroke-dasharray: 5 4;
      opacity: 0.55;
    }

    .zone.restricted {
      stroke-width: 5;
    }

    .zone.priority {
      stroke: #f8d66d;
    }

    .zone-name {
      fill: #e7eef8;
      font-size: 14px;
      font-weight: 650;
      text-anchor: middle;
    }

    .zone-type {
      fill: #8da3bd;
      font-size: 11px;
      text-anchor: middle;
    }

    .drone circle {
      fill: #f7fbff;
      stroke: #07111f;
      stroke-width: 3;
      filter: drop-shadow(0 5px 8px #0009);
    }

    .drone text {
      fill: #07111f;
      font-size: 11px;
      font-weight: 800;
      text-anchor: middle;
      dominant-baseline: central;
    }

    .controls {
      display: grid;
      grid-template-columns: auto minmax(180px, 1fr) auto;
      align-items: center;
      gap: 10px;
      padding: 16px;
      border-top: 1px solid #29405e;
    }

    .playback,
    .zoom-controls {
      display: flex;
      align-items: center;
      gap: 10px;
    }

    .zoom-controls input {
      width: 120px;
    }

    #zoom-label {
      min-width: 46px;
      color: #91a5be;
      font-size: 13px;
      text-align: right;
    }

    button {
      min-height: 42px;
      padding: 0 16px;
      border: 1px solid #365172;
      border-radius: 11px;
      background: #142942;
      color: #e7eef8;
      cursor: pointer;
      font: inherit;
      font-weight: 650;
    }

    button:hover {
      background: #1c3859;
    }

    button:focus-visible,
    input:focus-visible {
      outline: 3px solid #62b5ff;
      outline-offset: 2px;
    }

    input[type="range"] {
      width: 100%;
      accent-color: #62b5ff;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 12px 20px;
      margin-top: 14px;
      color: #9bb0c9;
      font-size: 13px;
    }

    .legend span {
      display: inline-flex;
      align-items: center;
      gap: 7px;
    }

    .swatch {
      width: 12px;
      height: 12px;
      border: 2px solid #d9e7f8;
      border-radius: 50%;
      background: #34506f;
    }

    .swatch.priority {
      border-color: #f8d66d;
    }

    .swatch.restricted {
      border-width: 4px;
    }

    .swatch.blocked {
      border-style: dashed;
      opacity: 0.55;
    }

    @media (max-width: 700px) {
      header {
        align-items: start;
        flex-direction: column;
      }

      .turn-card {
        width: 100%;
        text-align: left;
      }

      .controls {
        grid-template-columns: 1fr;
      }

      .playback,
      .zoom-controls {
        justify-content: center;
      }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <div>
        <h1>Fly-in Route Visualizer</h1>
        <p class="subtitle">Drone movement through the network</p>
      </div>
      <div class="turn-card" aria-live="polite">
        <span id="turn-label"></span>
        <span id="delivery-label"></span>
      </div>
    </header>

    <section class="stage" aria-label="Drone route visualization">
      <div class="canvas">
        <svg id="network" role="img"></svg>
      </div>
      <div class="controls">
        <div class="playback">
          <button id="previous" type="button">Previous</button>
          <button id="play" type="button">Play</button>
          <button id="next" type="button">Next</button>
        </div>
        <input id="turn" type="range" min="0" value="0"
          aria-label="Simulation turn">
        <div class="zoom-controls">
          <button id="zoom-out" type="button" aria-label="Zoom out">
            −
          </button>
          <input id="zoom" type="range" min="0.01" max="2"
            step="0.01" value="1" aria-label="Map zoom">
          <button id="zoom-in" type="button" aria-label="Zoom in">
            +
          </button>
          <button id="fit" type="button">Fit</button>
          <span id="zoom-label"></span>
        </div>
      </div>
    </section>

    <div class="legend" aria-label="Zone type legend">
      <span><i class="swatch"></i>normal</span>
      <span><i class="swatch priority"></i>priority</span>
      <span><i class="swatch restricted"></i>restricted</span>
      <span><i class="swatch blocked"></i>blocked</span>
    </div>
  </main>

  <script>
    const simulation = __SIMULATION_DATA__;
    const svg = document.querySelector("#network");
    const canvas = document.querySelector(".canvas");
    const turnInput = document.querySelector("#turn");
    const zoomInput = document.querySelector("#zoom");
    const zoomLabel = document.querySelector("#zoom-label");
    const turnLabel = document.querySelector("#turn-label");
    const deliveryLabel = document.querySelector("#delivery-label");
    const playButton = document.querySelector("#play");
    const zoneByName = new Map(
      simulation.zones.map(zone => [zone.name, zone])
    );
    const positions = new Map();
    const padding = 120;
    const horizontalSpacing = 165;
    const verticalSpacing = 175;
    let currentTurn = 0;
    let currentZoom = 1;
    let fitMode = true;
    let timer = null;

    const xValues = simulation.zones.map(zone => zone.x);
    const yValues = simulation.zones.map(zone => zone.y);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const minY = Math.min(...yValues);
    const maxY = Math.max(...yValues);
    const width = Math.max(
      1000,
      (maxX - minX) * horizontalSpacing + padding * 2
    );
    const height = Math.max(
      620,
      (maxY - minY) * verticalSpacing + padding * 2
    );
    svg.setAttribute("viewBox", `0 0 ${width} ${height}`);

    function scale(value, minimum, maximum, start, end) {
      if (minimum === maximum) {
        return (start + end) / 2;
      }

      return start + (value - minimum) * (end - start)
        / (maximum - minimum);
    }

    function element(name, attributes = {}) {
      const node = document.createElementNS(
        "http://www.w3.org/2000/svg",
        name
      );

      for (const [key, value] of Object.entries(attributes)) {
        node.setAttribute(key, String(value));
      }

      return node;
    }

    function applyZoom(value, preserveCenter = true) {
      const centerX = (
        canvas.scrollLeft + canvas.clientWidth / 2
      ) / (width * currentZoom);
      const centerY = (
        canvas.scrollTop + canvas.clientHeight / 2
      ) / (height * currentZoom);
      currentZoom = Math.max(0.01, Math.min(2, value));
      svg.setAttribute("width", String(width * currentZoom));
      svg.setAttribute("height", String(height * currentZoom));
      zoomInput.value = String(currentZoom);
      zoomLabel.textContent = `${Math.round(currentZoom * 100)}%`;

      if (preserveCenter) {
        canvas.scrollLeft = centerX * width * currentZoom
          - canvas.clientWidth / 2;
        canvas.scrollTop = centerY * height * currentZoom
          - canvas.clientHeight / 2;
      }
    }

    function fitMap() {
      fitMode = true;
      applyZoom(Math.min(1, canvas.clientWidth / width), false);
      canvas.scrollLeft = 0;
      canvas.scrollTop = 0;
    }

    function changeZoom(multiplier) {
      fitMode = false;
      applyZoom(currentZoom * multiplier);
    }

    function positionForZone(name) {
      return positions.get(name);
    }

    function drawMap() {
      for (const zone of simulation.zones) {
        positions.set(zone.name, {
          x: scale(zone.x, minX, maxX, padding, width - padding),
          y: scale(zone.y, minY, maxY, height - padding, padding),
        });
      }

      for (const connection of simulation.connections) {
        const origin = positionForZone(connection.zone_a);
        const destination = positionForZone(connection.zone_b);
        const line = element("line", {
          x1: origin.x,
          y1: origin.y,
          x2: destination.x,
          y2: destination.y,
          class: "connection",
        });
        svg.append(line);

        if (connection.capacity > 1) {
          const label = element("text", {
            x: (origin.x + destination.x) / 2,
            y: (origin.y + destination.y) / 2 - 8,
            class: "capacity",
          });
          label.textContent = `capacity ${connection.capacity}`;
          svg.append(label);
        }
      }

      for (const zone of simulation.zones) {
        const position = positionForZone(zone.name);
        const group = element("g");
        const circle = element("circle", {
          cx: position.x,
          cy: position.y,
          r: 28,
          class: `zone ${zone.type}`,
          fill: zone.color || "#34506f",
        });
        const name = element("text", {
          x: position.x,
          y: position.y + 47,
          class: "zone-name",
        });
        const type = element("text", {
          x: position.x,
          y: position.y + 63,
          class: "zone-type",
        });
        name.textContent = zone.name;
        type.textContent = zone.role === "hub"
          ? zone.type
          : zone.role;
        group.append(circle, name, type);
        svg.append(group);
      }
    }

    function positionForDrone(drone) {
      if (drone.kind === "zone") {
        return positionForZone(drone.zone);
      }

      const origin = positionForZone(drone.origin);
      const destination = positionForZone(drone.destination);
      return {
        x: (origin.x + destination.x) / 2,
        y: (origin.y + destination.y) / 2,
      };
    }

    function drawTurn(turn) {
      svg.querySelectorAll(".drone").forEach(node => node.remove());
      const drones = simulation.turns[turn];
      const occupied = new Map();

      for (const drone of drones) {
        const base = positionForDrone(drone);
        const key = `${Math.round(base.x)}:${Math.round(base.y)}`;
        const index = occupied.get(key) || 0;
        occupied.set(key, index + 1);
        const ring = Math.ceil(index / 8);
        const slot = (index - 1) % 8;
        const angle = slot * Math.PI / 4 + ring * 0.25;
        const distance = index === 0 ? 0 : ring * 24;
        const x = base.x + Math.cos(angle) * distance;
        const y = base.y + Math.sin(angle) * distance;
        const group = element("g", {
          class: "drone",
          "data-drone-id": drone.id,
        });
        const circle = element("circle", {cx: x, cy: y, r: 17});
        const label = element("text", {x, y});
        label.textContent = `D${drone.id}`;
        group.append(circle, label);
        svg.append(group);
      }

      const active = drones.filter(drone => {
        return drone.kind !== "zone" || drone.zone !== simulation.end;
      }).length;
      const delivered = simulation.nb_drones - active;
      turnLabel.textContent = `Turn ${turn} / ${simulation.last_turn}`;
      deliveryLabel.textContent = `${delivered} delivered`;
      turnInput.value = String(turn);
    }

    function stop() {
      if (timer !== null) {
        window.clearInterval(timer);
        timer = null;
      }
      playButton.textContent = "Play";
    }

    function showTurn(turn) {
      currentTurn = Math.max(0, Math.min(simulation.last_turn, turn));
      drawTurn(currentTurn);
    }

    document.querySelector("#previous").addEventListener("click", () => {
      stop();
      showTurn(currentTurn - 1);
    });

    document.querySelector("#next").addEventListener("click", () => {
      stop();
      showTurn(currentTurn + 1);
    });

    playButton.addEventListener("click", () => {
      if (timer !== null) {
        stop();
        return;
      }

      if (currentTurn === simulation.last_turn) {
        showTurn(0);
      }

      playButton.textContent = "Pause";
      timer = window.setInterval(() => {
        showTurn(currentTurn + 1);
        if (currentTurn === simulation.last_turn) {
          stop();
        }
      }, 800);
    });

    turnInput.addEventListener("input", event => {
      stop();
      showTurn(Number(event.target.value));
    });

    zoomInput.addEventListener("input", event => {
      fitMode = false;
      applyZoom(Number(event.target.value));
    });

    document.querySelector("#zoom-out").addEventListener("click", () => {
      changeZoom(0.8);
    });

    document.querySelector("#zoom-in").addEventListener("click", () => {
      changeZoom(1.25);
    });

    document.querySelector("#fit").addEventListener("click", fitMap);

    window.addEventListener("resize", () => {
      if (fitMode) {
        fitMap();
      }
    });

    turnInput.max = String(simulation.last_turn);
    drawMap();
    showTurn(0);
    fitMap();
  </script>
</body>
</html>
"""


def render_html(
    map: Map,
    schedule: RouteSchedule,
    output_file: str,
) -> None:
    """Write an interactive visualization to a standalone HTML file."""

    turns: list[list[dict[str, object]]] = []

    for turn in range(schedule.last_turn + 1):
        drones: list[dict[str, object]] = []

        for drone_id in range(1, map.nb_drones + 1):
            route = schedule.get_route(drone_id)
            if turn >= len(route):
                continue

            location = route[turn]
            if isinstance(location, Transit):
                drones.append(
                    {
                        "id": drone_id,
                        "kind": "transit",
                        "origin": location.origin,
                        "destination": location.destination,
                    }
                )
            else:
                drones.append(
                    {"id": drone_id, "kind": "zone", "zone": location}
                )

        turns.append(drones)

    data = {
        "nb_drones": map.nb_drones,
        "last_turn": schedule.last_turn,
        "end": map.end,
        "zones": [
            {
                "name": zone.name,
                "x": zone.x,
                "y": zone.y,
                "role": zone.zone_role.value,
                "type": zone.zone_type.value,
                "color": zone.color,
                "capacity": zone.capacity,
            }
            for zone in map.zones.values()
        ],
        "connections": [
            {
                "zone_a": connection.zone_a,
                "zone_b": connection.zone_b,
                "capacity": connection.capacity,
            }
            for connection in map.connections
        ],
        "turns": turns,
    }
    serialized_data = json.dumps(data, separators=(",", ":")).replace(
        "<", "\\u003c"
    )
    html = _HTML_TEMPLATE.replace("__SIMULATION_DATA__", serialized_data)
    path = Path(output_file)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
