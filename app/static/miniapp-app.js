import { computed, createApp, reactive } from "https://unpkg.com/vue@3/dist/vue.esm-browser.prod.js";

const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
}

const state = reactive({
  token: null,
  me: null,
  products: [],
  statusMessage: "",
  statusKind: "",
  isLoginPending: false,
  isScanPending: false,
  isRedeemPending: false,
  qrTokenInput: "",
});

function setStatus(message, kind = "") {
  state.statusMessage = message;
  state.statusKind = kind;
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(state.token ? { Authorization: `Bearer ${state.token}` } : {}),
      ...(options.headers || {}),
    },
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

async function loadProducts() {
  state.products = await api("/api/shop/products", { method: "GET" });
}

async function loadMe() {
  state.me = await api("/api/me", { method: "GET" });
}

async function hydrateDashboard() {
  await Promise.all([loadMe(), loadProducts()]);
}

async function login() {
  if (!tg?.initData) {
    setStatus("Эта страница должна быть открыта из Telegram Mini App.", "error");
    return;
  }

  state.isLoginPending = true;
  setStatus("Выполняю авторизацию через Telegram...", "");
  try {
    const data = await api("/api/auth/telegram", {
      method: "POST",
      body: JSON.stringify({ init_data: tg.initData }),
    });
    state.token = data.access_token;
    await hydrateDashboard();
    setStatus("Авторизация прошла успешно.", "ok");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    state.isLoginPending = false;
  }
}

async function scanByToken(token) {
  const cleanToken = token.trim();
  if (!cleanToken) {
    setStatus("Вставь QR token.", "error");
    return false;
  }

  state.isScanPending = true;
  setStatus("Начисляю баллы...", "");
  try {
    const data = await api("/api/scan", {
      method: "POST",
      body: JSON.stringify({ token: cleanToken }),
    });
    state.qrTokenInput = "";
    await hydrateDashboard();
    setStatus(`${data.message}: +${data.awarded_points}`, "ok");
    return true;
  } catch (error) {
    setStatus(error.message, "error");
    return false;
  } finally {
    state.isScanPending = false;
  }
}

async function startCameraScan() {
  if (!state.token) {
    setStatus("Сначала авторизуйся.", "error");
    return;
  }
  if (typeof tg?.showScanQrPopup !== "function") {
    setStatus("QR-сканер не поддерживается в этом клиенте Telegram.", "error");
    return;
  }

  setStatus("Открыл камеру для сканирования QR...", "");
  tg.showScanQrPopup({ text: "Наведите камеру на QR-код точки" }, async (scannedText) => {
    if (!scannedText) {
      return false;
    }

    const ok = await scanByToken(scannedText);
    if (ok && typeof tg.closeScanQrPopup === "function") {
      tg.closeScanQrPopup();
    }
    return ok;
  });
}

async function redeemProduct(productId) {
  if (!state.token) {
    setStatus("Сначала авторизуйся.", "error");
    return;
  }
  state.isRedeemPending = true;
  setStatus("Обмениваю баллы на товар...", "");
  try {
    const data = await api(`/api/shop/redeem/${productId}`, { method: "POST" });
    await hydrateDashboard();
    setStatus(data.message, "ok");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    state.isRedeemPending = false;
  }
}

createApp({
  setup() {
    const telegramUser = computed(() => tg?.initDataUnsafe?.user || null);
    const profileName = computed(() => {
      const user = telegramUser.value || {};
      return [user.first_name, user.last_name].filter(Boolean).join(" ") || user.username || "Telegram user";
    });
    const authMeta = computed(() => {
      if (telegramUser.value) {
        return "Открой разделы ниже, чтобы сканировать точки и обменивать баллы на товары.";
      }
      return "Открой эту страницу из Telegram через кнопку бота и авторизуйся, чтобы начать.";
    });
    const isAuthorized = computed(() => Boolean(state.token && state.me));

    return {
      state,
      telegramUser,
      profileName,
      authMeta,
      isAuthorized,
      login,
      scanByToken,
      startCameraScan,
      redeemProduct,
    };
  },
  template: `
    <main class="app-shell">
      <section class="hero fade-up">
        <div class="eyebrow">Программа участника</div>
        <h1>HSE Business Club</h1>
        <p>
          Cканируйте QR на событиях и покупайте мерч за баллы
        </p>
        <div :class="['status', state.statusKind]">{{ state.statusMessage }}</div>
      </section>

      <div class="layout">
        <section v-if="!isAuthorized" class="card fade-up">
          <div class="grid two">
            <div>
              <h2>Вход через Telegram</h2>
              <p class="card-subtitle">{{ authMeta }}</p>
            </div>
            <div class="hero-actions" style="align-self:end; justify-content:flex-end;">
              <button class="button-primary" @click="login" :disabled="state.isLoginPending">
                <span v-if="state.isLoginPending" class="spinner"></span>
                <template v-else>Войти через Telegram</template>
              </button>
            </div>
          </div>
        </section>

        <section v-if="isAuthorized" class="card fade-up">
          <div class="profile-band">
            <div>
              <div class="eyebrow">Профиль участника</div>
              <div class="profile-name">{{ profileName }}</div>
              <p class="card-subtitle">Баланс считается как начисления за посещения минус обмены на товары.</p>
              <div class="meta-list">
                <span class="pill">Начислений: {{ state.me.history.length }}</span>
                <span class="pill">Покупок: {{ state.me.purchases.length }}</span>
              </div>
            </div>
            <div class="balance-tile">
              <div style="opacity:0.8;">Текущий баланс</div>
              <div class="balance-value">{{ state.me.balance }}</div>
              <div>баллов доступно для обмена</div>
            </div>
          </div>
        </section>

        <section v-if="isAuthorized" class="card fade-up">
          <h2>Сканирование точки</h2>
          <p class="card-subtitle">
            Сканируй QR через Telegram-камеру или вставь токен вручную.
          </p>
          <div class="scan-grid">
            <input v-model="state.qrTokenInput" placeholder="QR token" />
            <div class="stack-actions">
              <button class="button-secondary" @click="startCameraScan" :disabled="state.isScanPending">
                Сканировать камерой
              </button>
              <button class="button-primary" @click="scanByToken(state.qrTokenInput)" :disabled="state.isScanPending">
                <span v-if="state.isScanPending" class="spinner"></span>
                <template v-else>Начислить баллы</template>
              </button>
            </div>
          </div>
        </section>

        <section v-if="isAuthorized" class="card fade-up">
          <h2>Магазин призов</h2>
          <p class="card-subtitle">Товары подтягиваются из backend в реальном времени.</p>
          <div v-if="state.products.length" class="products-grid">
            <article v-for="product in state.products" :key="product.id" class="product-card">
              <div class="product-head">
                <div class="product-copy">
                  <div class="item-title">{{ product.name }}</div>
                  <div class="item-meta">{{ product.description || 'Без описания' }}</div>
                </div>
                <span class="pill">{{ product.price_points }} баллов</span>
              </div>
              <div class="list-top">
                <span class="item-meta">{{ product.stock > 0 ? 'В наличии' : 'Временно недоступно' }}</span>
                <button
                  class="button-primary"
                  @click="redeemProduct(product.id)"
                  :disabled="product.stock <= 0 || state.isRedeemPending"
                >
                  Забрать
                </button>
              </div>
            </article>
          </div>
          <div v-else class="empty">Товаров пока нет.</div>
        </section>

        <div v-if="isAuthorized" class="grid two fade-up">
          <section class="card">
            <h2>История начислений</h2>
            <div v-if="state.me.history.length" class="list">
              <article v-for="item in state.me.history" :key="item.visited_at + '-' + item.point_id" class="list-item">
                <div class="list-top">
                  <div>
                    <div class="item-title">{{ item.point_name }}</div>
                    <div class="item-meta">{{ new Date(item.visited_at).toLocaleString() }}</div>
                  </div>
                  <span class="pill">+{{ item.points_awarded }}</span>
                </div>
              </article>
            </div>
            <div v-else class="empty">Начислений пока нет.</div>
          </section>

          <section class="card">
            <h2>Купленные товары</h2>
            <div v-if="state.me.purchases.length" class="list">
              <article v-for="item in state.me.purchases" :key="item.purchased_at + '-' + item.product_id" class="list-item">
                <div class="list-top">
                  <div>
                    <div class="item-title">{{ item.product_name }}</div>
                    <div class="item-meta">{{ new Date(item.purchased_at).toLocaleString() }}</div>
                  </div>
                  <span class="pill">-{{ item.points_spent }}</span>
                </div>
              </article>
            </div>
            <div v-else class="empty">Покупок пока нет.</div>
          </section>
        </div>
      </div>
    </main>
  `,
}).mount("#app");
