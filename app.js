const influencers = Array.isArray(window.INFLUENCERS) ? window.INFLUENCERS : [];
const pageSize = 48;

let activeIndex = 0;
let visibleCount = pageSize;
let filtered = [];
let rotationTimer = null;

const els = {
  totalCount: document.querySelector("#totalCount"),
  photoCount: document.querySelector("#photoCount"),
  socialCount: document.querySelector("#socialCount"),
  featureMedia: document.querySelector("#featureMedia"),
  featureCategory: document.querySelector("#featureCategory"),
  featureName: document.querySelector("#featureName"),
  featureHandle: document.querySelector("#featureHandle"),
  featureFollowers: document.querySelector("#featureFollowers"),
  featureViews: document.querySelector("#featureViews"),
  featureLinks: document.querySelector("#featureLinks"),
  photoStrip: document.querySelector("#photoStrip"),
  searchInput: document.querySelector("#searchInput"),
  categorySelect: document.querySelector("#categorySelect"),
  sortSelect: document.querySelector("#sortSelect"),
  resultCount: document.querySelector("#resultCount"),
  creatorGrid: document.querySelector("#creatorGrid"),
  loadMore: document.querySelector("#loadMore"),
};

const photoInfluencers = influencers.filter((item) => item.avatarLocal);

function numberValue(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function formatCompact(value) {
  const numeric = numberValue(value);
  return new Intl.NumberFormat("en", {
    notation: "compact",
    maximumFractionDigits: numeric >= 1000000 ? 1 : 0,
  }).format(numeric);
}

function initials(name) {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function creatorImage(item, className = "avatar-img") {
  if (!item.avatarLocal) {
    return `<div class="avatar-fallback">${initials(item.name)}</div>`;
  }
  return `<img class="${className}" src="${item.avatarLocal}" alt="${item.name}" loading="lazy" />`;
}

function socialLabel(platform) {
  const labels = {
    TikTok: "TikTok",
    Instagram: "Instagram",
    Youtube: "YouTube",
  };
  return labels[platform] || platform;
}

function socialLinks(item, limit = 4) {
  return item.socials
    .filter((social) => social.platform !== "Email" && !social.url.toLowerCase().startsWith("mailto:"))
    .slice(0, limit)
    .map(
      (social) =>
        `<a href="${social.url}" target="_blank" rel="noreferrer">${socialLabel(social.platform)}</a>`,
    )
    .join("");
}

function sortValue(item, key) {
  return numberValue(item.metrics?.[key]);
}

function setFeature(index) {
  if (!photoInfluencers.length) return;
  activeIndex = (index + photoInfluencers.length) % photoInfluencers.length;
  const item = photoInfluencers[activeIndex];
  els.featureMedia.classList.remove("is-fallback");
  els.featureMedia.textContent = "";
  els.featureMedia.style.backgroundImage = `url("${item.avatarLocal}")`;
  els.featureCategory.textContent = item.category;
  els.featureName.textContent = item.name;
  els.featureHandle.textContent = item.handle;
  els.featureHandle.href = item.socials[0]?.url || "#";
  els.featureFollowers.textContent = `${formatCompact(item.metrics.followers)} followers`;
  els.featureViews.textContent = `${formatCompact(item.metrics.views30d)} views / 30d`;
  els.featureLinks.innerHTML = socialLinks(item, 5);

  els.photoStrip.querySelectorAll(".photo-tile").forEach((tile) => {
    tile.classList.toggle("active", Number(tile.dataset.index) === activeIndex);
  });
}

function renderPhotoStrip() {
  const tiles = photoInfluencers.slice(0, 12);
  els.photoStrip.innerHTML = tiles
    .map(
      (item, index) => `
        <button class="photo-tile" type="button" data-index="${index}" aria-label="${item.name}">
          <img src="${item.avatarLocal}" alt="${item.name}" loading="lazy" />
          <span>${item.name}</span>
        </button>
      `,
    )
    .join("");

  els.photoStrip.querySelectorAll(".photo-tile").forEach((tile) => {
    tile.addEventListener("click", () => {
      setFeature(Number(tile.dataset.index));
      startRotation();
    });
  });
}

function populateCategories() {
  const categories = [...new Set(influencers.map((item) => item.category).filter(Boolean))].sort((a, b) =>
    a.localeCompare(b),
  );
  els.categorySelect.innerHTML = [
    '<option value="all">All categories</option>',
    ...categories.map((category) => `<option value="${category}">${category}</option>`),
  ].join("");
}

function applyFilters() {
  const query = els.searchInput.value.trim().toLowerCase();
  const category = els.categorySelect.value;
  const sortKey = els.sortSelect.value;

  filtered = influencers
    .filter((item) => {
      const inCategory = category === "all" || item.category === category;
      if (!query) return inCategory;
      const haystack = [
        item.name,
        item.handle,
        item.category,
        item.region,
        item.socials.map((social) => social.url).join(" "),
      ]
        .join(" ")
        .toLowerCase();
      return inCategory && haystack.includes(query);
    })
    .sort((a, b) => sortValue(b, sortKey) - sortValue(a, sortKey));

  visibleCount = pageSize;
  renderGrid();
}

function renderGrid() {
  const visible = filtered.slice(0, visibleCount);
  els.resultCount.textContent = filtered.length.toLocaleString("en");
  els.creatorGrid.innerHTML = visible
    .map(
      (item) => `
        <article class="creator-card">
          <div class="avatar-frame">${creatorImage(item)}</div>
          <div class="card-body">
            <div class="meta-row">
              <span>${item.region || "Global"}</span>
              <span>${item.category}</span>
            </div>
            <div>
              <h3>${item.name}</h3>
              <a class="handle" href="${item.socials[0]?.url || "#"}" target="_blank" rel="noreferrer">
                ${item.handle}
              </a>
            </div>
            <div class="metric-row">
              <span>${formatCompact(item.metrics.followers)} followers</span>
              <span>${formatCompact(item.metrics.views30d)} views</span>
              <span>${numberValue(item.metrics.engagementRate).toFixed(1)}% ER</span>
            </div>
            <div class="card-links">${socialLinks(item)}</div>
          </div>
        </article>
      `,
    )
    .join("");
  els.loadMore.hidden = visibleCount >= filtered.length;
}

function startRotation() {
  if (rotationTimer) window.clearInterval(rotationTimer);
  rotationTimer = window.setInterval(() => setFeature(activeIndex + 1), 4200);
}

function init() {
  const socialCount = influencers.reduce((sum, item) => sum + item.socials.length, 0);
  els.totalCount.textContent = influencers.length.toLocaleString("en");
  els.photoCount.textContent = photoInfluencers.length.toLocaleString("en");
  els.socialCount.textContent = socialCount.toLocaleString("en");

  populateCategories();
  renderPhotoStrip();
  setFeature(0);
  startRotation();
  applyFilters();

  els.searchInput.addEventListener("input", applyFilters);
  els.categorySelect.addEventListener("change", applyFilters);
  els.sortSelect.addEventListener("change", applyFilters);
  els.loadMore.addEventListener("click", () => {
    visibleCount += pageSize;
    renderGrid();
  });
}

init();
