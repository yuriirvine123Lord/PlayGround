(() => {
  "use strict";

  const FX = [
    ["neon_grid", "Grade Neon"], ["glitch", "Glitch Digital"], ["chromatic", "Aberração Cromática"],
    ["vhs", "VHS Retrô"], ["scanlines", "Scanlines CRT"], ["particles", "Partículas Neon"],
    ["neon_rain", "Chuva Neon"], ["cyber_grid", "Horizonte Synthwave"], ["hologram", "Holograma"],
    ["bloom", "Bloom Suave"], ["lens_flare", "Lens Flare"], ["film_grain", "Grão de Filme"],
    ["shake", "Camera Shake"], ["zoom_pulse", "Zoom Pulsante"], ["dolly", "Dolly Cinemático"],
    ["orbit", "Órbita"], ["strobe", "Strobe Club"], ["matrix_rain", "Matrix Rain"],
    ["plasma", "Plasma"], ["kaleidoscope", "Caleidoscópio"], ["mirror", "Espelho"],
    ["wave", "Onda"], ["pixelate", "Pixelate 8-bit"], ["noise", "Ruído Digital"],
    ["vignette", "Vinheta Cinema"], ["light_leak", "Light Leak"], ["god_rays", "God Rays"],
    ["datamosh", "Datamosh"], ["synthwave_sun", "Sol Synthwave"], ["laser", "Lasers"],
    ["bokeh", "Bokeh Noturno"], ["aurora", "Aurora"], ["tunnel", "Túnel Neon"],
    ["hyperdrive", "Hiperdrive"], ["fire", "Chamas"], ["ice", "Gelo Cristal"],
    ["storm", "Tempestade"], ["golden_dust", "Poeira Dourada"], ["billboard", "Outdoors Neon"],
    ["slowmo", "Câmera Lenta"],
  ];

  const KEYWORDS = {
    neon_grid: ["neon", "grade", "grid", "cyber"], glitch: ["glitch"],
    chromatic: ["cromat", "rgb"], vhs: ["vhs", "retr"], scanlines: ["scanline", "crt"],
    particles: ["part", "poeira", "faisca", "faísca"], neon_rain: ["chuva"],
    cyber_grid: ["synthwave", "horizonte", "por do sol", "pôr do sol"], hologram: ["hologr"],
    bloom: ["bloom", "brilho"], film_grain: ["grao", "grão", "filme"], shake: ["shake", "tremor"],
    zoom_pulse: ["zoom"], dolly: ["dolly"], matrix_rain: ["matrix"], plasma: ["plasma", "neblina"],
    kaleidoscope: ["caleidosc"], wave: ["onda", "agua", "água"], noise: ["ruido", "ruído"],
    vignette: ["vinheta"], light_leak: ["leak", "ambar", "âmbar"], god_rays: ["god ray", "feixe"],
    datamosh: ["datamosh"], synthwave_sun: ["sol"], laser: ["laser"], aurora: ["aurora", "boreal"],
    tunnel: ["tunel", "túnel"], hyperdrive: ["hyperdrive", "warp"], fire: ["chama", "fogo", "brasa"],
    ice: ["gelo", "cristal"], storm: ["tempestade", "relamp", "relâmp"], golden_dust: ["dourad", "golden"],
    billboard: ["outdoor", "letreiro"], slowmo: ["camera lenta", "câmera lenta", "slow"],
  };

  const $ = (id) => document.getElementById(id);
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

  /* ---------- menu ---------- */
  const menuBtn = $("menuBtn");
  const nav = $("nav");
  if (menuBtn && nav) {
    menuBtn.addEventListener("click", () => {
      const open = nav.classList.toggle("open");
      menuBtn.classList.toggle("open", open);
      menuBtn.setAttribute("aria-expanded", String(open));
    });
    nav.querySelectorAll("a").forEach((a) => a.addEventListener("click", () => {
      nav.classList.remove("open");
      menuBtn.classList.remove("open");
      menuBtn.setAttribute("aria-expanded", "false");
    }));
  }

  /* ---------- effects chips ---------- */
  const selected = new Set();
  const grid = $("fxGrid");
  const count = $("fxCount");
  if (grid) {
    FX.forEach(([id, label]) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = label;
      b.dataset.id = id;
      b.setAttribute("aria-pressed", "false");
      b.addEventListener("click", () => {
        if (selected.has(id)) { selected.delete(id); b.classList.remove("on"); }
        else if (selected.size < 5) { selected.add(id); b.classList.add("on"); }
        b.setAttribute("aria-pressed", String(selected.has(id)));
        if (count) count.textContent = String(selected.size);
      });
      grid.appendChild(b);
    });
  }
  const clearBtn = $("fxClear");
  if (clearBtn) clearBtn.addEventListener("click", () => {
    selected.clear();
    grid.querySelectorAll(".chip").forEach((c) => { c.classList.remove("on"); c.setAttribute("aria-pressed", "false"); });
    if (count) count.textContent = "0";
  });

  /* ---------- hero canvas ---------- */
  const heroCanvas = $("heroCanvas");
  if (heroCanvas) {
    const hctx = heroCanvas.getContext("2d");
    let hw = 0, hh = 0, dpr = 1;
    const stars = [];
    const resize = () => {
      dpr = Math.min(devicePixelRatio || 1, 2);
      hw = heroCanvas.clientWidth; hh = heroCanvas.clientHeight;
      heroCanvas.width = Math.floor(hw * dpr);
      heroCanvas.height = Math.floor(hh * dpr);
      hctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (!stars.length) for (let i = 0; i < 90; i++) stars.push({
        x: Math.random(), y: Math.random(), r: Math.random() * 1.6 + 0.3, s: Math.random() * 0.35 + 0.08,
      });
    };
    resize();
    addEventListener("resize", resize, { passive: true });
    let t = 0;
    const drawHero = () => {
      t += 0.006;
      hctx.clearRect(0, 0, hw, hh);
      const horizon = hh * 0.76;
      const sky = hctx.createLinearGradient(0, 0, 0, horizon);
      sky.addColorStop(0, "#04060b"); sky.addColorStop(0.7, "#071026"); sky.addColorStop(1, "#0c1a38");
      hctx.fillStyle = sky; hctx.fillRect(0, 0, hw, horizon);
      const sunY = horizon - hh * 0.09;
      const sun = hctx.createLinearGradient(0, sunY - hh * 0.1, 0, sunY + hh * 0.1);
      sun.addColorStop(0, "#ff2e88"); sun.addColorStop(1, "#ffb03a");
      hctx.save();
      hctx.globalAlpha = 0.85;
      hctx.beginPath(); hctx.arc(hw * 0.5, sunY, Math.min(hw, hh) * 0.12, 0, Math.PI * 2); hctx.clip();
      hctx.fillStyle = sun; hctx.fillRect(0, sunY - hh * 0.2, hw, hh * 0.4);
      hctx.fillStyle = "#04060b";
      for (let i = 0; i < 6; i++) hctx.fillRect(0, sunY - hh * 0.05 + i * 7, hw, 3 + i);
      hctx.restore();
      hctx.globalAlpha = 1;
      hctx.fillStyle = "#0c1a38"; hctx.fillRect(0, horizon, hw, hh - horizon);
      hctx.strokeStyle = "#00f5d4"; hctx.lineWidth = 1;
      const rows = 16, cols = 22;
      for (let i = 1; i <= rows; i++) {
        const p = i / rows, y = horizon + (hh - horizon) * (p * p);
        hctx.globalAlpha = 0.10 + p * 0.32;
        hctx.beginPath(); hctx.moveTo(0, y); hctx.lineTo(hw, y); hctx.stroke();
      }
      const vpx = hw * 0.5;
      for (let i = -cols; i <= cols; i++) {
        const x = vpx + (i / cols) * hw * 1.7 * (1 + t * 0.2);
        hctx.globalAlpha = 0.18;
        hctx.beginPath(); hctx.moveTo(vpx + (i / cols) * hw * 0.12, horizon); hctx.lineTo(x, hh); hctx.stroke();
      }
      hctx.globalAlpha = 1;
      stars.forEach((s) => {
        s.y -= s.s * 0.0016;
        if (s.y < 0) { s.y = 1; s.x = Math.random(); }
        const y = s.y * horizon;
        hctx.globalAlpha = 0.35 + Math.sin(t * 6 + s.x * 10) * 0.25;
        hctx.fillStyle = s.x > 0.5 ? "#00f5d4" : "#ff2e88";
        hctx.beginPath(); hctx.arc(s.x * hw, y, s.r, 0, Math.PI * 2); hctx.fill();
      });
      hctx.globalAlpha = 1;
      requestAnimationFrame(drawHero);
    };
    if (!reduce) drawHero(); else {
      hctx.fillStyle = "#071026"; hctx.fillRect(0, 0, hw, hh);
    }
  }

  /* ---------- preview canvas ---------- */
  const preview = $("preview");
  let selectedFromPrompt = new Set(["neon_grid", "glitch", "neon_rain", "particles"]);
  const detect = (text) => {
    const t = (text || "").toLowerCase();
    const out = new Set();
    Object.entries(KEYWORDS).forEach(([id, words]) => {
      if (out.size < 5 && words.some((w) => t.includes(w))) out.add(id);
    });
    return out;
  };
  const activeEffects = () => {
    if (selected.size) return new Set(selected);
    return selectedFromPrompt.size ? selectedFromPrompt : new Set(["neon_grid", "particles"]);
  };

  if (preview) {
    const ctx = preview.getContext("2d");
    let pt = 0;
    const rain = Array.from({ length: 120 }, () => ({ x: Math.random(), y: Math.random(), l: Math.random() * 0.22 + 0.08, s: Math.random() * 0.6 + 0.4 }));
    const dust = Array.from({ length: 70 }, () => ({ x: Math.random(), y: Math.random(), r: Math.random() * 2 + 0.4, s: Math.random() * 0.004 + 0.001 }));
    let glitchFrames = 0;

    const sizeCanvas = () => {
      const vertical = $("aspect") && $("aspect").value === "9:16";
      preview.width = vertical ? 720 : 1280;
      preview.height = 1280;
      if (!vertical) preview.height = 720;
      const frame = preview.closest(".vp-frame");
      if (frame) frame.dataset.aspect = vertical ? "9:16" : "16:9";
    };
    sizeCanvas();
    if ($("aspect")) $("aspect").addEventListener("change", sizeCanvas);

    const drawPreview = () => {
      const fx = activeEffects();
      const W = preview.width, H = preview.height;
      pt += 0.012;
      const horizon = H * 0.62;
      const sky = ctx.createLinearGradient(0, 0, 0, horizon);
      sky.addColorStop(0, "#05070e"); sky.addColorStop(1, fx.has("storm") ? "#1a2140" : "#0d1b3a");
      ctx.fillStyle = sky; ctx.fillRect(0, 0, W, horizon);

      if (fx.has("aurora")) {
        for (let i = 0; i < 3; i++) {
          ctx.globalAlpha = 0.14;
          ctx.fillStyle = i % 2 ? "#00f5d4" : "#7a4bff";
          ctx.beginPath();
          ctx.moveTo(0, horizon * (0.2 + i * 0.12));
          for (let x = 0; x <= W; x += 40) ctx.lineTo(x, horizon * (0.2 + i * 0.12) + Math.sin(x * 0.004 + pt * 2 + i) * 26);
          ctx.lineTo(W, 0); ctx.lineTo(0, 0); ctx.closePath(); ctx.fill();
        }
        ctx.globalAlpha = 1;
      }

      if (fx.has("synthwave_sun") || fx.has("cyber_grid") || !fx.size) {
        const sunY = horizon - H * 0.16;
        const g = ctx.createLinearGradient(0, sunY - H * 0.14, 0, sunY + H * 0.14);
        g.addColorStop(0, "#ff2e88"); g.addColorStop(1, "#ffb03a");
        ctx.save();
        ctx.beginPath(); ctx.arc(W * 0.5, sunY, Math.min(W, H) * 0.15, 0, Math.PI * 2); ctx.clip();
        ctx.fillStyle = g; ctx.fillRect(0, sunY - H * 0.2, W, H * 0.4);
        ctx.fillStyle = "#05070e";
        for (let i = 0; i < 7; i++) ctx.fillRect(0, sunY - H * 0.04 + i * 8, W, 4 + i);
        ctx.restore();
      }

      ctx.fillStyle = fx.has("ice") ? "#0a1828" : "#080f1f";
      ctx.fillRect(0, horizon, W, H - horizon);

      const gridColor = fx.has("fire") ? "#ff7b39" : fx.has("ice") ? "#8fd8ff" : "#00f5d4";
      ctx.strokeStyle = gridColor; ctx.lineWidth = 1.2;
      const rows = 18, cols = 26, vpx = W * 0.5;
      const scroll = (pt * 0.35) % 1;
      for (let i = 0; i <= rows; i++) {
        const p = (i + scroll) / rows, y = horizon + (H - horizon) * (p * p);
        if (y > H) continue;
        ctx.globalAlpha = 0.08 + p * 0.3;
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
      }
      for (let i = -cols; i <= cols; i++) {
        ctx.globalAlpha = 0.16;
        ctx.beginPath(); ctx.moveTo(vpx + (i / cols) * W * 0.14, horizon); ctx.lineTo(vpx + (i / cols) * W * 1.8, H); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      if (fx.has("matrix_rain") || fx.has("neon_rain")) {
        ctx.strokeStyle = fx.has("matrix_rain") ? "#4dff88" : "#00b7ff";
        ctx.lineWidth = 1.6;
        rain.forEach((d) => {
          d.y += d.s * 0.012; if (d.y > 1) { d.y = -0.1; d.x = Math.random(); }
          ctx.globalAlpha = 0.5;
          const x = d.x * W, y = d.y * H;
          ctx.beginPath(); ctx.moveTo(x, y); ctx.lineTo(x + W * 0.010, y + d.l * H); ctx.stroke();
        });
        ctx.globalAlpha = 1;
      }

      if (fx.has("particles") || fx.has("golden_dust") || fx.has("bokeh")) {
        dust.forEach((d, i) => {
          d.y -= d.s; if (d.y < 0) { d.y = 1; d.x = Math.random(); }
          ctx.globalAlpha = 0.5 + Math.sin(pt * 4 + i) * 0.3;
          ctx.fillStyle = fx.has("golden_dust") ? "#ffd166" : fx.has("bokeh") ? "#ff9ad5" : "#00f5d4";
          ctx.beginPath(); ctx.arc(d.x * W, d.y * H, d.r, 0, Math.PI * 2); ctx.fill();
        });
        ctx.globalAlpha = 1;
      }

      if (fx.has("billboard")) {
        for (let i = 0; i < 4; i++) {
          const bx = W * (0.12 + i * 0.24), by = horizon - H * (0.16 + (i % 2) * 0.06);
          ctx.fillStyle = i % 2 ? "#ff2e8844" : "#00f5d444";
          ctx.fillRect(bx, by, W * 0.07, H * 0.18);
          ctx.strokeStyle = i % 2 ? "#ff2e88" : "#00f5d4"; ctx.lineWidth = 1.4;
          ctx.strokeRect(bx, by, W * 0.07, H * 0.18);
        }
      }

      if (fx.has("storm")) {
        if (Math.random() < 0.03) ctx.fillStyle = "#cfe3ff22", ctx.fillRect(0, 0, W, H);
        ctx.strokeStyle = "#dff0ff"; ctx.lineWidth = 2;
        ctx.beginPath();
        let lx = Math.random() * W; ctx.moveTo(lx, 0);
        for (let y = 0; y < horizon; y += 24) { lx += (Math.random() - 0.5) * 40; ctx.lineTo(lx, y); }
        ctx.globalAlpha = 0.6; ctx.stroke(); ctx.globalAlpha = 1;
      }

      if (fx.has("laser")) {
        [[0.28, "#ff2e88"], [0.72, "#00f5d4"]].forEach(([x, c], i) => {
          ctx.strokeStyle = c; ctx.lineWidth = 2.4; ctx.globalAlpha = 0.55;
          ctx.beginPath(); ctx.moveTo(W * x, 0); ctx.lineTo(W * (0.5 + Math.sin(pt + i) * 0.2), H); ctx.stroke();
        });
        ctx.globalAlpha = 1;
      }

      if (fx.has("vignette") || true) {
        const v = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.25, W / 2, H / 2, Math.max(W, H) * 0.7);
        v.addColorStop(0, "#00000000"); v.addColorStop(1, "#000000aa");
        ctx.fillStyle = v; ctx.fillRect(0, 0, W, H);
      }

      if (fx.has("scanlines")) {
        ctx.fillStyle = "#00000038";
        for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 1.4);
      }
      if (fx.has("noise") || fx.has("film_grain")) {
        ctx.globalAlpha = 0.06;
        for (let i = 0; i < 260; i++) {
          ctx.fillStyle = Math.random() > 0.5 ? "#fff" : "#000";
          ctx.fillRect(Math.random() * W, Math.random() * H, 2, 2);
        }
        ctx.globalAlpha = 1;
      }
      if (fx.has("glitch") || fx.has("datamosh")) {
        glitchFrames = (glitchFrames + 1) % 24;
        if (glitchFrames < 3 || fx.has("datamosh")) {
          const y = Math.random() * H, h = 6 + Math.random() * 30;
          const img = ctx.getImageData(0, y, W, Math.min(h, H - y));
          ctx.putImageData(img, (Math.random() - 0.5) * 40, y);
        }
      }
      if (fx.has("chromatic")) {
        ctx.globalCompositeOperation = "screen";
        ctx.globalAlpha = 0.16;
        ctx.drawImage(preview, -4, 0); ctx.drawImage(preview, 4, 0);
        ctx.globalCompositeOperation = "source-over"; ctx.globalAlpha = 1;
      }
      if (fx.has("vhs")) {
        ctx.fillStyle = "#ffffff10";
        ctx.fillRect(0, (Math.sin(pt * 3) * 0.5 + 0.5) * H, W, 3);
      }

      requestAnimationFrame(drawPreview);
    };
    if (!reduce) requestAnimationFrame(drawPreview);
    else {
      ctx.fillStyle = "#071026"; ctx.fillRect(0, 0, preview.width, preview.height);
      ctx.strokeStyle = "#00f5d4"; ctx.globalAlpha = 0.5;
      for (let y = preview.height * 0.62; y < preview.height; y += 24) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(preview.width, y); ctx.stroke(); }
    }
  }

  /* ---------- simulated generation ---------- */
  const form = $("studioForm");
  const stage = $("stage");
  const bar = $("bar");
  const frames = $("frames");
  const caption = $("vpCaption");
  let running = false;
  if (form) {
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      if (running) return;
      const promptEl = $("prompt");
      const prompt = promptEl ? promptEl.value.trim() : "";
      if (!prompt) { if (stage) stage.textContent = "descreva a cena primeiro"; return; }
      selectedFromPrompt = detect(prompt);
      running = true;
      const dur = parseInt(($("dur") && $("dur").value) || "8", 10);
      const total = dur * 24;
      let done = 0;
      if (stage) stage.textContent = "roteirizando…";
      if (caption) caption.textContent = "A IA está dirigindo: " + [...selectedFromPrompt].join(" · ");
      const tick = () => {
        done = Math.min(total, done + Math.ceil(total / 42));
        const pct = Math.round((done / total) * 100);
        if (bar) bar.style.width = pct + "%";
        if (frames) frames.textContent = "quadros: " + done + "/" + total;
        if (done < total) setTimeout(tick, 55);
        else {
          if (stage) stage.textContent = "concluído — vídeo pronto";
          running = false;
        }
      };
      setTimeout(tick, 250);
    });
  }
})();
