(function () {
  const payloadNode = document.getElementById("diplomaDesignDefinition");
  const previewContextNode = document.getElementById("diplomaPreviewContext");
  const canvas = document.getElementById("diplomaEditorCanvas");
  if (!payloadNode || !canvas) {
    return;
  }

  const definition = JSON.parse(payloadNode.textContent || "{}");
  const previewContext = previewContextNode ? JSON.parse(previewContextNode.textContent || "{}") : {};
  const canvasWidth = Number(canvas.dataset.canvasWidth || 3508);
  const canvasHeight = Number(canvas.dataset.canvasHeight || 2480);
  const fallbackBackgroundUrl = canvas.dataset.backgroundUrl || "";
  const canvasScaleNode = canvas.closest(".diploma-canvas-scale");

  const state = {
    canvasWidth,
    canvasHeight,
    saveUrl: canvas.dataset.saveUrl,
    elements: definition && definition.elements ? JSON.parse(JSON.stringify(definition.elements)) : {},
    selectedKey: null,
    drag: null,
    pristine: {},
  };

  if (!state.elements.fondo_diploma) {
    state.elements.fondo_diploma = {
      key: "fondo_diploma",
      label: "Fondo diploma",
      type: "imagen",
      visible: true,
      x: 0,
      y: 0,
      width: canvasWidth,
      height: canvasHeight,
      font_size: 20,
      color: "#111827",
      align: "center",
      z_index: 0,
      token: "{{ fondo_diploma }}",
      texto: "",
      image_url: fallbackBackgroundUrl,
    };
  }
  state.pristine = JSON.parse(JSON.stringify(state.elements));

  const ui = {
    layerList: document.getElementById("editorLayerList"),
    layerCount: document.getElementById("editorLayerCount"),
    layerSummary: document.getElementById("editorLayerSummary"),
    emptyState: document.getElementById("editorEmptyState"),
    propertyForm: document.getElementById("editorPropertyForm"),
    label: document.getElementById("editorPropLabel"),
    type: document.getElementById("editorPropType"),
    token: document.getElementById("editorPropToken"),
    texto: document.getElementById("editorPropTexto"),
    imageUrl: document.getElementById("editorPropImageUrl"),
    x: document.getElementById("editorPropX"),
    y: document.getElementById("editorPropY"),
    width: document.getElementById("editorPropWidth"),
    height: document.getElementById("editorPropHeight"),
    fontSize: document.getElementById("editorPropFontSize"),
    color: document.getElementById("editorPropColor"),
    align: document.getElementById("editorPropAlign"),
    zIndex: document.getElementById("editorPropZIndex"),
    visible: document.getElementById("editorPropVisible"),
    textGroup: document.getElementById("editorTextGroup"),
    textStyleGroup: document.getElementById("editorTextStyleGroup"),
    imageGroup: document.getElementById("editorImageGroup"),
    alignGroup: document.getElementById("editorAlignGroup"),
    reset: document.getElementById("editorReset"),
    save: document.getElementById("editorSave"),
  };

  function csrfToken() {
    const cookieMatch = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    if (cookieMatch) {
      return decodeURIComponent(cookieMatch[2]);
    }

    const csrfInput = document.querySelector("input[name='csrfmiddlewaretoken']");
    if (csrfInput && csrfInput.value) {
      return csrfInput.value;
    }

    const csrfMeta = document.querySelector("meta[name='csrf-token']");
    return csrfMeta ? csrfMeta.getAttribute("content") || "" : "";
  }

  function clamp(value, min, max) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
      return min;
    }
    return Math.min(Math.max(numeric, min), max);
  }

  function currentScale() {
    if (canvasScaleNode) {
      const transform = window.getComputedStyle(canvasScaleNode).transform;
      if (transform && transform !== "none") {
        const matrix = transform.match(/matrix\(([^)]+)\)/);
        if (matrix) {
          const values = matrix[1].split(",").map(Number);
          if (values.length >= 1 && Number.isFinite(values[0]) && values[0] > 0) {
            return values[0];
          }
        }
      }
    }

    const configuredScale = Number(canvas.dataset.editorScale || 0.28);
    return configuredScale > 0 ? configuredScale : 0.28;
  }

  function normalizeElement(element) {
    const normalized = element;
    normalized.key = normalized.key || "";
    normalized.label = normalized.label || normalized.key;
    normalized.type = normalized.type || "texto";
    normalized.visible = normalized.visible !== false;
    normalized.width = clamp(normalized.width || 200, 20, state.canvasWidth);
    normalized.height = clamp(normalized.height || 80, 20, state.canvasHeight);
    normalized.x = clamp(normalized.x || 0, 0, Math.max(state.canvasWidth - normalized.width, 0));
    normalized.y = clamp(normalized.y || 0, 0, Math.max(state.canvasHeight - normalized.height, 0));
    normalized.font_size = clamp(normalized.font_size || 24, 8, 300);
    normalized.z_index = clamp(normalized.z_index || 1, 0, 9999);
    normalized.color = normalized.color || "#111827";
    normalized.align = normalized.align || "center";
    normalized.token = normalized.token || "";
    normalized.texto = normalized.texto || "";
    normalized.image_url = normalized.image_url || "";

    if (normalized.key === "fondo_diploma") {
      normalized.x = 0;
      normalized.y = 0;
      normalized.width = state.canvasWidth;
      normalized.height = state.canvasHeight;
      normalized.z_index = 0;
    }
    return normalized;
  }

  function normalizeState() {
    Object.keys(state.elements).forEach(function (key) {
      state.elements[key] = normalizeElement(state.elements[key]);
    });
  }

  function previewText(element) {
    let resolved = element.texto || element.token || element.label || element.key;
    Object.entries(previewContext).forEach(function (entry) {
      const token = entry[0];
      const value = entry[1];
      resolved = resolved.split(token).join(value);
    });
    return resolved;
  }

  function typeLabel(type) {
    const labels = {
      texto: "Texto",
      imagen: "Imagen",
      decorativo: "Decorativo",
    };
    return labels[type] || type || "Elemento";
  }

  function layerTitle(element) {
    return element.label || element.key || "Elemento sin nombre";
  }

  function elementMarkup(element) {
    if (element.type === "imagen") {
      if (element.image_url) {
        return `<div class="editor-element-content"><img src="${element.image_url}" alt="${element.label}"></div>`;
      }
      return `<div class="editor-element-content"><div class="editor-image-placeholder">${element.label}</div></div>`;
    }

    const klass = `editor-element-content align-${element.align || "center"}`;
    return `<div class="${klass}">${previewText(element)}</div>`;
  }

  function renderCanvas() {
    normalizeState();
    const elements = Object.values(state.elements)
      .sort(function (left, right) { return left.z_index - right.z_index; })
      .map(function (element) {
        const typeClass = `is-${element.type === "imagen" ? "image" : element.type === "decorativo" ? "decorative" : "text"}`;
        const selectedClass = state.selectedKey === element.key ? "is-selected" : "";
        const display = element.visible ? "block" : "none";
        return `
          <div
            class="diploma-editor-element ${typeClass} ${selectedClass}"
            data-key="${element.key}"
            style="
              left:${element.x}px;
              top:${element.y}px;
              width:${element.width}px;
              height:${element.height}px;
              font-size:${element.font_size}px;
              color:${element.color};
              text-align:${element.align};
              z-index:${element.z_index};
              display:${display};
            ">
            ${elementMarkup(element)}
          </div>
        `;
      })
      .join("");

    const activeBackground = state.elements.fondo_diploma && state.elements.fondo_diploma.image_url
      ? state.elements.fondo_diploma.image_url
      : fallbackBackgroundUrl;
    canvas.style.backgroundImage = activeBackground ? `url("${activeBackground}")` : "none";
    canvas.innerHTML = elements;
  }

  function renderLayerPanel() {
    if (!ui.layerList) {
      return;
    }

    const elements = Object.values(state.elements)
      .sort(function (left, right) {
        if (right.z_index !== left.z_index) {
          return right.z_index - left.z_index;
        }
        return left.key.localeCompare(right.key);
      });

    if (ui.layerCount) {
      ui.layerCount.textContent = String(elements.length);
    }

    const visibleCount = elements.filter(function (element) { return element.visible; }).length;
    const hiddenCount = elements.length - visibleCount;
    if (ui.layerSummary) {
      ui.layerSummary.innerHTML = `
        <span class="editor-layer-summary-pill is-visible">Visibles: ${visibleCount}</span>
        <span class="editor-layer-summary-pill is-hidden">Ocultas: ${hiddenCount}</span>
      `;
    }

    if (!elements.length) {
      ui.layerList.innerHTML = '<div class="editor-layer-empty">No hay elementos cargados en este diseño.</div>';
      return;
    }

    ui.layerList.innerHTML = elements.map(function (element) {
      const isActive = state.selectedKey === element.key;
      const visibilityClass = element.visible ? "is-visible" : "is-hidden";
      const visibilityLabel = element.visible ? "Visible" : "Oculto";
      const toggleLabel = element.visible ? "Ocultar" : "Mostrar";
      const tokenLabel = element.token || element.key;
      const hiddenHelp = element.visible ? "" : '<div class="editor-layer-help">Oculto en el lienzo. Puedes seleccionarlo y volverlo a mostrar.</div>';
      return `
        <div class="editor-layer-item ${isActive ? "is-active" : ""} ${element.visible ? "" : "is-hidden"}" data-key="${element.key}">
          <div class="editor-layer-main">
            <div class="editor-layer-meta">
              <div class="editor-layer-title-row">
                <span class="editor-layer-title">${layerTitle(element)}</span>
              </div>
              <div class="editor-layer-token">${tokenLabel}</div>
              <div class="editor-layer-badges">
                <span class="editor-layer-badge is-type">${typeLabel(element.type)}</span>
                <span class="editor-layer-badge is-z">Orden ${Math.round(element.z_index)}</span>
                <span class="editor-layer-badge ${visibilityClass}">${visibilityLabel}</span>
              </div>
              ${hiddenHelp}
            </div>
          </div>
          <div class="editor-layer-actions">
            <button type="button" class="editor-layer-select" data-action="select" data-key="${element.key}">
              Seleccionar
            </button>
            <button type="button" class="editor-layer-toggle" data-action="toggle-visibility" data-key="${element.key}">
              ${toggleLabel}
            </button>
          </div>
        </div>
      `;
    }).join("");
  }

  function syncSidebar() {
    const element = state.elements[state.selectedKey];
    if (!element) {
      ui.emptyState.style.display = "block";
      ui.propertyForm.classList.add("is-hidden");
      return;
    }

    ui.emptyState.style.display = "none";
    ui.propertyForm.classList.remove("is-hidden");
    ui.label.value = element.label || "";
    ui.type.value = element.type || "";
    ui.token.value = element.token || "";
    ui.texto.value = element.texto || "";
    ui.imageUrl.value = element.image_url || "";
    ui.x.value = Math.round(element.x);
    ui.y.value = Math.round(element.y);
    ui.width.value = Math.round(element.width);
    ui.height.value = Math.round(element.height);
    ui.fontSize.value = Math.round(element.font_size);
    ui.color.value = element.color || "#111827";
    ui.align.value = element.align || "center";
    ui.zIndex.value = Math.round(element.z_index);
    ui.visible.checked = element.visible !== false;

    const isTextual = element.type !== "imagen";
    ui.textGroup.style.display = isTextual ? "block" : "none";
    ui.textStyleGroup.style.display = isTextual ? "flex" : "none";
    ui.alignGroup.style.display = isTextual ? "block" : "none";
    ui.imageGroup.style.display = element.type === "imagen" ? "block" : "none";
  }

  function selectElement(key) {
    if (!state.elements[key]) {
      return;
    }
    state.selectedKey = key;
    renderCanvas();
    renderLayerPanel();
    syncSidebar();
  }

  function setElementVisibility(key, visible) {
    if (!state.elements[key]) {
      return;
    }

    state.elements[key].visible = visible;
    state.elements[key] = normalizeElement(state.elements[key]);
    renderCanvas();
    renderLayerPanel();
    syncSidebar();
  }

  function updateSelectedFromSidebar() {
    const element = state.elements[state.selectedKey];
    if (!element) {
      return;
    }

    element.x = Number(ui.x.value || element.x);
    element.y = Number(ui.y.value || element.y);
    element.width = Number(ui.width.value || element.width);
    element.height = Number(ui.height.value || element.height);
    element.z_index = Number(ui.zIndex.value || element.z_index);
    element.visible = ui.visible.checked;

    if (element.type !== "imagen") {
      element.texto = ui.texto.value;
      element.font_size = Number(ui.fontSize.value || element.font_size);
      element.color = ui.color.value || element.color;
      element.align = ui.align.value || element.align;
    }

    state.elements[state.selectedKey] = normalizeElement(element);
    renderCanvas();
    renderLayerPanel();
    syncSidebar();
  }

  canvas.addEventListener("mousedown", function (event) {
    const target = event.target.closest(".diploma-editor-element");
    if (!target) {
      return;
    }
    const key = target.dataset.key;
    const element = state.elements[key];
    if (!element) {
      return;
    }
    selectElement(key);
    state.drag = {
      key: key,
      startX: event.clientX,
      startY: event.clientY,
      originX: element.x,
      originY: element.y,
    };
    event.preventDefault();
  });

  window.addEventListener("mousemove", function (event) {
    if (!state.drag) {
      return;
    }
    const element = state.elements[state.drag.key];
    if (!element) {
      return;
    }

    const scale = currentScale();
    const deltaX = (event.clientX - state.drag.startX) / scale;
    const deltaY = (event.clientY - state.drag.startY) / scale;
    element.x = state.drag.originX + deltaX;
    element.y = state.drag.originY + deltaY;
    state.elements[state.drag.key] = normalizeElement(element);
    renderCanvas();
    syncSidebar();
  });

  window.addEventListener("mouseup", function () {
    state.drag = null;
  });

  canvas.addEventListener("click", function (event) {
    const target = event.target.closest(".diploma-editor-element");
    if (!target) {
      return;
    }
    selectElement(target.dataset.key);
  });

  if (ui.layerList) {
    ui.layerList.addEventListener("click", function (event) {
      const actionNode = event.target.closest("[data-action]");
      if (!actionNode) {
        return;
      }

      const key = actionNode.dataset.key;
      const action = actionNode.dataset.action;
      if (!key || !state.elements[key]) {
        return;
      }

      if (action === "toggle-visibility") {
        event.preventDefault();
        event.stopPropagation();
        state.selectedKey = key;
        setElementVisibility(key, !state.elements[key].visible);
        return;
      }

      if (action === "select") {
        event.preventDefault();
        selectElement(key);
      }
    });
  }

  [ui.texto, ui.x, ui.y, ui.width, ui.height, ui.fontSize, ui.color, ui.align, ui.zIndex, ui.visible].forEach(function (input) {
    if (!input) {
      return;
    }
    input.addEventListener("input", updateSelectedFromSidebar);
    input.addEventListener("change", updateSelectedFromSidebar);
  });

  ui.reset.addEventListener("click", function () {
    state.elements = JSON.parse(JSON.stringify(state.pristine));
    const availableKey = state.selectedKey && state.elements[state.selectedKey]
      ? state.selectedKey
      : Object.keys(state.elements).find(function (key) { return key !== "fondo_diploma"; }) || Object.keys(state.elements)[0];
    renderCanvas();
    if (availableKey) {
      selectElement(availableKey);
    } else {
      syncSidebar();
    }
  });

  ui.save.addEventListener("click", async function () {
    const originalLabel = ui.save.textContent;
    ui.save.disabled = true;
    ui.save.textContent = "Guardando...";

    try {
      normalizeState();
      const token = csrfToken();
      const response = await fetch(state.saveUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { "X-CSRFToken": token } : {}),
        },
        body: JSON.stringify({
          elementos: state.elements,
        }),
      });

      const payload = await response.json();
      if (!response.ok || !payload.success) {
        window.alert(payload.error || "No se pudo guardar el diseño.");
        return;
      }

      state.elements = payload.elementos ? JSON.parse(JSON.stringify(payload.elementos)) : state.elements;
      state.pristine = JSON.parse(JSON.stringify(state.elements));
      renderCanvas();
      renderLayerPanel();
      syncSidebar();
      window.alert(payload.message || "Diseño guardado correctamente.");
    } catch (error) {
      window.alert("Ocurrió un error al guardar el diseño.");
    } finally {
      ui.save.disabled = false;
      ui.save.textContent = originalLabel;
    }
  });

  renderCanvas();
  renderLayerPanel();
  const firstKey = Object.keys(state.elements).find(function (key) {
    return key !== "fondo_diploma";
  });
  if (firstKey) {
    selectElement(firstKey);
  } else {
    syncSidebar();
  }
})();
