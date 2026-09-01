import React, { useRef, useEffect, useCallback, useMemo } from 'react';

/**
 * Animated force-directed item network, drawn on a 2D canvas.
 *
 * Written against the canvas rather than a plotting library because the point
 * here is interaction: nodes settle under simulation, can be dragged, and a
 * neighbourhood lifts out of the graph on hover. At the sizes this renders
 * (tens to a few hundred nodes) a naive O(n^2) repulsion is comfortably inside
 * one frame, so there is no dependency to carry — d3-force exists in the tree
 * only transitively via plotly, which is not something to build on.
 *
 * Encodings:
 *   position  — force layout, seeded from the server's precomputed spring
 *               layout so the graph opens already legible and settles rather
 *               than exploding from random noise
 *   area      — number of datasets the item appears in
 *   fill      — mean normalized liking, on a single-hue sequential ramp
 *               (a categorical rainbow over 17 food categories is unreadable,
 *               and colour here is a magnitude, not an identity)
 */

const BLUE = '#085AB3';
const ORANGE = '#E78A00';

// Sequential ramp, light -> dark, one hue. Anchors chosen to stay legible on
// the off-white surface at the small end.
const RAMP = [
  [0.0, [206, 224, 245]],
  [0.5, [ 42, 120, 214]],
  [1.0, [  6,  49, 102]],
];

const lerp = (a, b, t) => a + (b - a) * t;

const rampColor = (t) => {
  const v = Math.max(0, Math.min(1, Number.isFinite(t) ? t : 0.5));
  let lo = RAMP[0];
  let hi = RAMP[RAMP.length - 1];
  for (let i = 0; i < RAMP.length - 1; i += 1) {
    if (v >= RAMP[i][0] && v <= RAMP[i + 1][0]) {
      lo = RAMP[i];
      hi = RAMP[i + 1];
      break;
    }
  }
  const span = hi[0] - lo[0] || 1;
  const t2 = (v - lo[0]) / span;
  const c = [0, 1, 2].map((i) => Math.round(lerp(lo[1][i], hi[1][i], t2)));
  return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
};

const ItemNetworkCanvas = ({
  data,
  height = 640,
  focusId = null,
  onSelect,
  onHoverChange,
  /** Edge weights are signed partial correlations rather than shared-dataset
   *  counts, so sign and magnitude are drawn instead of tie strength. */
  signed = false,
}) => {
  const wrapRef = useRef(null);
  const canvasRef = useRef(null);
  const stateRef = useRef({
    nodes: [], edges: [], adjacency: new Map(),
    hover: null, drag: null, alpha: 0,
    scale: 1, tx: 0, ty: 0, pan: null,
    width: 0, height, raf: null, seeded: null,
  });

  // Build the simulation bodies. Keyed on the payload so a filter change
  // reseeds rather than animating between unrelated graphs.
  const graph = useMemo(() => {
    if (!data?.nodes?.length) {
      return { nodes: [], edges: [], adjacency: new Map(), meanRange: [0, 1] };
    }

    // Marks shrink as the graph grows: at full density, radii tuned for 65
    // nodes overlap into a solid mass and hide the structure underneath.
    const count = data.nodes.length;
    const sizeScale = count > 700 ? 0.55 : count > 300 ? 0.72 : 1;

    const byLabel = new Map();
    const nodes = data.nodes.map((n) => {
      const body = {
        ...n,
        // Server coords are roughly [-1, 1]; spread them into canvas units.
        x: (n.x ?? 0) * 320,
        y: (n.y ?? 0) * 320,
        vx: 0,
        vy: 0,
        r: (4 + Math.sqrt(Math.max(1, n.frequency)) * 2.6) * sizeScale,
      };
      byLabel.set(n.label, body);
      return body;
    });

    // Edges reference nodes by group label, not by item id.
    const edges = [];
    const adjacency = new Map();
    (data.edges || []).forEach((e) => {
      const a = byLabel.get(e.source);
      const b = byLabel.get(e.target);
      if (!a || !b) return;
      edges.push({ a, b, weight: e.weight });
      if (!adjacency.has(a.id)) adjacency.set(a.id, new Set());
      if (!adjacency.has(b.id)) adjacency.set(b.id, new Set());
      adjacency.get(a.id).add(b.id);
      adjacency.get(b.id).add(a.id);
    });
    const means = nodes
      .map((n) => n.mean_rating)
      .filter((v) => Number.isFinite(v));
    const lo = means.length ? Math.min(...means) : 0;
    const hi = means.length ? Math.max(...means) : 1;
    const span = hi - lo || 1;
    nodes.forEach((n) => {
      n.shade = Number.isFinite(n.mean_rating) ? (n.mean_rating - lo) / span : 0.5;
    });

    return { nodes, edges, adjacency, meanRange: [lo, hi] };
  }, [data]);

  const kick = useCallback((alpha = 0.55) => {
    stateRef.current.alpha = Math.max(stateRef.current.alpha, alpha);
  }, []);

  /**
   * Ease the viewport toward the graph's bounding box. A force layout has no
   * fixed extent, so without this the graph reliably runs off the top of the
   * canvas as it settles. Tracks until the viewer pans, zooms, or drags —
   * after that the view is theirs.
   */
  const fitToBounds = useCallback((immediate = false) => {
    const st = stateRef.current;
    if (st.userAdjusted || !st.nodes.length || !st.width) return;

    let minX = Infinity; let minY = Infinity;
    let maxX = -Infinity; let maxY = -Infinity;
    st.nodes.forEach((n) => {
      minX = Math.min(minX, n.x - n.r); maxX = Math.max(maxX, n.x + n.r);
      minY = Math.min(minY, n.y - n.r); maxY = Math.max(maxY, n.y + n.r);
    });
    // Room for the labels that hang below each node, and for the legend.
    const padX = 40;
    const padTop = 24;
    const padBottom = 58;
    const w = Math.max(1, maxX - minX);
    const h = Math.max(1, maxY - minY);
    const target = Math.min(
      (st.width - padX * 2) / w,
      (st.height - padTop - padBottom) / h,
      1.6
    );
    const cx = (minX + maxX) / 2;
    const cy = (minY + maxY) / 2;
    const tTx = -cx * target;
    const tTy = -cy * target + (padTop - padBottom) / 2;

    const ease = immediate ? 1 : 0.12;
    st.scale += (target - st.scale) * ease;
    st.tx += (tTx - st.tx) * ease;
    st.ty += (tTy - st.ty) * ease;
    st.dirty = true;
  }, []);

  // --- simulation -----------------------------------------------------

  const step = useCallback(() => {
    const st = stateRef.current;
    const { nodes, edges } = st;
    if (!nodes.length) return;

    const alpha = st.alpha;
    const REPULSION = 2600;
    const SPRING = 0.0016;
    const CENTER = 0.0016;
    const DAMP = 0.86;

    // Repulsion through a uniform spatial grid rather than every pair. At the
    // full graph (~1,050 nodes) all-pairs is ~550k distance computations per
    // frame and drops frames; binning cuts it to the neighbours that can
    // actually matter, since the force falls off as 1/d^2 and is negligible
    // past a couple of cells.
    const CELL = 90;
    const grid = new Map();
    const key = (cx, cy) => `${cx},${cy}`;
    nodes.forEach((n) => {
      const cx = Math.floor(n.x / CELL);
      const cy = Math.floor(n.y / CELL);
      const k = key(cx, cy);
      let bucket = grid.get(k);
      if (!bucket) { bucket = []; grid.set(k, bucket); }
      bucket.push(n);
      n._cx = cx; n._cy = cy;
    });

    nodes.forEach((a) => {
      for (let ox = -1; ox <= 1; ox += 1) {
        for (let oy = -1; oy <= 1; oy += 1) {
          const bucket = grid.get(key(a._cx + ox, a._cy + oy));
          if (!bucket) continue;
          for (let i = 0; i < bucket.length; i += 1) {
            const b = bucket[i];
            // Each unordered pair once: skip until b is "after" a.
            if (b === a) continue;
            if (b._cx < a._cx || (b._cx === a._cx && b._cy < a._cy)) continue;
            if (b._cx === a._cx && b._cy === a._cy && bucket.indexOf(a) > i) continue;

            let dx = b.x - a.x;
            let dy = b.y - a.y;
            let d2 = dx * dx + dy * dy;
            if (d2 < 1) { d2 = 1; dx = (Math.random() - 0.5); dy = (Math.random() - 0.5); }
            const d = Math.sqrt(d2);
            const force = (REPULSION / d2) * alpha;
            const fx = (dx / d) * force;
            const fy = (dy / d) * force;
            a.vx -= fx; a.vy -= fy;
            b.vx += fx; b.vy += fy;
          }
        }
      }
    });

    edges.forEach(({ a, b, weight }) => {
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const d = Math.sqrt(dx * dx + dy * dy) || 1;
      const target = 46 + 120 / (1 + Math.abs(weight) * (st.signed ? 12 : 1));
      const f = (d - target) * SPRING * alpha * Math.min(3, weight);
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    });

    // Weaker horizontal centring on a wide canvas: an isotropic force settles
    // into a circle, which leaves a 16:10 viewport mostly empty.
    const aspect = st.width && st.height ? Math.sqrt(st.width / st.height) : 1;
    const centerX = CENTER / aspect;
    const centerY = CENTER * aspect;

    nodes.forEach((n) => {
      n.vx -= n.x * centerX * alpha;
      n.vy -= n.y * centerY * alpha;
      if (st.drag && st.drag.node === n) {
        n.x = st.drag.x; n.y = st.drag.y; n.vx = 0; n.vy = 0;
        return;
      }
      n.vx *= DAMP; n.vy *= DAMP;
      n.x += n.vx; n.y += n.vy;
    });

    st.alpha *= 0.985;
    if (st.alpha < 0.004) st.alpha = 0;
  }, []);

  // --- drawing --------------------------------------------------------

  const draw = useCallback(() => {
    const st = stateRef.current;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const { width, height: h, scale, tx, ty } = st;
    const dpr = window.devicePixelRatio || 1;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, width, h);
    ctx.save();
    ctx.translate(width / 2 + tx, h / 2 + ty);
    ctx.scale(scale, scale);

    const signed = st.signed;
    const maxWeight = st.maxWeight || 1;
    const active = st.hover || st.focus;
    const neighbours = active ? st.adjacency.get(active.id) : null;
    const isLit = (n) => !active || n === active || (neighbours && neighbours.has(n.id));

    // Edges first, as curves. A quadratic bend keeps parallel bundles legible
    // where straight segments would overlay into a single grey mass.
    st.edges.forEach(({ a, b, weight }) => {
      const lit = !active || (isLit(a) && isLit(b) && (a === active || b === active));
      const dx = b.x - a.x;
      const dy = b.y - a.y;
      const mx = (a.x + b.x) / 2;
      const my = (a.y + b.y) / 2;
      const cx = mx - dy * 0.12;
      const cy = my + dx * 0.12;

      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.quadraticCurveTo(cx, cy, b.x, b.y);
      // `signed` networks (partial correlations) carry meaning in the sign:
      // blue draws items rated alike, orange items rated oppositely.
      const w = signed ? Math.abs(weight) / maxWeight : weight;
      const alpha = signed
        ? Math.min(0.75, 0.12 + w * 0.75)
        : Math.min(0.34, 0.10 + weight * 0.014);
      ctx.lineWidth = lit
        ? (signed ? Math.min(3, 0.4 + w * 3.2) : Math.min(2.4, 0.5 + weight * 0.12))
        : 0.5;
      ctx.strokeStyle = lit
        ? (signed && weight < 0
            ? `rgba(231, 138, 0, ${active ? 0.6 : alpha})`
            : `rgba(8, 90, 179, ${active ? 0.6 : alpha})`)
        : 'rgba(150, 150, 150, 0.06)';
      ctx.stroke();
    });

    // Nodes, largest last so big items sit on top of the crowd.
    const ordered = [...st.nodes].sort((p, q) => p.r - q.r);
    ordered.forEach((n) => {
      const lit = isLit(n);
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fillStyle = rampColor(n.shade);
      ctx.globalAlpha = lit ? 1 : 0.16;
      ctx.fill();
      // A surface-coloured ring keeps overlapping nodes countable.
      ctx.lineWidth = 1.5;
      ctx.strokeStyle = n === active ? ORANGE : '#ffffff';
      if (n === active) ctx.lineWidth = 2.5;
      ctx.stroke();
      ctx.globalAlpha = 1;
    });

    // Labels. Greedy placement, biggest node first: a label is drawn only if
    // its box is still clear, so a dense cluster loses its smallest labels
    // instead of turning into overstruck text. When a neighbourhood is lit,
    // that set is labelled regardless -- it is what the viewer asked to read.
    ctx.font = '500 11px -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';

    const candidates = [...st.nodes]
      .filter((n) => (active ? isLit(n) : true))
      .sort((p, q) => q.r - p.r);

    const placed = [];
    const overlaps = (a, b) =>
      a.x0 < b.x1 && a.x1 > b.x0 && a.y0 < b.y1 && a.y1 > b.y0;

    candidates.forEach((n) => {
      const text = n.label;
      const w = ctx.measureText(text).width;
      const x = n.x;
      const y = n.y + n.r + 3;
      // Boxes are in world units; pad by a couple of device px worth.
      const pad = 2 / scale;
      const box = {
        x0: x - w / 2 - pad, x1: x + w / 2 + pad,
        y0: y - pad, y1: y + 12 + pad,
      };
      const lit = active && isLit(n);
      if (!lit && placed.some((b) => overlaps(box, b))) return;
      placed.push(box);

      ctx.lineWidth = 3;
      ctx.strokeStyle = 'rgba(255,255,255,0.92)';
      ctx.strokeText(text, x, y);
      ctx.fillStyle = n === active ? '#1f1f1f' : '#3d3d3d';
      ctx.globalAlpha = active && !lit ? 0.25 : 1;
      ctx.fillText(text, x, y);
      ctx.globalAlpha = 1;
    });

    ctx.restore();
  }, []);

  // --- animation loop --------------------------------------------------

  useEffect(() => {
    const st = stateRef.current;
    st.nodes = graph.nodes;
    st.edges = graph.edges;
    st.adjacency = graph.adjacency;
    st.hover = null;
    st.focus = null;
    st.signed = signed;
    st.maxWeight = graph.edges.length
      ? Math.max(...graph.edges.map((e) => Math.abs(e.weight)), 1e-6)
      : 1;
    st.alpha = 0.9;
    st.userAdjusted = false;

    let running = true;
    const loop = () => {
      if (!running) return;
      if (st.alpha > 0 || st.dirty) {
        if (st.alpha > 0) step();
        fitToBounds();
        draw();
        st.dirty = false;
      }
      st.raf = window.requestAnimationFrame(loop);
    };
    st.raf = window.requestAnimationFrame(loop);
    return () => {
      running = false;
      if (st.raf) window.cancelAnimationFrame(st.raf);
    };
  }, [graph, step, draw, fitToBounds, signed]);

  // Keep the backing store matched to the element and the pixel ratio.
  useEffect(() => {
    const wrap = wrapRef.current;
    const canvas = canvasRef.current;
    if (!wrap || !canvas) return undefined;
    const resize = () => {
      const st = stateRef.current;
      const dpr = window.devicePixelRatio || 1;
      const w = wrap.clientWidth;
      st.width = w;
      st.height = height;
      canvas.width = Math.floor(w * dpr);
      canvas.height = Math.floor(height * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${height}px`;
      st.userAdjusted = false;
      st.dirty = true;
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(wrap);
    return () => ro.disconnect();
  }, [height]);

  // External focus (the search box) drives the same highlight as hover.
  useEffect(() => {
    const st = stateRef.current;
    st.focus = focusId ? st.nodes.find((n) => n.id === focusId) || null : null;
    st.dirty = true;
    if (st.focus) kick(0.28);
  }, [focusId, graph, kick]);

  // --- pointer handling ------------------------------------------------

  const toWorld = (clientX, clientY) => {
    const st = stateRef.current;
    const rect = canvasRef.current.getBoundingClientRect();
    return {
      x: (clientX - rect.left - st.width / 2 - st.tx) / st.scale,
      y: (clientY - rect.top - st.height / 2 - st.ty) / st.scale,
    };
  };

  const pick = (wx, wy) => {
    const st = stateRef.current;
    let best = null;
    let bestD = Infinity;
    st.nodes.forEach((n) => {
      const d = Math.hypot(n.x - wx, n.y - wy);
      if (d < Math.max(n.r + 4, 10) && d < bestD) { best = n; bestD = d; }
    });
    return best;
  };

  const onPointerMove = (e) => {
    const st = stateRef.current;
    const { x, y } = toWorld(e.clientX, e.clientY);

    if (st.drag) {
      st.drag.x = x; st.drag.y = y;
      st.userAdjusted = true;
      kick(0.32);
      return;
    }
    if (st.pan) {
      st.tx = st.pan.tx + (e.clientX - st.pan.px);
      st.ty = st.pan.ty + (e.clientY - st.pan.py);
      st.dirty = true;
      return;
    }
    const hit = pick(x, y);
    if (hit !== st.hover) {
      st.hover = hit;
      st.dirty = true;
      if (onHoverChange) onHoverChange(hit || null);
      canvasRef.current.style.cursor = hit ? 'pointer' : 'grab';
    }
  };

  const onPointerDown = (e) => {
    const st = stateRef.current;
    const { x, y } = toWorld(e.clientX, e.clientY);
    const hit = pick(x, y);
    canvasRef.current.setPointerCapture(e.pointerId);
    if (hit) {
      st.drag = { node: hit, x, y };
      st.focus = hit;
      st.dirty = true;
      if (onSelect) onSelect(hit);
      kick(0.3);
    } else {
      st.pan = { px: e.clientX, py: e.clientY, tx: st.tx, ty: st.ty };
      st.userAdjusted = true;
      canvasRef.current.style.cursor = 'grabbing';
    }
  };

  const endPointer = (e) => {
    const st = stateRef.current;
    if (canvasRef.current?.hasPointerCapture?.(e.pointerId)) {
      canvasRef.current.releasePointerCapture(e.pointerId);
    }
    st.drag = null;
    st.pan = null;
    if (canvasRef.current) canvasRef.current.style.cursor = st.hover ? 'pointer' : 'grab';
  };

  // React attaches onWheel passively, so preventDefault() inside it is
  // ignored and the page scrolls instead of the graph zooming. Bind it
  // directly with { passive: false }.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const handler = (e) => {
      e.preventDefault();
      const st = stateRef.current;
      st.userAdjusted = true;
      st.scale = Math.max(0.35, Math.min(4, st.scale * (e.deltaY < 0 ? 1.12 : 0.893)));
      st.dirty = true;
    };
    canvas.addEventListener('wheel', handler, { passive: false });
    return () => canvas.removeEventListener('wheel', handler);
  }, []);

  return (
    <div ref={wrapRef} style={{ position: 'relative', width: '100%' }}>
      <canvas
        ref={canvasRef}
        onPointerMove={onPointerMove}
        onPointerDown={onPointerDown}
        onPointerUp={endPointer}
        onPointerCancel={endPointer}
        onPointerLeave={(e) => {
          endPointer(e);
          const st = stateRef.current;
          if (st.hover) { st.hover = null; st.dirty = true; if (onHoverChange) onHoverChange(null); }
        }}
        style={{
          display: 'block',
          width: '100%',
          height,
          borderRadius: 6,
          background:
            'radial-gradient(circle at 50% 42%, #ffffff 0%, #f7f9fc 55%, #eef2f7 100%)',
          cursor: 'grab',
          touchAction: 'none',
        }}
      />
      <NetworkLegend range={graph.meanRange} />
    </div>
  );
};

/** Size and colour keys. Colour is a magnitude here, so it gets a ramp. */
const NetworkLegend = ({ range }) => (
  <div
    style={{
      position: 'absolute',
      left: 14,
      bottom: 12,
      display: 'flex',
      alignItems: 'center',
      gap: 18,
      fontSize: 13.5,
      color: '#4a4a4a',
      background: 'rgba(255,255,255,0.82)',
      padding: '6px 10px',
      borderRadius: 6,
      pointerEvents: 'none',
    }}
  >
    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      Mean liking
      <span
        style={{
          display: 'inline-block',
          width: 84,
          height: 8,
          borderRadius: 2,
          background: `linear-gradient(90deg, ${rampColor(0)}, ${rampColor(0.5)}, ${rampColor(1)})`,
        }}
      />
      <span style={{ color: '#5a5a5a' }}>
        {range ? `${range[0].toFixed(2)} → ${range[1].toFixed(2)}` : 'low → high'}
      </span>
    </span>
    <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
      Size
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: BLUE, opacity: 0.65 }} />
        <span style={{ width: 11, height: 11, borderRadius: '50%', background: BLUE, opacity: 0.65 }} />
      </span>
      <span style={{ color: '#5a5a5a' }}>studies</span>
    </span>
  </div>
);

export default ItemNetworkCanvas;
