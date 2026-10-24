(() => {
  const navToggle = document.querySelector("[data-nav-toggle]");
  const navigation = document.querySelector("[data-collapsible-nav]");

  if (navToggle && navigation) {
    const mobileViewport = window.matchMedia("(max-width: 760px)");
    const updateNavigationForViewport = () => {
      navToggle.hidden = !mobileViewport.matches;
      navigation.hidden = mobileViewport.matches;
      navToggle.setAttribute("aria-expanded", String(!mobileViewport.matches));
      navToggle.setAttribute(
        "aria-label",
        mobileViewport.matches ? "Open navigation" : "Close navigation",
      );
    };

    updateNavigationForViewport();
    mobileViewport.addEventListener("change", updateNavigationForViewport);

    navToggle.addEventListener("click", () => {
      const isExpanded = navToggle.getAttribute("aria-expanded") === "true";
      navToggle.setAttribute("aria-expanded", String(!isExpanded));
      navToggle.setAttribute(
        "aria-label",
        isExpanded ? "Open navigation" : "Close navigation",
      );
      navigation.hidden = isExpanded;
    });

    navigation.addEventListener("click", (event) => {
      if (event.target instanceof Element && event.target.closest("a, button")) {
        navigation.hidden = true;
        navToggle.setAttribute("aria-expanded", "false");
        navToggle.setAttribute("aria-label", "Open navigation");
      }
    });
  }

  document.querySelectorAll("[data-dismiss-alert]").forEach((button) => {
    button.addEventListener("click", () => {
      button.closest("[data-dismissible-alert]")?.remove();
    });
  });

  document.querySelectorAll("[data-dashboard-filters]").forEach((filters) => {
    const searchInput = filters.querySelector("[data-complaint-search]");
    const statusSelect = filters.querySelector("[data-complaint-status]");
    const list = document.querySelector("[data-complaint-list]");
    const filterEmpty = document.querySelector("[data-filter-empty]");
    const filterStatus = document.querySelector("[data-filter-status]");

    if (
      !(searchInput instanceof HTMLInputElement) ||
      !(statusSelect instanceof HTMLSelectElement) ||
      !list ||
      !filterEmpty ||
      !filterStatus
    ) {
      return;
    }

    const items = Array.from(list.querySelectorAll("[data-complaint-item]"));
    const updateComplaints = () => {
      const query = searchInput.value.trim().toLocaleLowerCase();
      const status = statusSelect.value;
      let visibleCount = 0;

      items.forEach((item) => {
        const matchesQuery = (item.getAttribute("data-search") ?? "")
          .toLocaleLowerCase()
          .includes(query);
        const matchesStatus = !status || item.getAttribute("data-status") === status;
        const isVisible = matchesQuery && matchesStatus;
        item.hidden = !isVisible;
        if (isVisible) visibleCount += 1;
      });

      filterEmpty.hidden = visibleCount !== 0;
      filterStatus.textContent = `Showing ${visibleCount} of ${items.length} complaints`;
    };

    searchInput.disabled = false;
    statusSelect.disabled = false;
    searchInput.addEventListener("input", updateComplaints);
    statusSelect.addEventListener("change", updateComplaints);
  });

  document.querySelectorAll("form[data-loading-form]").forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.reportValidity()) {
        event.preventDefault();
        return;
      }

      const submitButton = form.querySelector('button[type="submit"]');
      if (!(submitButton instanceof HTMLButtonElement)) return;

      submitButton.dataset.originalText = submitButton.textContent ?? "";
      submitButton.textContent = submitButton.dataset.loadingText ?? "Please wait…";
      submitButton.disabled = true;
      form.classList.add("is-submitting");
      form.setAttribute("aria-busy", "true");
    });
  });
})();
