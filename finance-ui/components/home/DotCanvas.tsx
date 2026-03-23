"use client";

import { useEffect, useRef } from "react";

type Dot = {
  x: number; y: number; tx: number; ty: number; shade: number;
  vx: number; vy: number; size: number; alpha: number; ph: number;
  col: [number, number, number];
};

function pickColor(i: number, n: number): [number, number, number] {
  const t = i / n;
  if (t < 0.33) return [167, 139, 250];
  if (t < 0.66) return [148, 120, 250];
  return [196, 181, 253];
}

export function DotCanvas() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const countRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    // ctx is non-null from here — cast for nested function scope
    const safeCtx = ctx;

    let W = 0, H = 0;
    let animId: number;
    let done = false;
    let dots: Dot[] = [];
    type Phase = "scatter"|"formHi"|"holdHi"|"toRupee"|"holdRupee"|"toText"|"holdText";
    let phase: Phase = "scatter";
    let phaseT = 0, frame = 0;
    const DUR = { scatter:100, formHi:90, holdHi:160, toRupee:110, holdRupee:260, toText:120, holdText:240 };

    function sampleCanvas(drawFn: (c: CanvasRenderingContext2D) => void, step: number) {
      if (W <= 0 || H <= 0) return [];
      const off = document.createElement("canvas");
      off.width = W; off.height = H;
      const c = off.getContext("2d")!;
      drawFn(c);
      const data = c.getImageData(0, 0, W, H).data;
      const pts: { x: number; y: number }[] = [];
      for (let y = 0; y < H; y += step)
        for (let x = 0; x < W; x += step)
          if (data[(y * W + x) * 4 + 3] > 128) pts.push({ x, y });
      return pts;
    }

    function buildRupee3D(step: number) {
      const front = sampleCanvas(c => {
        c.fillStyle = "#fff";
        c.font = `bold ${Math.floor(H * 0.52)}px Arial,sans-serif`;
        c.textAlign = "center"; c.textBaseline = "middle";
        c.fillText("₹", W / 2, H / 2);
      }, step);
      const layers = 9, ox = 1.8, oy = 1.4;
      const all: { x: number; y: number; shade: number }[] = [];
      for (let z = layers - 1; z >= 0; z--) {
        const shade = 1 - (z / layers) * 0.6;
        front.forEach(p => all.push({ x: p.x + z * ox, y: p.y + z * oy, shade }));
      }
      return all;
    }

    function buildText(step: number) {
      return sampleCanvas(c => {
        const l1 = "let's start", l2 = "researching", maxW = W * 0.82;
        let fs = Math.floor(H * 0.22);
        while (fs > 12) {
          c.font = `bold ${fs}px Arial,sans-serif`;
          if (c.measureText(l1).width <= maxW && c.measureText(l2).width <= maxW) break;
          fs--;
        }
        c.fillStyle = "#fff"; c.textAlign = "center"; c.textBaseline = "middle";
        const gap = fs * 1.6;
        c.fillText(l1, W / 2, H / 2 - gap / 2);
        c.fillText(l2, W / 2, H / 2 + gap / 2);
      }, 5);
    }

    let hiT: { x: number; y: number }[] = [];
    let rupeeT: { x: number; y: number; shade: number }[] = [];
    let textT: { x: number; y: number }[] = [];

    function resize() {
      if (!canvas) return;
      const parent = canvas.parentElement;
      if (!parent) return;
      W = canvas.width = parent.clientWidth;
      H = canvas.height = parent.clientHeight;
    }

    function init() {
      hiT = sampleCanvas(c => {
        c.fillStyle = "#fff";
        c.font = `bold ${Math.floor(H * 0.52)}px Arial,sans-serif`;
        c.textAlign = "center"; c.textBaseline = "middle";
        c.fillText("Hi", W / 2, H / 2);
      }, 8);
      rupeeT = buildRupee3D(7);
      textT = buildText(5);
      const N = Math.max(hiT.length, rupeeT.length, textT.length, 220);
      dots = Array.from({ length: N }, (_, i) => ({
        x: Math.random() * W, y: Math.random() * H,
        tx: hiT[i % hiT.length].x, ty: hiT[i % hiT.length].y,
        shade: 1, vx: (Math.random() - 0.5) * 1.6, vy: (Math.random() - 0.5) * 1.6,
        size: Math.random() * 1.4 + 1, alpha: Math.random() * 0.35 + 0.3,
        ph: Math.random(), col: pickColor(i, N),
      }));
    }

    function setTargets(tgts: { x: number; y: number; shade?: number }[]) {
      dots.forEach((d, i) => {
        const t = tgts[i % tgts.length];
        d.tx = t.x; d.ty = t.y; d.shade = t.shade !== undefined ? t.shade : 1;
      });
    }

    function drawDots() {
      const formed = ["holdHi","toRupee","holdRupee","toText","holdText"].includes(phase);
      dots.forEach(d => {
        const pulse = formed ? 0.45 + 0.55 * Math.sin(frame * 0.04 + d.ph * Math.PI * 2) : d.alpha;
        const sz = formed ? d.size * (1 + 0.18 * Math.sin(frame * 0.05 + d.ph * 5)) : d.size;
        safeCtx.beginPath();
        safeCtx.arc(d.x, d.y, Math.max(0.5, sz), 0, Math.PI * 2);
        safeCtx.fillStyle = `rgba(${Math.round(d.col[0]*d.shade)},${Math.round(d.col[1]*d.shade)},${Math.round(d.col[2]*d.shade)},${Math.min(1, pulse).toFixed(2)})`;
        safeCtx.fill();
      });
    }

    function countUp(target: number, duration: number) {
      const el = countRef.current;
      if (!el) return;
      const start = Date.now();
      const tick = () => {
        const p = Math.min((Date.now() - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        el.textContent = Math.round(ease * target).toLocaleString() + "+";
        if (p < 1) requestAnimationFrame(tick);
      };
      tick();
    }

    function fadeToOverlay() {
      if (!canvas) return;
      let op = 1;
      const iv = setInterval(() => {
        op = Math.max(0, op - 0.018);
        canvas.style.opacity = op.toString();
        if (op <= 0) {
          clearInterval(iv);
          canvas.style.display = "none";
          const ov = overlayRef.current;
          if (ov) {
            ov.style.display = "flex";
            requestAnimationFrame(() => {
              ov.style.opacity = "1";
              setTimeout(() => countUp(5000, 1600), 300);
            });
          }
        }
      }, 16);
    }

    resize();

    // Retry init until dimensions are available (can be 0 on mobile before layout)
    function tryInit() {
      if (W <= 0 || H <= 0) { requestAnimationFrame(tryInit); return; }
      init();
      animId = requestAnimationFrame(loop);
    }

    const ro = new ResizeObserver(() => resize());
    if (canvas.parentElement) ro.observe(canvas.parentElement);

    function loop() {
      if (done) return;
      frame++; phaseT++;
      safeCtx.clearRect(0, 0, W, H);

      if (phase === "scatter") {
        dots.forEach(d => {
          d.x += d.vx; d.y += d.vy;
          d.vx += (Math.random()-0.5)*0.07; d.vy += (Math.random()-0.5)*0.07;
          d.vx *= 0.97; d.vy *= 0.97;
          if (d.x < 0 || d.x > W) d.vx *= -1;
          if (d.y < 0 || d.y > H) d.vy *= -1;
        });
        if (phaseT > DUR.scatter) { setTargets(hiT); phase = "formHi"; phaseT = 0; }
      } else if (phase === "formHi") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.1; d.y += (d.ty-d.y)*0.1; });
        if (phaseT > DUR.formHi) { phase = "holdHi"; phaseT = 0; }
      } else if (phase === "holdHi") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.2; d.y += (d.ty-d.y)*0.2; });
        if (phaseT > DUR.holdHi) { setTargets(rupeeT); phase = "toRupee"; phaseT = 0; }
      } else if (phase === "toRupee") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.09; d.y += (d.ty-d.y)*0.09; });
        if (phaseT > DUR.toRupee) { phase = "holdRupee"; phaseT = 0; }
      } else if (phase === "holdRupee") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.18; d.y += (d.ty-d.y)*0.18; });
        if (phaseT > DUR.holdRupee) { setTargets(textT); phase = "toText"; phaseT = 0; }
      } else if (phase === "toText") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.09; d.y += (d.ty-d.y)*0.09; d.shade += (1-d.shade)*0.09; });
        if (phaseT > DUR.toText) { phase = "holdText"; phaseT = 0; }
      } else if (phase === "holdText") {
        dots.forEach(d => { d.x += (d.tx-d.x)*0.15; d.y += (d.ty-d.y)*0.15; d.shade = 1; });
        if (phaseT > DUR.holdText) { done = true; fadeToOverlay(); return; }
      }

      drawDots();
      animId = requestAnimationFrame(loop);
    }

    tryInit();
    return () => { cancelAnimationFrame(animId); ro.disconnect(); };
  }, []);

  return (
    <div style={{ position: "relative", overflow: "hidden", background: "var(--home-bg)", width: "100%", height: "100%" }}>
      <canvas ref={canvasRef} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
      <div ref={overlayRef} style={{
        position: "absolute", inset: 0, display: "none", opacity: 0,
        alignItems: "center", justifyContent: "center", flexDirection: "column",
        zIndex: 5, pointerEvents: "none", transition: "opacity 1.4s ease",
      }}>
        <div style={{ fontSize: 11, color: "var(--home-purple)", fontFamily: "var(--font-mono)", letterSpacing: 2, marginBottom: 12, textAlign: "center" }}>
          BSE companies accessible
        </div>
        <div ref={countRef} style={{ fontSize: 56, fontWeight: 800, letterSpacing: -3, lineHeight: 1, textAlign: "center", color: "var(--home-text)" }}>0</div>
        <div style={{ fontSize: 13, color: "var(--home-muted)", marginTop: 10, fontWeight: 300, textAlign: "center" }}>
          Load any ticker. Always current.
        </div>
      </div>
    </div>
  );
}
