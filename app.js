'use strict';

/* ── State ─────────────────────────────────────────────────────── */

const state = {
  channelId: null,   // null = all channels
  filter: 'all',     // 'all' | 'unwatched' | 'watched'
  data: null,        // parsed videos.json
};

/* ── Watched (localStorage) ─────────────────────────────────────── */

const WATCHED_KEY = 'yt_watched';

function getWatched() {
  try { return JSON.parse(localStorage.getItem(WATCHED_KEY) || '{}'); }
  catch { return {}; }
}

function saveWatched(map) {
  localStorage.setItem(WATCHED_KEY, JSON.stringify(map));
}

function toggleWatched(videoId, event) {
  event.stopPropagation();
  const map = getWatched();
  if (map[videoId]) delete map[videoId];
  else map[videoId] = Date.now();
  saveWatched(map);
  render();
}

function openVideo(url, videoId) {
  const map = getWatched();
  map[videoId] = Date.now();
  saveWatched(map);
  window.open(url, '_blank', 'noopener,noreferrer');
  render();
}

/* ── Navigation ─────────────────────────────────────────────────── */

function goTo(channelId) {
  state.channelId = channelId;
  const hash = channelId ? '#' + channelId : '';
  history.pushState(null, '', location.pathname + hash);
  render();
}

window.addEventListener('popstate', () => {
  state.channelId = location.hash.replace(/^#/, '') || null;
  render();
});

/* ── Filters ─────────────────────────────────────────────────────── */

function setFilter(f) {
  state.filter = f;
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.classList.toggle('active', btn.textContent.toLowerCase() === f);
  });
  renderMain();
}

/* ── Helpers ─────────────────────────────────────────────────────── */

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function timeAgo(iso) {
  const secs = Math.floor((Date.now() - new Date(iso)) / 1000);
  const steps = [
    [31536000, 'year'],
    [2592000,  'month'],
    [86400,    'day'],
    [3600,     'hour'],
    [60,       'minute'],
  ];
  for (const [n, label] of steps) {
    const v = Math.floor(secs / n);
    if (v >= 1) return `${v}\u00a0${label}${v > 1 ? 's' : ''} ago`;
  }
  return 'just now';
}

function applyFilter(videos) {
  const watched = getWatched();
  if (state.filter === 'watched')   return videos.filter(v => !!watched[v.id]);
  if (state.filter === 'unwatched') return videos.filter(v => !watched[v.id]);
  return videos;
}

/* ── Render ─────────────────────────────────────────────────────── */

function renderSidebar() {
  const { data, channelId } = state;
  const watched = getWatched();

  const totalUnwatched = data.channels.reduce(
    (sum, ch) => sum + ch.videos.filter(v => !watched[v.id]).length, 0
  );

  let html = `
    <div class="ch-item all-item ${!channelId ? 'active' : ''}" onclick="goTo(null)">
      <span class="ch-initial">&#8801;</span>
      <span class="ch-label">All Channels</span>
      ${totalUnwatched > 0 ? `<span class="badge">${totalUnwatched}</span>` : ''}
    </div>
  `;

  for (const ch of data.channels) {
    const unwatched = ch.videos.filter(v => !watched[v.id]).length;
    const active = channelId === ch.id ? 'active' : '';
    const avatar = ch.thumbnail
      ? `<img class="ch-avatar" src="${esc(ch.thumbnail)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ch-initial',textContent:'${esc(ch.name[0] || '?')}'}))">`
      : `<span class="ch-initial">${esc(ch.name[0] || '?')}</span>`;

    html += `
      <div class="ch-item ${active}" onclick="goTo('${esc(ch.id)}')">
        ${avatar}
        <span class="ch-label">${esc(ch.name)}</span>
        ${unwatched > 0 ? `<span class="badge">${unwatched}</span>` : ''}
      </div>
    `;
  }

  document.getElementById('channel-list').innerHTML = html;
}

function renderCard(video, showChannel, channelName) {
  const watched = getWatched();
  const isWatched = !!watched[video.id];
  const id  = esc(video.id);
  const url = esc(video.url);

  return `
    <div class="card ${isWatched ? 'watched' : ''}" onclick="openVideo('${url}','${id}')">
      <div class="thumb-wrap">
        <img src="${esc(video.thumbnail)}" alt="" loading="lazy"
          onerror="this.style.visibility='hidden'">
        ${isWatched ? '<span class="watched-badge">&#10003; watched</span>' : ''}
      </div>
      <div class="card-body">
        <p class="card-title">${esc(video.title)}</p>
        <div class="card-meta">
          ${showChannel ? `<span class="ch-name">${esc(channelName)}</span> &middot; ` : ''}
          <span>${timeAgo(video.published_at)}</span>
        </div>
      </div>
      <button class="toggle-btn ${isWatched ? 'marked' : ''}"
        onclick="toggleWatched('${id}',event)"
        title="${isWatched ? 'Mark unwatched' : 'Mark watched'}">&#10003;</button>
    </div>
  `;
}

function renderMain() {
  const { data, channelId } = state;
  const main = document.getElementById('main');

  if (channelId) {
    const ch = data.channels.find(c => c.id === channelId);
    if (!ch) {
      main.innerHTML = '<div class="status-msg error">Channel not found.</div>';
      return;
    }
    const videos = applyFilter(ch.videos);
    main.innerHTML = `
      <h2 class="channel-heading">${esc(ch.name)}</h2>
      ${videos.length
        ? `<div class="video-grid">${videos.map(v => renderCard(v, false, ch.name)).join('')}</div>`
        : `<div class="status-msg">No ${state.filter === 'all' ? '' : state.filter + ' '}videos.</div>`}
    `;
  } else {
    // All channels: merge and sort by date descending
    const allVideos = data.channels
      .flatMap(ch => ch.videos.map(v => ({ ...v, _ch: ch.name })))
      .sort((a, b) => new Date(b.published_at) - new Date(a.published_at));

    const videos = applyFilter(allVideos);
    main.innerHTML = videos.length
      ? `<div class="video-grid">${videos.map(v => renderCard(v, true, v._ch)).join('')}</div>`
      : `<div class="status-msg">No ${state.filter === 'all' ? '' : state.filter + ' '}videos.</div>`;
  }
}

function render() {
  if (!state.data) return;
  renderSidebar();
  renderMain();
}

/* ── Init ─────────────────────────────────────────────────────── */

async function init() {
  // Parse initial URL
  state.channelId = location.hash.replace(/^#/, '') || null;

  try {
    const res = await fetch('data/videos.json');
    if (!res.ok) throw new Error('HTTP ' + res.status);
    state.data = await res.json();
  } catch (e) {
    document.getElementById('main').innerHTML =
      '<div class="status-msg error">Could not load video data.<br>Trigger the GitHub Action manually to fetch videos.</div>';
    return;
  }

  if (state.data.last_updated) {
    document.getElementById('last-updated').textContent =
      'Updated ' + timeAgo(state.data.last_updated);
  }

  render();
}

init();
