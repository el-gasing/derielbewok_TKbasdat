(function () {
    "use strict";

    function sanitizeUserText(value) {
        if (typeof value !== "string") {
            return value;
        }

        return value
            .replace(/<[^>]*>/g, "")
            .replace(/[<>]/g, "")
            .replace(/[\u0000-\u001F\u007F]/g, "")
            .replace(/\s{2,}/g, " ")
            .trim();
    }

    function getCsrfToken() {
        var csrfField = document.querySelector("input[name='csrfmiddlewaretoken']");
        return csrfField ? csrfField.value : "";
    }

    function isMutatingMethod(method) {
        var normalized = (method || "GET").toUpperCase();
        return ["POST", "PUT", "PATCH", "DELETE"].indexOf(normalized) !== -1;
    }

    function isSameOrigin(url) {
        try {
            var targetUrl = new URL(url, window.location.origin);
            return targetUrl.origin === window.location.origin;
        } catch (error) {
            return false;
        }
    }

    function hardenFetchCsrf() {
        if (typeof window.fetch !== "function") {
            return;
        }

        var originalFetch = window.fetch.bind(window);
        window.fetch = function (resource, init) {
            var requestInit = init || {};
            var method = requestInit.method || "GET";
            var requestUrl = typeof resource === "string" ? resource : (resource && resource.url ? resource.url : "");

            if (isMutatingMethod(method) && isSameOrigin(requestUrl)) {
                var csrfToken = getCsrfToken();
                if (csrfToken) {
                    var headers = new Headers(requestInit.headers || {});
                    if (!headers.has("X-CSRFToken")) {
                        headers.set("X-CSRFToken", csrfToken);
                    }
                    requestInit.headers = headers;
                }
            }

            return originalFetch(resource, requestInit);
        };
    }

    function hardenForms() {
        var forms = document.querySelectorAll("form");
        forms.forEach(function (form) {
            var isPostForm = (form.getAttribute("method") || "GET").toUpperCase() === "POST";
            var csrfToken = getCsrfToken();

            if (isPostForm && csrfToken && !form.querySelector("input[name='csrfmiddlewaretoken']")) {
                var hiddenToken = document.createElement("input");
                hiddenToken.type = "hidden";
                hiddenToken.name = "csrfmiddlewaretoken";
                hiddenToken.value = csrfToken;
                form.appendChild(hiddenToken);
            }

            form.addEventListener("submit", function () {
                var fields = form.querySelectorAll("input[type='text'], input[type='search'], input[type='email'], input[type='tel'], textarea");
                fields.forEach(function (field) {
                    if (field.dataset.sanitize === "off") {
                        return;
                    }
                    field.value = sanitizeUserText(field.value);
                });
            });
        });
    }

    function setupRevealAnimation() {
        var revealTargets = document.querySelectorAll(".welcome-card, .sidebar, .stat-card, .card");
        if (!revealTargets.length || typeof IntersectionObserver !== "function") {
            return;
        }

        revealTargets.forEach(function (el) {
            el.classList.add("js-reveal");
        });

        var revealObserver = new IntersectionObserver(function (entries, observer) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add("in-view");
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: 0.14 });

        revealTargets.forEach(function (el) {
            revealObserver.observe(el);
        });
    }

    function setupStatCounter() {
        var statValues = document.querySelectorAll(".stat-card .stat-value");
        statValues.forEach(function (el) {
            var raw = (el.textContent || "").trim();
            var match = raw.match(/\d+/g);
            if (!match) {
                return;
            }

            var target = Number(match.join(""));
            if (!Number.isFinite(target)) {
                return;
            }

            var duration = 1200;
            var startTime = performance.now();

            function animateCount(now) {
                var progress = Math.min((now - startTime) / duration, 1);
                var eased = 1 - Math.pow(1 - progress, 3);
                var value = Math.round(target * eased);
                el.textContent = raw.replace(/\d[\d.,]*/g, value.toLocaleString("id-ID"));

                if (progress < 1) {
                    requestAnimationFrame(animateCount);
                }
            }

            requestAnimationFrame(animateCount);
        });
    }

    function setupActiveMenu() {
        var menuButtons = document.querySelectorAll("a.menu-button[href]");
        if (!menuButtons.length) {
            return;
        }

        var currentPath = window.location.pathname;
        menuButtons.forEach(function (btn) {
            if (btn.getAttribute("href") === currentPath) {
                btn.classList.add("is-active");
            }
        });
    }

    function setupCardTilt() {
        var cards = document.querySelectorAll(".stat-card");
        cards.forEach(function (card) {
            card.addEventListener("mousemove", function (event) {
                var rect = card.getBoundingClientRect();
                var x = event.clientX - rect.left;
                var y = event.clientY - rect.top;
                var midX = rect.width / 2;
                var midY = rect.height / 2;
                var rotateX = ((y - midY) / midY) * -4;
                var rotateY = ((x - midX) / midX) * 4;
                card.style.transform = "perspective(900px) rotateX(" + rotateX.toFixed(2) + "deg) rotateY(" + rotateY.toFixed(2) + "deg)";
            });

            card.addEventListener("mouseleave", function () {
                card.style.transform = "perspective(900px) rotateX(0deg) rotateY(0deg)";
            });
        });
    }


    document.addEventListener("DOMContentLoaded", function () {
        hardenFetchCsrf();
        hardenForms();

        setupRevealAnimation();
        setupStatCounter();
        setupActiveMenu();
        setupCardTilt();
        setupDynamicGreeting();
    });
})();
