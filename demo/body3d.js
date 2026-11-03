// 3D body viewer for the report map (three.js + GSAP, both vendored so the demo works offline).
// Frame: x = patient's left, y = up, z = anterior (metres). The page owns the data; this module owns the scene.
//
//   const viewer = await createBodyViewer(containerEl, { onSelect(regionId) {}, onFail(reason) {} });
//   viewer.setMarkers([{ id, status: "finding"|"uncertain"|"normal", count, label, aria }]);
//   viewer.focus(regionId | null);      // camera glide + organ highlight (null = back to overview)
import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const COLORS = {
  lung_r_upper: 0xe7a3a8, lung_r_mid: 0xe7a3a8, lung_r_lower: 0xe7a3a8, lung_l_upper: 0xe7a3a8, lung_l_lower: 0xe7a3a8,
  heart: 0xb3202f, aorta: 0xc0392b, airway: 0xd9d4c7, diaphragm: 0xb97a68, liver: 0x8c4a2f, stomach: 0xc98a7d,
  brain: 0xe8c9c2, ribs: 0xece4d0, sternum: 0xece4d0, clavicles: 0xece4d0, spine: 0xe6dcc4, skull: 0xefe8d8, pelvis: 0xe6dcc4,
  arm_bones: 0xe6dcc4, leg_bones: 0xe6dcc4,
};
const DIM = 0.2;            // opacity of organs that are not the focus
const FOV = 30;
const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
const wrapPi = (a) => Math.atan2(Math.sin(a), Math.cos(a));

function glassSkin() {
  return new THREE.ShaderMaterial({
    transparent: true, depthWrite: false, side: THREE.FrontSide,
    uniforms: { uBase: { value: new THREE.Color(0xf1c7b3) }, uRim: { value: new THREE.Color(0xbfdcff) }, uOpacity: { value: 1 } },
    vertexShader: `varying vec3 vN; varying vec3 vV;
      void main(){ vec4 mv = modelViewMatrix * vec4(position,1.0); vN = normalize(normalMatrix * normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix * mv; }`,
    fragmentShader: `varying vec3 vN; varying vec3 vV; uniform vec3 uBase; uniform vec3 uRim; uniform float uOpacity;
      void main(){ float f = pow(1.0 - abs(dot(normalize(vN), normalize(vV))), 2.2);
        vec3 c = mix(uBase, uRim, f); gl_FragColor = vec4(c, (0.07 + 0.55 * f) * uOpacity); }`,
  });
}

export async function createBodyViewer(container, { onSelect = () => {}, onFail = () => {} } = {}) {
  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  } catch (e) { onFail("WebGL is not available"); return null; }
  renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.domElement.className = "body3d-canvas";
  renderer.domElement.setAttribute("aria-hidden", "true");
  container.prepend(renderer.domElement);
  const pinLayer = document.createElement("div");
  pinLayer.className = "pins";
  container.append(pinLayer);

  let anatomy, gltf;
  try {
    const [meta, model] = await Promise.all([
      fetch("/assets/anatomy.json").then((r) => { if (!r.ok) throw new Error("anatomy.json " + r.status); return r.json(); }),
      new GLTFLoader().loadAsync("/assets/anatomy.glb"),
    ]);
    anatomy = meta; gltf = model;
  } catch (e) { renderer.dispose(); renderer.domElement.remove(); pinLayer.remove(); onFail(String(e.message || e)); return null; }

  // ---------- scene ----------
  const scene = new THREE.Scene();
  scene.add(new THREE.HemisphereLight(0xffffff, 0x7d8ba0, 1.25));
  const key = new THREE.DirectionalLight(0xffffff, 2.1); key.position.set(1.5, 2.2, 3); scene.add(key);
  const rim = new THREE.DirectionalLight(0x9cc2ff, 1.4); rim.position.set(-2, 1, -2.5); scene.add(rim);
  const camera = new THREE.PerspectiveCamera(FOV, 1, 0.05, 20);
  const controls = new OrbitControls(camera, renderer.domElement);
  renderer.domElement.style.touchAction = "pan-y pinch-zoom";   // OrbitControls sets "none", which traps page scroll on phones
  controls.enableDamping = !reduceMotion(); controls.dampingFactor = 0.08; controls.enablePan = false;
  // wheel zoom must not trap page scroll: zoom only while the pointer is pressed or Ctrl/Meta is held
  controls.enableZoom = false;
  let pressed = false, modKey = false;
  const syncZoom = () => { controls.enableZoom = pressed || modKey; };
  renderer.domElement.addEventListener("wheel", (e) => { controls.enableZoom = pressed || e.ctrlKey || e.metaKey; }, { capture: true });
  renderer.domElement.addEventListener("pointerdown", () => { pressed = true; syncZoom(); });
  addEventListener("pointerup", () => { pressed = false; syncZoom(); });
  addEventListener("pointercancel", () => { pressed = false; syncZoom(); });
  addEventListener("keydown", (e) => { if (e.key === "Control" || e.key === "Meta") { modKey = true; syncZoom(); } });
  addEventListener("keyup", (e) => { if (e.key === "Control" || e.key === "Meta") { modKey = false; syncZoom(); } });
  addEventListener("blur", () => { pressed = modKey = false; syncZoom(); });
  controls.minPolarAngle = 0.5; controls.maxPolarAngle = Math.PI - 0.5;

  const organs = new Map();      // node name -> [materials]
  const meshesByNode = new Map();
  let skin = null;
  gltf.scene.traverse((o) => {
    if (!o.isMesh) return;
    const name = o.name;
    if (name === "skin") {
      skin = glassSkin(); o.material = skin; o.renderOrder = 10; return;
    }
    const shell = name.endsWith("_hull");     // translucent lung shell around the airway tree
    o.material = new THREE.MeshStandardMaterial({
      color: shell ? 0xf0aeb4 : COLORS[name] ?? 0xdddddd, roughness: shell ? 0.9 : 0.55, metalness: 0.02, side: THREE.DoubleSide,
      transparent: true, opacity: shell ? 0.3 : name === "skull" ? 0.45 : 1, depthWrite: !shell,
      emissive: 0xffc83d, emissiveIntensity: 0,
    });
    if (shell) o.renderOrder = 5;
    o.material.userData.base = o.material.opacity;
    organs.set(name, [o.material]); meshesByNode.set(name, o);
  });
  scene.add(gltf.scene);

  // overview framing: the chest (default) or the whole body, head to feet
  let viewMode = "chest";
  const overview = () => (viewMode === "body" && anatomy.full) || anatomy.overview;
  const baseSph = { az: 0.35, pol: 1.45 };
  function fitDistance() {
    const ov = overview(), t = Math.tan((FOV * Math.PI) / 360), aspect = camera.aspect;
    return Math.max(ov.height / 2 / t, ov.width / 2 / (t * aspect)) * 1.05;
  }
  const state = { az: baseSph.az, pol: baseSph.pol, dist: 1.6, tx: 0, ty: 0, tz: 0 };
  const overviewState = () => { const [tx, ty, tz] = overview().target; return { az: baseSph.az, pol: baseSph.pol, dist: fitDistance(), tx, ty, tz }; };
  function applyState() {
    const s = state, sp = Math.sin(s.pol);
    controls.target.set(s.tx, s.ty, s.tz);
    camera.position.set(s.tx + s.dist * sp * Math.sin(s.az), s.ty + s.dist * Math.cos(s.pol), s.tz + s.dist * sp * Math.cos(s.az));
    camera.lookAt(controls.target);
  }
  function readState() {
    const off = camera.position.clone().sub(controls.target), sph = new THREE.Spherical().setFromVector3(off);
    Object.assign(state, { az: sph.theta, pol: sph.phi, dist: sph.radius, tx: controls.target.x, ty: controls.target.y, tz: controls.target.z });
  }

  // ---------- render loop (only while something moves) ----------
  let animating = false, idleUntil = 0, hidden = document.hidden, markers = new Map();
  const wake = (ms = 1500) => { idleUntil = performance.now() + ms; if (!animating && !hidden) { animating = true; renderer.setAnimationLoop(frame); } };
  function frame(now) {
    controls.update();
    updatePins();
    renderer.render(scene, camera);
    if (now > idleUntil && !tween) { animating = false; renderer.setAnimationLoop(null); }
  }
  controls.addEventListener("change", () => wake());
  controls.addEventListener("start", () => { if (tween) tween.kill(); tween = null; wake(); });
  document.addEventListener("visibilitychange", () => { hidden = document.hidden; if (hidden) { animating = false; renderer.setAnimationLoop(null); } else wake(); });

  function resize() {
    const w = container.clientWidth, h = container.clientHeight;
    if (!w || !h) return;
    renderer.setSize(w, h, false); renderer.domElement.style.width = w + "px"; renderer.domElement.style.height = h + "px";
    camera.aspect = w / h; camera.updateProjectionMatrix();
    if (!focused && !tween) { state.dist = fitDistance(); applyState(); }
    wake();
  }
  new ResizeObserver(resize).observe(container);

  // ---------- pins ----------
  const v3 = new THREE.Vector3();
  function updatePins() {
    const w = container.clientWidth, h = container.clientHeight;
    const center = controls.target, camDir = camera.getWorldDirection(new THREE.Vector3());
    const centerDepth = center.clone().sub(camera.position).dot(camDir);
    const list = [];
    for (const m of markers.values()) {
      v3.set(...m.anchor);
      const depth = v3.clone().sub(camera.position).dot(camDir);
      v3.project(camera);
      list.push({ m, x: (v3.x * 0.5 + 0.5) * w, y: (-v3.y * 0.5 + 0.5) * h, far: depth > centerDepth + 0.05 });
    }
    for (let it = 0; it < 4; it++) {          // keep pins readable: nudge apart pins that land on top of each other
      for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
        const a = list[i], b = list[j], dx = b.x - a.x, dy = b.y - a.y, d = Math.hypot(dx, dy) || 0.01, min = matchMedia("(pointer: coarse)").matches ? 44 : 26;
        if (d < min) { const k = (min - d) / 2 / d; a.x -= dx * k; a.y -= dy * k; b.x += dx * k; b.y += dy * k; }
      }
    }
    for (const p of list) {
      p.m.el.style.transform = `translate(${p.x.toFixed(1)}px, ${p.y.toFixed(1)}px) translate(-50%, -50%)`;
      p.m.el.dataset.far = p.far ? "1" : "0";
      // pins outside the canvas leave the tab order (visibility:hidden)
      p.m.el.style.visibility = (p.x < 0 || p.x > w || p.y < 0 || p.y > h) ? "hidden" : "";
      // keep the label inside the figure: beside the pin when there is room, else below it, shifted to fit
      const lw = 36 + p.m.labelLen * 6.6;
      const side = w - p.x - 16 >= lw ? "r" : p.x - 16 >= lw ? "l" : "b";
      p.m.el.dataset.side = side;
      if (side === "b") {
        const left = p.x - lw / 2, right = p.x + lw / 2;
        p.m.el.style.setProperty("--lx", (left < 6 ? 6 - left : right > w - 6 ? w - 6 - right : 0).toFixed(0) + "px");
      }
    }
  }
  let markerSig = "";
  function setMarkers(items) {
    pinLayer.innerHTML = ""; markers = new Map();
    const sigParts = [];
    // tab order follows the picture: top of the body first
    const ordered = [...items].sort((a, b) => ((anatomy.regions[b.id]?.anchor[1] ?? 0) - (anatomy.regions[a.id]?.anchor[1] ?? 0)));
    for (const it of ordered) {
      const reg = anatomy.regions[it.id];
      if (!reg) continue;
      const el = document.createElement("button");
      el.type = "button"; el.className = `mk ${it.status}`; el.dataset.r = it.id; el.setAttribute("aria-pressed", "false");
      el.setAttribute("aria-label", it.aria);
      const glyph = { finding: "!", uncertain: "?", normal: "&#10003;" }[it.status];
      el.innerHTML = `<span class="mk-dot" aria-hidden="true">${glyph}</span>` +
        `<span class="mk-label" aria-hidden="true"><i class="d"></i>${it.label}${it.count > 1 ? ` <b>&times;${it.count}</b>` : ""}</span>` +
        (it.count > 1 ? `<span class="mk-count" aria-hidden="true">${it.count}</span>` : "");
      el.onclick = () => onSelect(it.id);
      pinLayer.append(el);
      sigParts.push(it.id + ":" + it.status);
      markers.set(it.id, { el, anchor: reg.anchor, labelLen: it.label.replace(/&[a-z#0-9]+;/g, "x").length + (it.count > 1 ? 3 : 0) });
    }
    const sig = sigParts.join("|"), changed = sig !== markerSig;   // same pins as before: no replay
    markerSig = sig;
    if (changed && window.gsap && !reduceMotion()) gsap.fromTo(pinLayer.querySelectorAll(".mk-dot"), { scale: 0.3, opacity: 0 }, { scale: 1, opacity: 1, duration: 0.4, stagger: { amount: 0.3 }, ease: "back.out(1.2)", overwrite: true, clearProps: "scale,opacity" });
    wake();
  }

  // ---------- focus: camera glide + organ highlight ----------
  let tween = null, focused = null;
  function viewFor(id, anchor) {
    const right = /(^|-)r($|-)/.test(id), left = /(^|-)l($|-)/.test(id);
    let az = right ? -0.75 : left ? 0.75 : 0.3, pol = 1.42, dist = 0.7;
    if (id === "spine") { az = Math.PI - 0.35; dist = 0.65; }
    if (id === "heart" || id === "mediastinum") { az = 0.25; dist = 0.55; }
    if (id === "head" || id === "neck") dist = 0.8;
    if (id === "abdomen" || id === "pelvis" || id === "diaphragm") dist = 0.85;
    if (id.startsWith("pleura")) { az = right ? -1.15 : 1.15; dist = 0.7; }
    if (id === "ribs") { az = -1.0; dist = 0.8; }
    return { az, pol, dist, tx: anchor[0], ty: anchor[1], tz: anchor[2] };
  }
  function highlight(nodes, on) {
    const active = new Set(on ? nodes : []);
    for (const [name, mats] of organs) for (const m of mats) {
      const isOn = active.has(name), dim = on && !isOn;
      const to = { opacity: dim ? m.userData.base * DIM : m.userData.base, emissiveIntensity: isOn ? 0.5 : 0 };
      if (window.gsap && !reduceMotion()) gsap.to(m, { ...to, duration: 0.5, ease: "power2.out", overwrite: "auto", onUpdate: () => wake(600) });
      else Object.assign(m, to);
    }
    if (skin) {
      if (window.gsap && !reduceMotion()) gsap.to(skin.uniforms.uOpacity, { value: on ? 0.35 : 1, duration: 0.5, overwrite: "auto", onUpdate: () => wake(600) });
      else skin.uniforms.uOpacity.value = on ? 0.35 : 1;
    }
    wake(900);
  }
  function glideTo(end) {
    readState();
    if (tween) tween.kill();
    if (!window.gsap || reduceMotion()) { Object.assign(state, end); applyState(); controls.update(); wake(); return; }
    const from = { ...state }, delta = wrapPi(end.az - from.az), p = { k: 0 };
    tween = gsap.to(p, {
      k: 1, duration: 1.1, ease: "power3.inOut",
      onUpdate: () => {
        const k = p.k;
        Object.assign(state, { az: from.az + delta * k, pol: from.pol + (end.pol - from.pol) * k, dist: from.dist + (end.dist - from.dist) * k,
          tx: from.tx + (end.tx - from.tx) * k, ty: from.ty + (end.ty - from.ty) * k, tz: from.tz + (end.tz - from.tz) * k });
        applyState(); wake(600);
      },
      onComplete: () => { tween = null; wake(900); },
    });
    wake(1500);
  }
  function focus(id) {
    focused = id && anatomy.regions[id] ? id : null;
    for (const [rid, m] of markers) { m.el.setAttribute("aria-pressed", String(rid === focused)); }
    if (focused) {
      const reg = anatomy.regions[focused];
      highlight(reg.nodes, true); glideTo(viewFor(focused, reg.anchor));
    } else {
      highlight([], false);
      glideTo(overviewState());
    }
  }

  function setView(mode) {
    viewMode = mode === "body" ? "body" : "chest";
    if (!focused) glideTo(overviewState());
  }

  // clicking an organ in the scene selects the first marker whose region includes it (drag = rotate, not click)
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2();
  let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 4) { down = null; return; }
    down = null;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects([...meshesByNode.values()], false)[0];
    if (!hit) return;
    for (const [rid] of markers) if (anatomy.regions[rid].nodes.includes(hit.object.name)) { onSelect(rid); return; }
  });

  // ---------- start ----------
  Object.assign(state, overviewState()); resize(); applyState();
  if (window.gsap && !reduceMotion()) {
    gsap.from(gltf.scene.position, { y: -0.04, duration: 1.0, ease: "power2.out" });
    if (skin) gsap.from(skin.uniforms.uOpacity, { value: 0, duration: 1.2, ease: "power1.out", onUpdate: () => wake(400) });
    // reveal: swing in from the patient's right and settle on the front view
    const k = { v: 0 }, swing = 0.5;
    state.az = baseSph.az - swing; applyState();
    tween = gsap.to(k, { v: 1, duration: 1.4, ease: "power3.out",
      onUpdate: () => { state.az = baseSph.az - swing * (1 - k.v); applyState(); wake(600); },
      onComplete: () => { tween = null; wake(900); } });
  }
  wake(2800);
  container.__body3d = { scene, camera, controls, organs, meshesByNode, renderer };   // inspection handle for debugging
  return {
    setMarkers, focus, setView, hasFullBody: !!anatomy.full, credit: anatomy.credit || "",
    pinFor: (id) => markers.get(id)?.el || null,
  };
}
