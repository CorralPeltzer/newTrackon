(() => {
  "use strict";

  const storageKey = "newtrackon-theme";
  const colorScheme = window.matchMedia("(prefers-color-scheme: dark)");

  const getStoredTheme = () => {
    try {
      const theme = window.localStorage.getItem(storageKey);
      return theme === "light" || theme === "dark" ? theme : null;
    } catch {
      return null;
    }
  };

  let selectedTheme = getStoredTheme();

  const storeTheme = (theme) => {
    try {
      window.localStorage.setItem(storageKey, theme);
    } catch {
      // The selected theme still applies for this page when storage is unavailable.
    }
  };

  const getTheme = () => selectedTheme || (colorScheme.matches ? "dark" : "light");

  const syncThemeComponents = (theme) => {
    document.querySelectorAll("rapi-doc").forEach((apiDocs) => {
      apiDocs.setAttribute("theme", theme);

      const primaryColorAttribute = `data-primary-color-${theme}`;
      if (apiDocs.hasAttribute(primaryColorAttribute)) {
        apiDocs.setAttribute("primary-color", apiDocs.getAttribute(primaryColorAttribute));
      }
    });
  };

  const applyTheme = (theme) => {
    document.documentElement.setAttribute("data-bs-theme", theme);
    syncThemeComponents(theme);
  };

  const updateThemeToggle = (theme) => {
    const toggle = document.querySelector("#theme-toggle");
    const toggleIcon = document.querySelector("#theme-toggle-icon");

    if (!toggle || !toggleIcon) {
      return;
    }

    const nextTheme = theme === "dark" ? "light" : "dark";
    const label = `Switch to ${nextTheme} theme`;
    toggleIcon.className = `fas ${nextTheme === "dark" ? "fa-moon" : "fa-sun"}`;
    toggle.setAttribute("aria-label", label);
    toggle.setAttribute("title", label);
  };

  applyTheme(getTheme());

  colorScheme.addEventListener("change", () => {
    if (!selectedTheme) {
      const theme = getTheme();
      applyTheme(theme);
      updateThemeToggle(theme);
    }
  });

  document.addEventListener("DOMContentLoaded", () => {
    const theme = getTheme();
    applyTheme(theme);
    updateThemeToggle(theme);

    document.querySelector("#theme-toggle")?.addEventListener("click", () => {
      selectedTheme = getTheme() === "dark" ? "light" : "dark";
      storeTheme(selectedTheme);
      applyTheme(selectedTheme);
      updateThemeToggle(selectedTheme);
    });
  });
})();
