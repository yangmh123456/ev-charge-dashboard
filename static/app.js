const svgNS = "http://www.w3.org/2000/svg";
const palette = {
  green: "#34c759",
  yellow: "#ff9f0a",
  cyan: "#0071e3",
  red: "#ff3b30",
  moss: "#8e8e93",
  pale: "#c7d2fe",
};

function byId(id) {
  return document.getElementById(id);
}

function section(payload, id) {
  return payload.sections.find((item) => item.id === id);
}

function clear(node) {
  node.replaceChildren();
}

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function svgEl(tag, attrs = {}, text) {
  const node = document.createElementNS(svgNS, tag);
  Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, String(value)));
  if (text !== undefined) node.textContent = String(text);
  return node;
}

function addTitle(parent, text) {
  const title = svgEl("title");
  title.textContent = text;
  parent.appendChild(title);
}

function makeMetric(label, value) {
  const card = el("div", "metric");
  card.append(el("span", "", label), el("strong", "", value));
  return card;
}

function renderSummary(summary) {
  const container = byId("summary");
  clear(container);
  [
    ["\u5145\u7535\u4f1a\u8bdd", summary.session_count],
    ["\u7535\u6c60\u91c7\u6837\u70b9", summary.battery_points],
    ["\u7d2f\u8ba1\u7535\u91cf", `${summary.total_kwh} kWh`],
    ["\u5e73\u5747\u65f6\u957f", `${summary.avg_charge_hours} h`],
    ["\u5e73\u5747\u901f\u7387", `${summary.avg_speed} kWh/h`],
    ["\u5e73\u53f0\u6570\u91cf", summary.platforms],
  ].forEach(([label, value]) => container.appendChild(makeMetric(label, value)));
}

function renderNav() {
  const nav = byId("sectionNav");
  clear(nav);
  [
    ["top", "概览"],
    ["time_frequency", "频率"],
    ["hourly_soc", "SOC"],
    ["time_distribution", "分布"],
    ["avg_speed", "速率"],
    ["requirements", "验收"],
  ].forEach(([id, title]) => {
    const link = el("a");
    link.href = `#${id}`;
    link.textContent = title;
    nav.appendChild(link);
  });
}

function scale(value, max, height) {
  return max === 0 ? 0 : (value / max) * height;
}

function renderBars(id, labels, series) {
  const width = 900;
  const height = 260;
  const pad = 34;
  const plotHeight = height - pad * 2;
  const plotWidth = width - pad * 2;
  const max = Math.max(...series.flatMap((item) => item.values), 1);
  const groupWidth = plotWidth / labels.length;
  const barWidth = Math.max(5, groupWidth / (series.length + 1.4));
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });

  series.forEach((item, index) => {
    svg.append(svgEl("circle", { cx: pad + index * 120, cy: 14, r: 5, fill: item.color }));
    svg.append(svgEl("text", { x: pad + 10 + index * 120, y: 18 }, item.name));
  });
  svg.append(svgEl("line", { x1: pad, y1: height - pad, x2: width - pad, y2: height - pad, stroke: "rgba(29,29,31,.14)" }));

  labels.forEach((label, index) => {
    series.forEach((item, seriesIndex) => {
      const h = scale(item.values[index], max, plotHeight);
      const rect = svgEl("rect", {
        x: pad + index * groupWidth + seriesIndex * barWidth + 4,
        y: height - pad - h,
        width: barWidth - 2,
        height: h,
        fill: item.color,
      });
      addTitle(rect, `${item.name}: ${item.values[index]}`);
      svg.append(rect);
    });
    if (index % 2 === 0) svg.append(svgEl("text", { x: pad + index * groupWidth, y: height - 9 }, label));
  });

  const target = byId(id);
  clear(target);
  target.appendChild(svg);
}

function renderLine(id, labels, values, color, name) {
  const width = 900;
  const height = 260;
  const pad = 34;
  const plotHeight = height - pad * 2;
  const plotWidth = width - pad * 2;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const spread = max - min || 1;
  const points = values.map((value, index) => {
    const x = pad + (index / Math.max(values.length - 1, 1)) * plotWidth;
    const y = height - pad - ((value - min) / spread) * plotHeight;
    return [x, y, value];
  });
  const svg = svgEl("svg", { viewBox: `0 0 ${width} ${height}`, role: "img" });
  svg.append(svgEl("text", { x: pad, y: 18 }, name));
  svg.append(svgEl("line", { x1: pad, y1: height - pad, x2: width - pad, y2: height - pad, stroke: "rgba(29,29,31,.14)" }));
  svg.append(svgEl("polyline", { fill: "none", stroke: color, "stroke-width": 3, points: points.map(([x, y]) => `${x},${y}`).join(" ") }));
  points.forEach(([x, y, value], index) => {
    const dot = svgEl("circle", { cx: x, cy: y, r: 4, fill: color });
    addTitle(dot, `${name}: ${value}`);
    svg.append(dot);
    if (index % 2 === 0) svg.append(svgEl("text", { x: x - 10, y: height - 9 }, labels[index]));
  });
  const target = byId(id);
  clear(target);
  target.appendChild(svg);
}

function renderDonut(id, items) {
  const total = items.reduce((sum, item) => sum + item.sessions, 0);
  const colors = [palette.green, palette.yellow, palette.cyan, palette.red, palette.moss, palette.pale];
  const svg = svgEl("svg", { viewBox: "0 0 520 260", role: "img" });
  const group = svgEl("g", { transform: "rotate(-90 140 130)" });
  let offset = 25;

  items.forEach((item, index) => {
    const length = total ? (item.sessions / total) * 100 : 0;
    const circle = svgEl("circle", {
      cx: 140,
      cy: 130,
      r: 72,
      pathLength: 100,
      fill: "none",
      stroke: colors[index],
      "stroke-width": 28,
      "stroke-dasharray": `${length} ${100 - length}`,
      "stroke-dashoffset": offset,
    });
    addTitle(circle, `${item.bucket}: ${item.sessions}`);
    group.appendChild(circle);
    offset -= length;
  });
  svg.append(group, svgEl("text", { x: 110, y: 124 }, "\u603b\u8ba1"), svgEl("text", { x: 103, y: 150 }, total));
  items.forEach((item, index) => {
    svg.append(svgEl("rect", { x: 265, y: 50 + index * 28, width: 12, height: 12, fill: colors[index] }));
    svg.append(svgEl("text", { x: 286, y: 61 + index * 28 }, `${item.bucket} ${item.sessions}`));
  });
  const target = byId(id);
  clear(target);
  target.appendChild(svg);
}

function renderCharts(payload) {
  const frequency = section(payload, "time_frequency").data;
  renderBars("frequencyChart", frequency.map((item) => `${item.hour}:00`), [
    { name: "\u4f1a\u8bdd\u6b21\u6570", values: frequency.map((item) => item.sessions), color: palette.green },
    { name: "\u5145\u7535\u91cf(kWh)", values: frequency.map((item) => item.kwh), color: palette.yellow },
  ]);

  const soc = section(payload, "hourly_soc").data;
  renderLine("socChart", soc.map((item) => `${item.hour}:00`), soc.map((item) => item.soc), palette.cyan, "SOC(%)");
  renderDonut("distributionChart", section(payload, "time_distribution").data);

  const speed = section(payload, "avg_speed").data;
  renderLine("speedChart", speed.map((item) => `${item.hour}:00`), speed.map((item) => item.kw_per_hour), palette.yellow, "\u5e73\u5747\u901f\u7387(kWh/h)");
}

function renderReports(payload) {
  const list = byId("performanceList");
  clear(list);
  section(payload, "performance_report").data.forEach((item) => {
    const row = el("div", `report-item ${item.level}`);
    row.append(el("span", "", item.name), el("strong", "", item.value));
    list.appendChild(row);
  });

  const cards = byId("predictionCards");
  clear(cards);
  payload.sections.filter((item) => item.type === "prediction").forEach((item) => {
    const card = el("div", "prediction-card");
    card.append(el("span", "", item.data.title), el("strong", "", item.data.value), el("span", "", item.data.hint));
    cards.appendChild(card);
  });
}

function renderRequirements(payload) {
  const list = byId("requirementsList");
  clear(list);
  payload.items.forEach((item) => {
    const row = el("div", `coverage-item ${item.status}`);
    const meta = el("div");
    meta.append(el("strong", "", item.name), el("span", "", item.evidence));
    row.append(el("i", "", item.status), meta);
    list.appendChild(row);
  });
}

function renderMapReduceJobs(payload) {
  const list = byId("mapreduceJobs");
  clear(list);
  payload.jobs.forEach((job) => {
    const row = el("div", "job-item");
    row.append(el("strong", "", job.title), el("span", "", `${job.map_key} -> ${job.reduce_value}`), el("small", "", `输出行数：${job.rows.length}`));
    list.appendChild(row);
  });
}

async function boot() {
  const [dashboardResponse, requirementsResponse, jobsResponse] = await Promise.all([
    fetch("/api/dashboard"),
    fetch("/api/requirements"),
    fetch("/api/mapreduce-jobs"),
  ]);
  const payload = await dashboardResponse.json();
  renderNav();
  renderSummary(payload.summary);
  renderCharts(payload);
  renderReports(payload);
  renderRequirements(await requirementsResponse.json());
  renderMapReduceJobs(await jobsResponse.json());
  byId("progressText").textContent = "10/10 \u529f\u80fd\u5df2\u63a5\u5165";
  byId("progressBar").style.width = "100%";
}

boot().catch((error) => {
  byId("progressText").textContent = "\u52a0\u8f7d\u5931\u8d25";
  console.error(error);
});
