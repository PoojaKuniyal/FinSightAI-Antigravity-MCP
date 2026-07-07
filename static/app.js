/**
 * app.js – FinSight AI Frontend Logic
 *
 * Handles:
 *  - Chat message submission & rendering
 *  - Typing indicator with animated agent pipeline steps
 *  - Sidebar toggle & quick query buttons
 *  - Redis status & /api/status polling
 *  - Toast notifications
 *  - Markdown-ish rendering (bold, italic, headers, lists, code, hr)
 *  - Auto-resize textarea
 *  - Session history restore on load
 */

'use strict';

// ── DOM refs ────────────────────────────────────────────────────────────────
const form = document.getElementById('chat-form');
const input = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const charCount = document.getElementById('char-count');
const messages = document.getElementById('messages-container');
const typingEl = document.getElementById('typing-indicator');
const sidebarEl = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebar-toggle');
const clearBtn = document.getElementById('clear-btn');
const redisDot = document.getElementById('redis-dot');
const redisLabel = document.getElementById('redis-label');
const toastContainer = document.getElementById('toast-container');
const quickBtns = document.querySelectorAll('.quick-btn');

// Typing pipeline steps
const stepGuardrail = document.getElementById('step-guardrail');
const stepRouter = document.getElementById('step-router');
const stepAgent = document.getElementById('step-agent');
const stepSummary = document.getElementById('step-summary');

// Agent badges
const badgeGuardrail = document.getElementById('badge-guardrail');
const badgeRouter = document.getElementById('badge-router');
const badgeFaq = document.getElementById('badge-faq');
const badgeAnalysis = document.getElementById('badge-analysis');
const badgeSummary = document.getElementById('badge-summary');

// ── State ────────────────────────────────────────────────────────────────────
let isProcessing = false;
let typingInterval = null;

// ── Markdown-ish renderer ────────────────────────────────────────────────────
/**
 * Very lightweight markdown → HTML converter (no external deps).
 * Handles: headers, bold, italic, inline code, horizontal rule,
 *          unordered/ordered lists, paragraphs.
 */
function renderMarkdown(text) {
  if (!text) return '';

  const lines = text.split('\n');
  const html = [];
  let inList = false;
  let listType = '';

  const escape = s => s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');

  const inline = s => {
    // inline code
    s = s.replace(/`([^`]+)`/g, '<code>$1</code>');
    // bold
    s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    // italic (but not emoji *)
    s = s.replace(/\*([^*\s][^*]*[^*\s])\*/g, '<em>$1</em>');
    return s;
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    const trimmed = line.trim();

    // Horizontal rule
    if (/^---+$/.test(trimmed)) {
      if (inList) { html.push(`</${listType}>`); inList = false; }
      html.push('<hr>');
      continue;
    }

    // Headers
    const h3 = trimmed.match(/^###\s+(.+)/);
    const h2 = trimmed.match(/^##\s+(.+)/);
    const h1m = trimmed.match(/^#\s+(.+)/);
    if (h3) { if (inList) { html.push(`</${listType}>`); inList = false; } html.push(`<h3>${inline(escape(h3[1]))}</h3>`); continue; }
    if (h2) { if (inList) { html.push(`</${listType}>`); inList = false; } html.push(`<h2>${inline(escape(h2[1]))}</h2>`); continue; }
    if (h1m) { if (inList) { html.push(`</${listType}>`); inList = false; } html.push(`<h2>${inline(escape(h1m[1]))}</h2>`); continue; }

    // Unordered list
    const ul = trimmed.match(/^[-*•]\s+(.+)/);
    if (ul) {
      if (!inList || listType !== 'ul') {
        if (inList) html.push(`</${listType}>`);
        html.push('<ul>'); inList = true; listType = 'ul';
      }
      html.push(`<li>${inline(escape(ul[1]))}</li>`);
      continue;
    }

    // Ordered list
    const ol = trimmed.match(/^\d+\.\s+(.+)/);
    if (ol) {
      if (!inList || listType !== 'ol') {
        if (inList) html.push(`</${listType}>`);
        html.push('<ol>'); inList = true; listType = 'ol';
      }
      html.push(`<li>${inline(escape(ol[1]))}</li>`);
      continue;
    }

    // Close list if not a list item
    if (inList && trimmed !== '') { html.push(`</${listType}>`); inList = false; }

    // Empty line → paragraph break (we skip it; paragraphs come from non-empty lines)
    if (trimmed === '') { html.push('<br>'); continue; }

    // Regular paragraph line
    html.push(`<p>${inline(escape(trimmed))}</p>`);
  }

  if (inList) html.push(`</${listType}>`);

  return html.join('\n');
}

// ── Chat UI helpers ──────────────────────────────────────────────────────────

function now() {
  return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

function scrollToBottom() {
  messages.scrollTo({ top: messages.scrollHeight, behavior: 'smooth' });
}

function appendMessage(role, content) {
  const isUser = role === 'user';
  const div = document.createElement('div');
  div.className = `message message-${isUser ? 'user' : 'assistant'}`;

  const avatarSvg = isUser
    ? `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/></svg>`
    : `<svg width="16" height="16" viewBox="0 0 28 28" fill="none"><polyline points="4,20 10,12 15,16 22,7" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="22" cy="7" r="2.5" fill="white"/></svg>`;

  const rendered = isUser
    ? content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    : renderMarkdown(content);

  div.innerHTML = `
    <div class="message-avatar" aria-hidden="true">${avatarSvg}</div>
    <div class="message-content">
      <div class="message-bubble">${rendered}</div>
      <span class="message-time">${now()}</span>
    </div>
  `;

  messages.appendChild(div);
  scrollToBottom();
  return div;
}

// ── Typing indicator with animated pipeline stages ───────────────────────────

const pipelineSteps = [stepGuardrail, stepRouter, stepAgent, stepSummary];

function startTyping() {
  typingEl.hidden = false;
  typingEl.removeAttribute('aria-hidden');
  scrollToBottom();

  let step = 0;
  pipelineSteps.forEach(s => s.classList.remove('active'));
  pipelineSteps[0].classList.add('active');

  typingInterval = setInterval(() => {
    pipelineSteps[step].classList.remove('active');
    step = (step + 1) % pipelineSteps.length;
    pipelineSteps[step].classList.add('active');
  }, 1200);
}

function stopTyping() {
  clearInterval(typingInterval);
  typingInterval = null;
  typingEl.hidden = true;
  typingEl.setAttribute('aria-hidden', 'true');
  pipelineSteps.forEach(s => s.classList.remove('active'));
}

// ── Agent execution path ─────────────────────────────────────────────────────

/**
 * Maps an agent name (as returned by the server) to its CSS class and emoji.
 * The server sends the canonical names defined in _build_execution_path().
 */
const AGENT_META = {
  'Guardrail':        { cls: 'flow-guardrail', emoji: '🛡️' },
  'Router':           { cls: 'flow-router',    emoji: '🧭' },
  'FAQ':              { cls: 'flow-faq',        emoji: '📚' },
  'Company Analysis': { cls: 'flow-analysis',  emoji: '📊' },
  'Summary':          { cls: 'flow-summary',   emoji: '✨' },
  'Blocked':          { cls: 'flow-blocked',   emoji: '🚫' },
};

/**
 * Append an execution-path trail below the last assistant message bubble.
 * @param {string[]} path  e.g. ["Guardrail","Router","FAQ","Summary"]
 * @param {HTMLElement} msgDiv  The message wrapper div returned by appendMessage()
 */
function appendExecutionPath(path, msgDiv) {
  if (!path || path.length === 0) return;

  const trail = document.createElement('div');
  trail.className = 'exec-path-trail';
  trail.setAttribute('aria-label', 'Agent execution path: ' + path.join(' → '));

  path.forEach((name, i) => {
    const meta = AGENT_META[name] || { cls: '', emoji: '⚙️' };

    const node = document.createElement('span');
    node.className = `exec-path-node ${meta.cls}`;
    node.title = name;
    node.textContent = `${meta.emoji} ${name}`;
    trail.appendChild(node);

    if (i < path.length - 1) {
      const sep = document.createElement('span');
      sep.className = 'exec-path-sep';
      sep.setAttribute('aria-hidden', 'true');
      sep.textContent = '→';
      trail.appendChild(sep);
    }
  });

  // Insert trail into the message-content div (after the bubble)
  const contentDiv = msgDiv.querySelector('.message-content');
  if (contentDiv) contentDiv.appendChild(trail);
}

/**
 * Update sidebar agent badges from the authoritative execution_path array.
 * @param {string[]} path
 */
function updateBadges(path) {
  // Reset all badges first
  const allBadges = [badgeGuardrail, badgeRouter, badgeFaq, badgeAnalysis, badgeSummary];
  allBadges.forEach(b => { b.textContent = '—'; b.className = 'agent-badge'; });

  if (!path || path.length === 0) return;

  const pathSet = new Set(path);

  // Guardrail always in the path
  if (pathSet.has('Guardrail')) {
    const isBlocked = pathSet.has('Blocked');
    setBadge(badgeGuardrail, isBlocked ? 'BLOCKED' : 'SAFE', isBlocked ? 'blocked' : 'safe');
  }

  // Router
  if (pathSet.has('Router')) {
    let routeLabel = '✓';
    if (pathSet.has('FAQ')) routeLabel = 'FAQ';
    else if (pathSet.has('Company Analysis')) routeLabel = 'ANALYSIS';
    else if (!pathSet.has('Summary')) routeLabel = 'OFF_TOPIC';
    setBadge(badgeRouter, routeLabel, 'active');
  }

  // Specialist agents
  setBadge(badgeFaq,      pathSet.has('FAQ')              ? '✓' : '—', pathSet.has('FAQ')              ? 'safe' : '');
  setBadge(badgeAnalysis, pathSet.has('Company Analysis') ? '✓' : '—', pathSet.has('Company Analysis') ? 'safe' : '');

  // Summary
  if (pathSet.has('Summary')) setBadge(badgeSummary, '✓', 'safe');
  else if (pathSet.has('Blocked')) setBadge(badgeSummary, '—', '');
}

function setBadge(el, text, cls) {
  el.textContent = text;
  el.className = 'agent-badge' + (cls ? ` ${cls}` : '');
}

// ── Toast ────────────────────────────────────────────────────────────────────

function showToast(msg, type = 'info', duration = 3500) {
  const el = document.createElement('div');
  el.className = `toast toast-${type}`;
  el.textContent = msg;
  toastContainer.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity .4s';
    setTimeout(() => el.remove(), 400);
  }, duration);
}

// ── API calls ────────────────────────────────────────────────────────────────

async function sendMessage(message) {
  if (!message.trim() || isProcessing) return;

  isProcessing = true;
  sendBtn.disabled = true;
  input.disabled = true;

  appendMessage('user', message);
  startTyping();

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.error || `Server error ${res.status}`);
    }

    stopTyping();
    const msgDiv = appendMessage('assistant', data.response);
    if (data.execution_path) {
      appendExecutionPath(data.execution_path, msgDiv);
      updateBadges(data.execution_path);
    }

  } catch (err) {
    stopTyping();
    appendMessage('assistant', `⚠️ **Error:** ${err.message}\n\nPlease try again.`);
    showToast(err.message, 'error');
    console.error('[FinSight] Chat error:', err);
  } finally {
    isProcessing = false;
    sendBtn.disabled = false;
    input.disabled = false;
    input.focus();
  }
}

async function clearConversation() {
  if (isProcessing) return;
  try {
    await fetch('/api/clear', { method: 'POST' });
    // Remove all messages except welcome
    const welcomeMsg = document.getElementById('welcome-msg');
    [...messages.children].forEach(el => {
      if (el !== welcomeMsg) el.remove();
    });
    // Reset badges
    [badgeGuardrail, badgeRouter, badgeFaq, badgeAnalysis, badgeSummary]
      .forEach(b => { b.textContent = '—'; b.className = 'agent-badge'; });
    // Also remove any exec-path trails from cleared messages
    document.querySelectorAll('.exec-path-trail').forEach(el => el.remove());
    showToast('Conversation cleared.', 'success');
  } catch (err) {
    showToast('Failed to clear conversation.', 'error');
  }
}

async function checkStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    const redisOk = data.redis === 'connected';
    redisDot.className = 'redis-dot ' + (redisOk ? 'on' : 'off');
    redisLabel.textContent = redisOk ? 'Redis ●' : 'Memory';
  } catch {
    redisDot.className = 'redis-dot off';
    redisLabel.textContent = 'Offline';
  }
}

async function loadHistory() {
  try {
    const res = await fetch('/api/history');
    const data = await res.json();
    const hist = data.history || [];
    if (hist.length === 0) return;

    for (const turn of hist) {
      appendMessage(turn.role === 'assistant' ? 'assistant' : 'user', turn.content);
    }
    scrollToBottom();
  } catch {
    // Silently ignore; history is a nice-to-have
  }
}

// ── Input helpers ────────────────────────────────────────────────────────────

function autoResize() {
  input.style.height = 'auto';
  input.style.height = Math.min(input.scrollHeight, 160) + 'px';
}

function updateCharCount() {
  const len = input.value.length;
  charCount.textContent = `${len}/2000`;
  sendBtn.disabled = isProcessing || len === 0;
}

// ── Event listeners ──────────────────────────────────────────────────────────

form.addEventListener('submit', e => {
  e.preventDefault();
  const msg = input.value.trim();
  if (!msg) return;
  input.value = '';
  autoResize();
  updateCharCount();
  sendMessage(msg);
});

input.addEventListener('input', () => {
  autoResize();
  updateCharCount();
});

input.addEventListener('keydown', e => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    form.dispatchEvent(new Event('submit'));
  }
});

sidebarToggle.addEventListener('click', () => {
  // Mobile: toggle open class; Desktop: toggle collapsed
  if (window.innerWidth <= 768) {
    sidebarEl.classList.toggle('open');
  } else {
    sidebarEl.classList.toggle('collapsed');
  }
});

clearBtn.addEventListener('click', () => clearConversation());

quickBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const query = btn.dataset.query;
    if (query && !isProcessing) {
      input.value = query;
      updateCharCount();
      autoResize();
      // On mobile, close sidebar first
      if (window.innerWidth <= 768) sidebarEl.classList.remove('open');
      form.dispatchEvent(new Event('submit'));
    }
  });
});

// ── Init ─────────────────────────────────────────────────────────────────────

(async () => {
  await checkStatus();
  setInterval(checkStatus, 30_000); // refresh status every 30 s
  await loadHistory();
  input.focus();
})();
