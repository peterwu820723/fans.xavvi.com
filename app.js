const influencers = Array.isArray(window.INFLUENCERS) ? window.INFLUENCERS : [];
const pageSize = 48;
const languageKey = "xavviInfluencerLanguage";

let activeIndex = 0;
let visibleCount = pageSize;
let filtered = [];
let rotationTimer = null;
let language = localStorage.getItem(languageKey) === "en" ? "en" : "zh";

const copy = {
  zh: {
    documentTitle: "Xavvi ????????",
    eyebrow: "??????",
    total: "??",
    photos: "??",
    socialLinks: "????",
    search: "??",
    searchPlaceholder: "????????",
    category: "??",
    sort: "??",
    allCategories: "????",
    matched: "?????",
    loadMore: "????",
    followers: "??",
    views: "??",
    views30d: "30???",
    global: "??",
    er: "???",
    sorts: {
      followers: "???",
      views30d: "30???",
      likes30d: "30???",
      engagementRate: "???",
      gmv: "GMV",
    },
  },
  en: {
    documentTitle: "Xavvi U.S. Beauty Influencer List",
    eyebrow: "Beauty Creator Directory",
    total: "Creators",
    photos: "Photos",
    socialLinks: "Social Links",
    search: "Search",
    searchPlaceholder: "Name, handle, category",
    category: "Category",
    sort: "Sort",
    allCategories: "All categories",
    matched: "matched influencers",
    loadMore: "Load more",
    followers: "followers",
    views: "views",
    views30d: "views / 30d",
    global: "Global",
    er: "ER",
    sorts: {
      followers: "Followers",
      views30d: "30 Days Views",
      likes30d: "30 Days Likes",
      engagementRate: "ER Rate",
      gmv: "GMV",
    },
  },
};

const categoryCopy = {
  "Uncategorized": "???",
  "Beauty & Personal Care": "????",
  "Womenswear & Underwear": "????",
  "Fashion Accessories": "????",
  "Food & Beverages": "????",
  "Sports & Outdoor": "????",
  "Home Supplies": "????",
  "Menswear & Underwear": "????",
  "Toys & Hobbies": "????",
  "Furniture": "??",
  "Health": "??",
  "Phones & Electronics": "????",
  "Baby & Maternity": "??",
  "Household Appliances": "????",
  "Pet Supplies": "????",
  "Kitchenware": "??",
  "Tools & Hardware": "????",
  "Books, Magazines & Audio": "????",
  "Automotive & Motorcycle": "????",
  "Collectibles": "???",
  "Luggage & Bags": "??",
  "Shoes": "??",
  "Jewelry Accessories & Derivatives": "????",
  "Textiles & Soft Furnishings": "????",
};

const els = {
  heading: document.querySelector("h1"),
  eyebrow: document.querySelector(".eyebrow"),
  languageButtons: document.querySelectorAll("[data-language]"),
  totalCount: document.querySelector("#totalCount"),
  photoCount: document.querySelector("#photoCount"),
  socialCount: document.querySelector("#socialCount"),
  statLabels: document.querySelectorAll(".stats small"),
  controlLabels: document.querySelectorAll(".controls label > span"),
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
  resultLabel: document.querySelector(".result-bar span"),
  creatorGrid: document.querySelector("#creatorGrid"),
  loadMore: document.querySelector("#loadMore"),
};

const photoInfluencers = influencers.filter((item) => item.avatarLocal);

function numberValue(value) {
  return Number.isFinite(Number(value)) ? Number(value) : 0;
}

function formatCompact(value) {
  const numeric = numberValue(value);
  return new Intl.NumberFormat(language === "zh" ? "zh-CN" : "en", {
    notation: "compact",
    maximumFractionDigits: numeric >= 1000000 ? 1 : 0,
  }).format(numeric);
}

function text(key) {
  return copy[language][key];
}

function displayCategory(category) {
  return language === "zh" ? categoryCopy[category] || category : category;
}

function displayRegion(region) {
  return region || text("global");
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
  els.featureCategory.textContent = displayCategory(item.category);
  els.featureName.textContent = item.name;
  els.featureHandle.textContent = item.handle;
  els.featureHandle.href = item.socials[0]?.url || "#";
  els.featureFollowers.textContent = `${formatCompact(item.metrics.followers)} ${text("followers")}`;
  els.featureViews.textContent = `${formatCompact(item.metrics.views30d)} ${text("views30d")}`;
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
    `<option value="all">${text("allCategories")}</option>`,
    ...categories.map((category) => `<option value="${category}">${displayCategory(category)}</option>`),
  ].join("");
}

function populateSortOptions() {
  [...els.sortSelect.options].forEach((option) => {
    option.textContent = copy[language].sorts[option.value] || option.textContent;
  });
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
        displayCategory(item.category),
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
  els.resultCount.textContent = filtered.length.toLocaleString(language === "zh" ? "zh-CN" : "en");
  els.creatorGrid.innerHTML = visible
    .map(
      (item) => `
        <article class="creator-card">
          <div class="avatar-frame">${creatorImage(item)}</div>
          <div class="card-body">
            <div class="meta-row">
              <span>${displayRegion(item.region)}</span>
              <span>${displayCategory(item.category)}</span>
            </div>
            <div>
              <h3>${item.name}</h3>
              <a class="handle" href="${item.socials[0]?.url || "#"}" target="_blank" rel="noreferrer">
                ${item.handle}
              </a>
            </div>
            <div class="metric-row">
              <span>${formatCompact(item.metrics.followers)} ${text("followers")}</span>
              <span>${formatCompact(item.metrics.views30d)} ${text("views")}</span>
              <span>${numberValue(item.metrics.engagementRate).toFixed(1)}% ${text("er")}</span>
            </div>
            <div class="card-links">${socialLinks(item)}</div>
          </div>
        </article>
      `,
    )
    .join("");
  els.loadMore.hidden = visibleCount >= filtered.length;
}

function renderStaticText() {
  document.documentElement.lang = language === "zh" ? "zh-CN" : "en";
  document.title = text("documentTitle");
  els.heading.textContent = text("documentTitle");
  els.eyebrow.textContent = text("eyebrow");
  els.searchInput.placeholder = text("searchPlaceholder");
  els.resultLabel.textContent = text("matched");
  els.loadMore.textContent = text("loadMore");
  els.statLabels[0].textContent = text("total");
  els.statLabels[1].textContent = text("photos");
  els.statLabels[2].textContent = text("socialLinks");
  els.controlLabels[0].textContent = text("search");
  els.controlLabels[1].textContent = text("category");
  els.controlLabels[2].textContent = text("sort");
  els.languageButtons.forEach((button) => {
    const isActive = button.dataset.language === language;
    button.classList.toggle("active", isActive);
    button.setAttribute("aria-pressed", String(isActive));
  });
  populateSortOptions();
}

function renderCounts() {
  const socialCount = influencers.reduce((sum, item) => sum + item.socials.length, 0);
  els.totalCount.textContent = influencers.length.toLocaleString(language === "zh" ? "zh-CN" : "en");
  els.photoCount.textContent = photoInfluencers.length.toLocaleString(language === "zh" ? "zh-CN" : "en");
  els.socialCount.textContent = socialCount.toLocaleString(language === "zh" ? "zh-CN" : "en");
}

function setLanguage(nextLanguage) {
  language = nextLanguage === "en" ? "en" : "zh";
  localStorage.setItem(languageKey, language);
  const selectedCategory = els.categorySelect.value;
  renderStaticText();
  populateCategories();
  if ([...els.categorySelect.options].some((option) => option.value === selectedCategory)) {
    els.categorySelect.value = selectedCategory;
  }
  renderCounts();
  setFeature(activeIndex);
  applyFilters();
}

function startRotation() {
  if (rotationTimer) window.clearInterval(rotationTimer);
  rotationTimer = window.setInterval(() => setFeature(activeIndex + 1), 4200);
}

function init() {
  renderStaticText();
  renderCounts();
  populateCategories();
  renderPhotoStrip();
  setFeature(0);
  startRotation();
  applyFilters();

  els.searchInput.addEventListener("input", applyFilters);
  els.categorySelect.addEventListener("change", applyFilters);
  els.sortSelect.addEventListener("change", applyFilters);
  els.languageButtons.forEach((button) => {
    button.addEventListener("click", () => setLanguage(button.dataset.language));
  });
  els.loadMore.addEventListener("click", () => {
    visibleCount += pageSize;
    renderGrid();
  });
}

init();
