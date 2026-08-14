<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import ButtonCustom from '@/components/ButtonCustom.vue';
import song from '@/assets/audio/TheEdenProject-TimesLikeThese.mp3';

type Bubble = {
  x: number;
  y: number;
  r: number;
  vx: number;
  vy: number;
  color: string;
  baseColor: string;
  cellPosition?: { x: number; y: number };
};

const SPEED = 1.5,
  SPREAD = 15,
  ANGLE_STEP = 10,
  MAX_BUBBLES = 25_000,
  CELL_SIZE = 250,
  AUDIO_VISUALIZER_RADIUS = 100;

// Audio
const audioContext = new AudioContext(),
  audioRef = ref<HTMLMediaElement | null>(null);

let track: MediaElementAudioSourceNode, analyser: AnalyserNode;

// Canvas
const canvas = ref<HTMLCanvasElement | null>(null),
  visualizerView = ref<HTMLDivElement | null>(null),
  mode = ref<'pulsing' | 'linear' | 'collision' | 'hole' | 'audio'>('linear');

const bubbles: Bubble[] = [],
  bubbleGrid = new Map<string, Bubble[]>();

let observer: ResizeObserver | null = null,
  mouseX: number | null = null,
  mouseY: number | null = null,
  frame = 0,
  angle = 0,
  pulsing: boolean = false;

let interval: number | null = null,
  counter: number = 0,
  stopped: boolean = false;

const random = (min: number, max: number) => Math.random() * (max - min) + min,
  randomInt = (min: number, max: number) => Math.floor(random(Math.ceil(min), Math.floor(max))),
  randomColor = () => `rgba(0, ${randomInt(0, 255)}, ${randomInt(0, 127)})`;

const initAudioElements = () => {
  if (!audioRef.value) return;
  track = audioContext.createMediaElementSource(audioRef.value);

  // Analyser node setup
  analyser = audioContext.createAnalyser();
  analyser.fftSize = 2048; // Set the FFT size for the analyser, default also is 2048, which gives us 1024 data points for the time domain data.

  track.connect(analyser); // Connect the track to the analyser
  analyser.connect(audioContext.destination); // Connect the analyser to the destination (speakers)
};

const playOrPause = async () => {
  if (audioContext.state === 'suspended') {
    await audioContext.resume();
  }

  if (audioRef.value?.dataset?.playing === 'true') {
    audioRef.value.pause();
    audioRef.value.dataset.playing = 'false';
    console.log('Paused: Eden - Times Like These');
  } else if (audioRef.value) {
    await audioRef.value!.play();
    audioRef.value.dataset.playing = 'true';
    console.log('Now playing: Eden - Times Like These');
  }
};

const initCanvas = () => {
  if (!canvas.value) return;

  canvas.value.width = canvas.value.clientWidth;
  canvas.value.height = canvas.value.clientHeight;
};

const updateMousePosition = (evt: MouseEvent) => {
  if (!canvas.value) return;

  stopped = false;

  const rect = canvas.value.getBoundingClientRect();

  mouseX = evt.clientX - rect.left;
  mouseY = evt.clientY - rect.top;
};

const stopSpawn = () => {
  if (mode.value === 'audio') return;
  bubbles.length = 0;
  mouseX = null;
  mouseY = null;
  stopped = true;

  if (!canvas.value) return;
  const ctx = canvas.value.getContext('2d');
  ctx?.clearRect(0, 0, canvas.value.width, canvas.value.height);
};

const stopAudio = () => {
  if (audioRef.value) {
    audioRef.value.pause();
    audioRef.value.currentTime = 0;
    audioRef.value.dataset.playing = 'false';
  }
};

const setMode = (newMode: 'pulsing' | 'linear' | 'collision' | 'hole' | 'audio') => {
  mode.value = newMode;
  if (newMode !== 'audio') {
    stopAudio();
  }
};

// BUBBLE COLLISION MODE -----------------------------------------------------------------------------------------------------------------------------

// Grid handling
const updateBubbleGrid = () => {
  bubbleGrid.clear();

  for (const bubble of bubbles) {
    const cellX = Math.floor(bubble.x / CELL_SIZE),
      cellY = Math.floor(bubble.y / CELL_SIZE),
      cellKey = `${cellX},${cellY}`;

    if (!bubbleGrid.has(cellKey)) {
      bubbleGrid.set(cellKey, []);
    }

    bubbleGrid.get(cellKey)?.push(bubble);
  }
};

const detectBubbleCollision = (bubble: Bubble) => {
  const cellX = Math.floor(bubble.x / CELL_SIZE),
    cellY = Math.floor(bubble.y / CELL_SIZE);

  const gridCellBubbles = bubbleGrid.get(`${cellX},${cellY}`) || [];

  for (const otherBubble of gridCellBubbles) {
    // Ignore comparing a bubble with itself.
    if (bubble === otherBubble) continue;

    // Vector from the other bubble to the current bubble.
    const dx = bubble.x - otherBubble.x,
      dy = bubble.y - otherBubble.y;

    // Combined collision radius and squared distance between centers.
    // Squared values avoid an expensive Math.sqrt() for non-colliding bubbles.
    const radius = bubble.r + otherBubble.r,
      distanceSquared = dx * dx + dy * dy;

    // If the distance between centers is greater than the combined radii,
    // the circles cannot overlap.
    if (distanceSquared >= radius * radius) continue;

    bubble.color = 'rgba(255, 0, 0, 0.75)';
    otherBubble.color = 'rgba(255, 0, 0, 0.75)';

    // Actual distance is only needed once we know a collision occurred.
    // The fallback prevents division by zero when two bubbles share*
    // the exact same center.
    const distance = Math.sqrt(distanceSquared) || 0.0001,
      invDistance = 1 / distance;

    // Normalized collision direction (unit vector).
    // This tells us the direction in which the bubbles should separate.
    const nx = dx * invDistance,
      ny = dy * invDistance;

    // Bubble radius is used as a simple approximation of mass.
    const totalMass = bubble.r + otherBubble.r;

    // Calculate new velocities using a simplified elastic collision formula.
    const newVx1 = (bubble.vx * (bubble.r - otherBubble.r) + 2 * otherBubble.r * otherBubble.vx) / totalMass,
      newVy1 = (bubble.vy * (bubble.r - otherBubble.r) + 2 * otherBubble.r * otherBubble.vy) / totalMass;

    const newVx2 = (otherBubble.vx * (otherBubble.r - bubble.r) + 2 * bubble.r * bubble.vx) / totalMass,
      newVy2 = (otherBubble.vy * (otherBubble.r - bubble.r) + 2 * bubble.r * bubble.vy) / totalMass;

    // Apply the updated velocities.
    bubble.vx = newVx1;
    bubble.vy = newVy1;

    otherBubble.vx = newVx2;
    otherBubble.vy = newVy2;

    // Calculate how much the circles overlap.
    // Splitting the overlap in half moves each bubble an equal amount.
    const overlap = (radius - distance) * 0.5;

    // Push both bubbles away from each other along the collision normal
    // until they no longer overlap.
    bubble.x += nx * overlap;
    bubble.y += ny * overlap;

    otherBubble.x -= nx * overlap;
    otherBubble.y -= ny * overlap;
  }
};

// HOLE MODE -----------------------------------------------------------------------------------------------------------------------------

const drawHole = (ctx: CanvasRenderingContext2D) => {
  if (!canvas.value || mouseX === null || mouseY === null) return;

  const r = canvas.value.width / 500,
    spacing = r * 2;

  const countX = Math.floor(canvas.value.width / spacing),
    countY = Math.floor(canvas.value.height / spacing),
    numBubbles = countX * countY;

  const holeRadius = r * 7.5,
    holeRadiusSq = holeRadius * holeRadius;

  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);

  ctx.beginPath();
  ctx.fillStyle = 'rgba(0, 100, 134, 0.75)';

  for (let i = 0; i < numBubbles; i++) {
    const x = (i % countX) * spacing + r,
      y = Math.floor(i / countX) * spacing + r,
      dx = x - mouseX,
      dy = y - mouseY;

    // Standard circle equation: (x - h)^2 + (y - k)^2 < r^2
    if (dx * dx + dy * dy < holeRadiusSq) continue;

    // Prevent arcs from being connected
    ctx.moveTo(x + r, y);
    ctx.arc(x, y, r, 0, Math.PI * 2);
  }

  ctx.fill();
};

// BUBBLE HANDLING -----------------------------------------------------------------------------------------------------------------------------

const createBubble = (x: number, y: number): Bubble => {
  const bubbleAngle = ((angle + random(-SPREAD, SPREAD)) * Math.PI) / 180,
    velocity = random(0.25, SPEED),
    c = randomColor();

  return {
    x,
    y,
    r: random(0, 25),
    vx: Math.cos(bubbleAngle) * velocity,
    vy: Math.sin(bubbleAngle) * velocity,
    color: c,
    baseColor: c,
  };
};

const updateBubbles = () => {
  for (const bubble of bubbles) {
    bubble.x += mode.value === 'pulsing' && pulsing ? bubble.vx * -1 : bubble.vx;
    bubble.y -= mode.value === 'pulsing' && pulsing ? bubble.vy * -1 : bubble.vy;
    bubble.r *= 0.995;
    bubble.color = bubble.baseColor;
  }
};

const drawBubbles = (ctx: CanvasRenderingContext2D) => {
  if (!canvas.value) return;

  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);

  for (const bubble of bubbles) {
    ctx.beginPath();
    ctx.strokeStyle = bubble.color;
    ctx.arc(bubble.x, bubble.y, bubble.r, 0, Math.PI * 2);
    ctx.stroke();
  }
};

// AUDIO MODE -----------------------------------------------------------------------------------------------------------------------------

const animateAudioContext = (ctx: CanvasRenderingContext2D) => {
  if (!canvas.value || audioRef.value?.dataset?.playing === 'false') return;
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height);

  const bufferLength = analyser.frequencyBinCount, // Get the number of data points from the analyser / half the value of fftSize (2048 / 2 = 1024)
    dataArray = new Uint8Array(bufferLength); // Create a new array to hold the time domain data
  analyser.getByteTimeDomainData(dataArray); // Populate: Copies the current waveform, or time-domain, data into a Uint8Array (unsigned byte array) passed into it.

  ctx.fillStyle = 'rgb(0, 0, 0)';
  ctx.fillRect(0, 0, canvas.value.width, canvas.value.height);

  ctx.lineWidth = Math.floor(Math.random() * (10 - 2) + 2);
  ctx.strokeStyle = '#00ff00';

  ctx.beginPath();

  const centerX = canvas.value.width / 2,
    centerY = canvas.value.height / 2;

  let firstX = 0,
    firstY = 0;

  for (let i = 0; i < bufferLength; i++) {
    const v = dataArray[i]! / 128.0, // Normalize the data to a range of 0 to 1.99 (dataArray[i] is between 0 and 255) - 128 is the 0 line
      angle = (i / bufferLength) * Math.PI * 2, // Distribute samples evenly around the circle (0 to 2π)
      radius = AUDIO_VISUALIZER_RADIUS * v, // Modulate the radius by the waveform amplitude
      x = centerX + radius * Math.cos(angle), // Polar to Cartesian conversion (radius * (-1 to +1))
      y = centerY + radius * Math.sin(angle); // Polar to Cartesian conversion (radius * (-1 to +1))

    if (i === 0) {
      ctx.moveTo(x, y);
      firstX = x;
      firstY = y;
    } else {
      ctx.lineTo(x, y);
    }
  }

  ctx.lineTo(firstX, firstY); // Close the loop back to the starting point
  ctx.stroke();
};

// RENDER LOOP -----------------------------------------------------------------------------------------------------------------------------

const render = () => {
  requestAnimationFrame(render);

  if (frame++ % 2) return; // Slow down the rendering for performance reasons.
  if (mouseX === null || mouseY === null || !canvas.value || stopped) return;

  const ctx = canvas.value.getContext('2d');
  if (!ctx) return;

  if (mode.value === 'audio') {
    animateAudioContext(ctx);
    return;
  }

  if (mode.value === 'hole') {
    drawHole(ctx);
    return;
  }

  angle = (angle + ANGLE_STEP) % 360;

  bubbles.push(createBubble(mouseX, mouseY));

  if (bubbles.length > MAX_BUBBLES) {
    bubbles.shift();
  }

  updateBubbles();
  if (mode.value === 'collision') {
    updateBubbleGrid();
    for (const bubble of bubbles) {
      detectBubbleCollision(bubble);
    }
  }
  drawBubbles(ctx);
};

onMounted(() => {
  observer = new ResizeObserver(initCanvas);

  if (visualizerView.value) {
    observer.observe(visualizerView.value);
  }

  initCanvas();
  initAudioElements();

  requestAnimationFrame(render);

  interval = setInterval(() => {
    if (counter === 1000) {
      pulsing = true;
    }

    if (counter === 1250) {
      pulsing = false;
      counter = 0;
    }

    counter += 10;
  }, 10);
});

onUnmounted(() => {
  observer?.disconnect();
  if (interval) clearInterval(interval);
});
</script>

<template>
  <h1>Visualizer</h1>

  <fieldset class="visualizer-elements">
    <legend>Aktionen</legend>

    <div class="visualizer-elements-actions">
      <ButtonCustom ar-label-name="Pulsierend" @click="setMode('pulsing')" :active="mode === 'pulsing'">Pulsierend</ButtonCustom>
      <ButtonCustom ar-label-name="Linear" @click="setMode('linear')" :active="mode === 'linear'">Linear</ButtonCustom>
      <ButtonCustom ar-label-name="Kollision" @click="setMode('collision')" :active="mode === 'collision'">
        Kollisionsvermeidung
      </ButtonCustom>
      <ButtonCustom ar-label-name="Loch" @click="setMode('hole')" :active="mode === 'hole'">Loch-Blick</ButtonCustom>
      <ButtonCustom
        ar-label-name="Audi-Visualizer"
        @click="
          setMode('audio');
          playOrPause();
        "
        :active="mode === 'audio'"
      >
        Audi-Visualizer
      </ButtonCustom>
    </div>
  </fieldset>

  <audio class="audio-element" ref="audioRef" :src="song"></audio>

  <div ref="visualizerView" class="visualizer-view">
    <canvas ref="canvas" @mousemove="updateMousePosition($event)" @mouseleave="stopSpawn"></canvas>
  </div>
</template>

<style scoped>
.visualizer-elements-actions {
  display: flex;
  flex-direction: row;
  gap: var(--spacing-component);
}

@media (max-width: 768px) {
  .visualizer-elements-actions {
    flex-direction: column;
  }
}

.audio-element {
  display: none;
  width: 0;
}

.visualizer-view {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: start;
  box-sizing: border-box;
  display: flex;
  border: var(--border-width-standard) solid var(--color-border-accent-1);
  margin-top: var(--spacing-section);

  canvas {
    flex: 1;
    min-height: 0;
    width: 100%;
    border: 2px solid var(--color-border-accent-1);
  }
}
</style>
