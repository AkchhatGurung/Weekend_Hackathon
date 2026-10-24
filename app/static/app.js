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
