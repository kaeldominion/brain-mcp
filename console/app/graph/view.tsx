"use client";

import { useEffect, useRef, useState } from "react";

type Node = { id: string; title: string; folder: string; status?: string; links: number };
type Edge = { source: string; target: string };

const GRADIENT = ["#2DD4BF", "#22D3EE", "#A78BFA", "#C084FC", "#F472B6", "#FBBF24", "#34D399", "#60A5FA"];

export default function GraphView({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<Node | null>(null);
  const state = useRef<any>({ pts: new Map(), tx: 0, ty: 0, scale: 1, drag: null });

  useEffect(() => {
    const canvas = canvasRef.current!;
    const ctx = canvas.getContext("2d")!;
    const dpr = window.devicePixelRatio || 1;
    const W = canvas.clientWidth, H = canvas.clientHeight;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.scale(dpr, dpr);

    const folders = [...new Set(nodes.map((n) => n.folder))].sort();
    const color = (f: string) => GRADIENT[folders.indexOf(f) % GRADIENT.length];

    // deterministic initial ring layout, then force simulation
    const pts = state.current.pts as Map<string, any>;
    nodes.forEach((n, i) => {
      if (!pts.has(n.id)) {
        const a = (i / nodes.length) * Math.PI * 2;
        pts.set(n.id, { x: W / 2 + Math.cos(a) * W * 0.3, y: H / 2 + Math.sin(a) * H * 0.3, vx: 0, vy: 0, n });
      }
    });
    const ids = nodes.map((n) => n.id);
    const es = edges
      .map((e) => ({ a: pts.get(e.source), b: pts.get(e.target) }))
      .filter((e) => e.a && e.b);

    let raf = 0;
    let alpha = 1;
    function tick() {
      // forces
      if (alpha > 0.005) {
        for (let i = 0; i < ids.length; i++) {
          const p = pts.get(ids[i]);
          for (let j = i + 1; j < ids.length; j++) {
            const q = pts.get(ids[j]);
            let dx = p.x - q.x, dy = p.y - q.y;
            let d2 = dx * dx + dy * dy || 1;
            if (d2 < 40000) {
              const f = (900 * alpha) / d2;
              p.vx += dx * f; p.vy += dy * f;
              q.vx -= dx * f; q.vy -= dy * f;
            }
          }
          // gravity to center
          p.vx += (W / 2 - p.x) * 0.0015 * alpha;
          p.vy += (H / 2 - p.y) * 0.0015 * alpha;
        }
        for (const e of es) {
          const dx = e.b.x - e.a.x, dy = e.b.y - e.a.y;
          const d = Math.sqrt(dx * dx + dy * dy) || 1;
          const f = ((d - 90) / d) * 0.02 * alpha;
          e.a.vx += dx * f; e.a.vy += dy * f;
          e.b.vx -= dx * f; e.b.vy -= dy * f;
        }
        for (const id of ids) {
          const p = pts.get(id);
          if (state.current.drag?.id === id) { p.vx = 0; p.vy = 0; continue; }
          p.x += p.vx *= 0.85;
          p.y += p.vy *= 0.85;
        }
        alpha *= 0.995;
      }

      // draw
      const { tx, ty, scale } = state.current;
      ctx.clearRect(0, 0, W, H);
      ctx.save();
      ctx.translate(tx, ty);
      ctx.scale(scale, scale);
      ctx.lineWidth = 1 / scale;
      for (const e of es) {
        ctx.strokeStyle = "rgba(163,163,163,0.25)";
        ctx.beginPath();
        ctx.moveTo(e.a.x, e.a.y);
        ctx.lineTo(e.b.x, e.b.y);
        ctx.stroke();
      }
      for (const id of ids) {
        const p = pts.get(id);
        const r = 4 + Math.min(p.n.links * 1.5, 12);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = color(p.n.folder);
        ctx.globalAlpha = p.n.status === "unverified" ? 0.55 : 1;
        ctx.fill();
        ctx.globalAlpha = 1;
        if (p.n.links >= 3 || scale > 1.4) {
          ctx.fillStyle = "#a3a3a3";
          ctx.font = `${11 / scale}px sans-serif`;
          ctx.fillText(p.n.title, p.x + r + 4 / scale, p.y + 4 / scale);
        }
      }
      ctx.restore();
      raf = requestAnimationFrame(tick);
    }
    raf = requestAnimationFrame(tick);

    function toWorld(ev: MouseEvent) {
      const rect = canvas.getBoundingClientRect();
      const { tx, ty, scale } = state.current;
      return { x: (ev.clientX - rect.left - tx) / scale, y: (ev.clientY - rect.top - ty) / scale };
    }
    function nodeAt(w: { x: number; y: number }) {
      for (const id of ids) {
        const p = pts.get(id);
        const r = 6 + Math.min(p.n.links * 1.5, 12);
        if ((p.x - w.x) ** 2 + (p.y - w.y) ** 2 < r * r) return p;
      }
      return null;
    }

    const onMove = (ev: MouseEvent) => {
      const w = toWorld(ev);
      if (state.current.drag) {
        if (state.current.drag.id) {
          const p = pts.get(state.current.drag.id);
          p.x = w.x; p.y = w.y;
          alpha = Math.max(alpha, 0.3);
        } else {
          state.current.tx += ev.movementX;
          state.current.ty += ev.movementY;
        }
        return;
      }
      const hit = nodeAt(w);
      canvas.style.cursor = hit ? "pointer" : "grab";
      setHover(hit ? hit.n : null);
    };
    const onDown = (ev: MouseEvent) => {
      const hit = nodeAt(toWorld(ev));
      state.current.drag = hit ? { id: hit.n.id, moved: false } : { id: null };
    };
    const onUp = (ev: MouseEvent) => {
      const drag = state.current.drag;
      state.current.drag = null;
      const hit = nodeAt(toWorld(ev));
      if (drag?.id && hit && hit.n.id === drag.id && Math.abs(ev.movementX) < 2) {
        window.location.href = `/vault?path=${encodeURIComponent(hit.n.id)}`;
      }
    };
    const onWheel = (ev: WheelEvent) => {
      ev.preventDefault();
      const factor = ev.deltaY < 0 ? 1.1 : 0.9;
      const rect = canvas.getBoundingClientRect();
      const mx = ev.clientX - rect.left, my = ev.clientY - rect.top;
      const s = state.current;
      s.tx = mx - (mx - s.tx) * factor;
      s.ty = my - (my - s.ty) * factor;
      s.scale *= factor;
    };
    canvas.addEventListener("mousemove", onMove);
    canvas.addEventListener("mousedown", onDown);
    canvas.addEventListener("mouseup", onUp);
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener("mousemove", onMove);
      canvas.removeEventListener("mousedown", onDown);
      canvas.removeEventListener("mouseup", onUp);
      canvas.removeEventListener("wheel", onWheel);
    };
  }, [nodes, edges]);

  const folders = [...new Set(nodes.map((n) => n.folder))].sort();
  return (
    <div>
      <div className="row" style={{ marginBottom: 10 }}>
        {folders.map((f, i) => (
          <span key={f} className="badge" style={{ borderColor: GRADIENT[i % GRADIENT.length], color: GRADIENT[i % GRADIENT.length] }}>
            {f}
          </span>
        ))}
      </div>
      <div style={{ position: "relative" }}>
        <canvas
          ref={canvasRef}
          style={{ width: "100%", height: "68vh", background: "var(--surface)", borderRadius: 12, border: "1px solid var(--line)" }}
        />
        {hover && (
          <div className="card" style={{ position: "absolute", left: 12, bottom: 12, pointerEvents: "none" }}>
            <b>{hover.title}</b>
            <div className="dim mono" style={{ fontSize: 11.5 }}>{hover.id}</div>
            <div className="dim" style={{ fontSize: 12 }}>
              {hover.links} link{hover.links === 1 ? "" : "s"}
              {hover.status ? ` · ${hover.status}` : ""}
            </div>
          </div>
        )}
      </div>
      <p className="dim" style={{ marginTop: 8, fontSize: 12.5 }}>
        Node size = connections · dimmed = unverified · drag to rearrange, scroll to zoom, click to open the note.
      </p>
    </div>
  );
}
