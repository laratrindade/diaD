const photo = document.getElementById("photo");
const video = document.getElementById("video");
const hint = document.getElementById("hint");
const frame = document.getElementById("frame");
const playBtn = document.getElementById("play");
const pauseBtn = document.getElementById("pause");
const nextBtn = document.getElementById("next");

let items = [];
let currentIndex = -1;
let timer = null;
let isPlaying = false;

const IMAGE_DURATION_MS = 6000;

function showHint(text) {
  hint.textContent = text;
}

async function loadList() {
  const res = await fetch("/media_list");
  const data = await res.json();
  items = data.items || [];
  if (!items.length) {
    showHint("Sem media encontrado. Confirma a pasta configurada.");
  } else {
    showHint("Pronto para reproduzir.");
  }
}

function clearStage() {
  photo.classList.remove("show");
  video.classList.remove("show");
  video.pause();
  video.removeAttribute("src");
  video.load();
}

function pickNext() {
  if (!items.length) return null;
  let idx = Math.floor(Math.random() * items.length);
  if (items.length > 1 && idx === currentIndex) {
    idx = (idx + 1) % items.length;
  }
  currentIndex = idx;
  return items[idx];
}

function scheduleNext(delay) {
  if (timer) window.clearTimeout(timer);
  timer = window.setTimeout(() => {
    if (isPlaying) playNext();
  }, delay);
}

function playImage(url) {
  clearStage();
  frame.classList.add("playing");
  photo.src = url;
  photo.onload = () => photo.classList.add("show");
  scheduleNext(IMAGE_DURATION_MS);
}

function playVideo(url) {
  clearStage();
  frame.classList.add("playing");
  video.src = url;
  video.classList.add("show");
  video.play().catch(() => {
    showHint("Clique em Reproduzir para iniciar o vídeo.");
  });
}

function playNext() {
  const item = pickNext();
  if (!item) return;
  if (item.type === "video") {
    playVideo(item.url);
  } else {
    playImage(item.url);
  }
}

playBtn.addEventListener("click", () => {
  if (!items.length) return;
  isPlaying = true;
  frame.classList.add("playing");
  showHint("");
  if (currentIndex === -1) {
    playNext();
  } else if (video.classList.contains("show")) {
    video.play();
  } else {
    scheduleNext(IMAGE_DURATION_MS);
  }
});

pauseBtn.addEventListener("click", () => {
  isPlaying = false;
  frame.classList.remove("playing");
  if (timer) window.clearTimeout(timer);
  video.pause();
});

nextBtn.addEventListener("click", () => {
  isPlaying = true;
  frame.classList.add("playing");
  playNext();
});

video.addEventListener("ended", () => {
  if (isPlaying) playNext();
});

loadList();
