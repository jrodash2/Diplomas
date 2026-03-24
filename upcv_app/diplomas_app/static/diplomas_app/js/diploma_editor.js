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
    uploadUrl: canvas.dataset.uploadUrl || "",
    elements: definition && definition.elements ? JSON.parse(JSON.stringify(definition.elements)) : {},
    selectedKey: null,
    drag: null,
    pristine: {},
    pendingImageTarget: null,
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
      font_family: 'Georgia, "Times New Roman", serif',
      font_weight: "400",
      color: "#111827",
      align: "center",
      z_index: 0,
      token: "{{ fondo_diploma }}",
      texto: "",
      image_url: fallbackBackgroundUrl,
      shape: "rect",
    };
  }
  state.pristine = JSON.parse(JSON.stringify(state.elements));

  const ui = {
    tabButtons: Array.from(document.querySelectorAll(".editor-sidebar-tab")),
    tabPanels: Array.from(document.querySelectorAll(".editor-sidebar-panel")),
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
    fontFamily: document.getElementById("editorPropFontFamily"),
    bold: document.getElementById("editorPropBold"),
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
    addText: document.getElementById("editorAddText"),
    addImage: document.getElementById("editorAddImage"),
    imageInput: document.getElementById("editorImageInput"),
    replaceImage: document.getElementById("editorReplaceImage"),
    uploadFeedback: document.getElementById("editorUploadFeedback"),
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

  function setFeedback(message, tone) {
    if (!ui.uploadFeedback) {
      return;
    }
    ui.uploadFeedback.classList.remove("text-muted", "text-success", "text-danger");
    ui.uploadFeedback.classList.add(tone === "success" ? "text-success" : tone === "error" ? "text-danger" : "text-muted");
    ui.uploadFeedback.textContent = message;
  }

  function notify(message, tone) {
    const normalizedTone = tone === "error" ? "error" : tone === "warning" ? "warning" : tone === "success" ? "success" : "info";
    if (typeof window.showDiplomaToast === "function") {
      window.showDiplomaToast(message, normalizedTone);
      return;
    }
    setFeedback(message, normalizedTone === "error" ? "error" : "neutral");
    console.warn(message);
  }

  function setActiveSidebarTab(tabName) {
    ui.tabButtons.forEach(function (button) {
      const isActive = button.dataset.tabTarget === tabName;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
    });

    ui.tabPanels.forEach(function (panel) {
      panel.classList.toggle("is-active", panel.dataset.tabPanel === tabName);
    });
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
    normalized.label = normalized.label || normalized.key || "Elemento";
    normalized.type = normalized.type || "texto";
    normalized.visible = normalized.visible !== false;
    normalized.width = clamp(normalized.width || 200, 20, state.canvasWidth);
    normalized.height = clamp(normalized.height || 80, 20, state.canvasHeight);
    normalized.x = clamp(normalized.x || 0, 0, Math.max(state.canvasWidth - normalized.width, 0));
    normalized.y = clamp(normalized.y || 0, 0, Math.max(state.canvasHeight - normalized.height, 0));
    normalized.font_size = clamp(normalized.font_size || 24, 8, 300);
    normalized.font_family = normalized.font_family || 'Georgia, "Times New Roman", serif';
    normalized.font_weight = String(normalized.font_weight || "400");
    normalized.z_index = clamp(normalized.z_index || 1, 0, 9999);
    normalized.color = normalized.color || "#111827";
    normalized.align = normalized.align || "center";
    normalized.token = normalized.token || "";
    normalized.texto = normalized.texto || "";
    normalized.image_url = normalized.image_url || "";
    normalized.shape = normalized.shape || "rect";

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

  function previewImageUrl(element) {
    let resolved = element.image_url || "";
    Object.entries(previewContext).forEach(function (entry) {
      const token = entry[0];
      const value = entry[1];
      resolved = resolved.split(token).join(value);
    });
    return resolved;
  }

  function renderSafeBoldHtml(text) {
    const escaped = String(text || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");

    return escaped.replace(/(\*\*|__)(.+?)\1/g, "<strong>$2</strong>");
  }

  function previewTextPayload(element) {
    const resolved = previewText(element);
    if (element.key === "descripcion_curso") {
      return {
        text: resolved,
        html: renderSafeBoldHtml(resolved),
        asHtml: true,
      };
    }

    return {
      text: resolved,
      html: "",
      asHtml: false,
    };
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

  function nextZIndex() {
    const zIndexes = Object.values(state.elements).map(function (element) {
      return Number(element.z_index || 0);
    });
    return (Math.max.apply(null, zIndexes.length ? zIndexes : [0]) || 0) + 1;
  }

  function generateUniqueKey(prefix) {
    const safePrefix = prefix || "custom";
    let key;
    do {
      key = safePrefix + "_" + Date.now().toString(36) + "_" + Math.random().toString(36).slice(2, 6);
    } while (state.elements[key]);
    return key;
  }

  function defaultPosition(width, height) {
    return {
      x: clamp(Math.round((state.canvasWidth - width) / 2), 0, Math.max(state.canvasWidth - width, 0)),
      y: clamp(Math.round((state.canvasHeight - height) / 2), 0, Math.max(state.canvasHeight - height, 0)),
    };
  }

  function createCustomTextElement() {
    const width = 960;
    const height = 180;
    const position = defaultPosition(width, height);
    const key = generateUniqueKey("custom_text");
    return normalizeElement({
      key: key,
      label: "Texto personalizado",
      type: "texto",
      visible: true,
      x: position.x,
      y: position.y,
      width: width,
      height: height,
      font_size: 42,
      font_family: 'Georgia, "Times New Roman", serif',
      font_weight: "400",
      color: "#111827",
      align: "center",
      z_index: nextZIndex(),
      token: "",
      texto: "Nuevo texto",
      image_url: "",
      shape: "rect",
    });
  }

  function createCustomImageElement(imageUrl) {
    const width = 420;
    const height = 260;
    const position = defaultPosition(width, height);
    const key = generateUniqueKey("custom_image");
    return normalizeElement({
      key: key,
      label: "Imagen personalizada",
      type: "imagen",
      visible: true,
      x: position.x,
      y: position.y,
      width: width,
      height: height,
      font_size: 20,
      font_family: 'Georgia, "Times New Roman", serif',
      font_weight: "400",
      color: "#111827",
      align: "center",
      z_index: nextZIndex(),
      token: "",
      texto: "",
      image_url: imageUrl || "",
      shape: "rect",
    });
  }

  function elementMarkup(element) {
    if (element.type === "imagen") {
      const imageUrl = previewImageUrl(element);
      const shapeClass = element.shape === "circle" ? " is-circle diploma-photo-circle" : "";
      const imageClass = element.shape === "circle" ? "diploma-photo-media" : "";
      const placeholderClass = element.shape === "circle" ? "editor-image-placeholder diploma-photo-placeholder" : "editor-image-placeholder";
      if (imageUrl) {
        return `<div class="editor-element-content${shapeClass}"><img src="${imageUrl}" alt="${element.label}" class="${imageClass}"></div>`;
      }
      return `<div class="editor-element-content${shapeClass}"><div class="${placeholderClass}">${element.label}</div></div>`;
    }

    const klass = `editor-element-content diploma-text-element align-${element.align || "center"}`;
    const preview = previewTextPayload(element);
    if (preview.asHtml) {
      return `<div class="${klass}"><div class="diploma-text-flow">${preview.html}</div></div>`;
    }

    return `<div class="${klass}"><div class="diploma-text-flow">${preview.text}</div></div>`;
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
              font-family:${element.font_family};
              font-weight:${element.font_weight};
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
      const typeClass = element.type === "imagen" ? "is-image" : element.type === "decorativo" ? "is-decorative" : "is-text";
      const visibilityClass = element.visible ? "is-visible" : "is-hidden";
      const visibilityLabel = element.visible ? "Visible" : "Oculto";
      const toggleLabel = element.visible ? "Ocultar" : "Mostrar";
      const tokenLabel = element.token || element.key;
      return `
        <div class="editor-layer-item ${isActive ? "is-active" : ""} ${element.visible ? "" : "is-hidden"}" data-key="${element.key}">
          <button type="button" class="editor-layer-trigger" data-action="select" data-key="${element.key}" aria-expanded="${isActive ? "true" : "false"}">
            <span class="editor-layer-leading">
              <span class="editor-layer-type-dot ${typeClass}" aria-hidden="true"></span>
              <span class="editor-layer-title">${layerTitle(element)}</span>
            </span>
            <span class="editor-layer-summary-inline">
              <span class="editor-layer-inline-pill ${visibilityClass}">${visibilityLabel}</span>
              <span class="editor-layer-inline-pill is-order">#${Math.round(element.z_index)}</span>
            </span>
          </button>
          <div class="editor-layer-panel">
            <div class="editor-layer-panel-meta">
              <span class="editor-layer-badge is-type">${typeLabel(element.type)}</span>
              <span class="editor-layer-badge is-z">Orden ${Math.round(element.z_index)}</span>
              <span class="editor-layer-badge ${visibilityClass}">${visibilityLabel}</span>
            </div>
            <div class="editor-layer-token">${tokenLabel}</div>
            <div class="editor-layer-actions">
              <button type="button" class="editor-layer-select" data-action="select" data-key="${element.key}">Seleccionar</button>
              <button type="button" class="editor-layer-toggle" data-action="toggle-visibility" data-key="${element.key}">${toggleLabel}</button>
            </div>
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
    ui.fontFamily.value = element.font_family || 'Georgia, "Times New Roman", serif';
    ui.bold.checked = String(element.font_weight || "400") === "700";
    ui.color.value = element.color || "#111827";
    ui.align.value = element.align || "center";
    ui.zIndex.value = Math.round(element.z_index);
    ui.visible.checked = element.visible !== false;

    const isTextual = element.type !== "imagen";
    ui.textGroup.style.display = isTextual ? "block" : "none";
    ui.textStyleGroup.style.display = isTextual ? "flex" : "none";
    ui.alignGroup.style.display = isTextual ? "block" : "none";
    ui.imageGroup.style.display = element.type === "imagen" ? "block" : "none";
    if (ui.replaceImage) {
      ui.replaceImage.style.display = element.type === "imagen" && element.key !== "fondo_diploma" ? "inline-flex" : "none";
    }
  }

  function selectElement(key) {
    if (!state.elements[key]) {
      return;
    }
    state.selectedKey = key;
    renderCanvas();
    renderLayerPanel();
    syncSidebar();
    setActiveSidebarTab("properties");
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

  function refreshFontInCanvas(fontFamily) {
    if (!fontFamily || !document.fonts || typeof document.fonts.load !== "function") {
      return;
    }
    document.fonts.load(`32px ${fontFamily}`).then(function () {
      renderCanvas();
      renderLayerPanel();
      syncSidebar();
    }).catch(function () {
      // Ignore font loading failures and keep current render/fallback stack.
    });
  }

  function updateSelectedFromSidebar() {
    const element = state.elements[state.selectedKey];
    if (!element) {
      return;
    }

    element.label = ui.label.value || element.label;
    element.x = Number(ui.x.value || element.x);
    element.y = Number(ui.y.value || element.y);
    element.width = Number(ui.width.value || element.width);
    element.height = Number(ui.height.value || element.height);
    element.z_index = Number(ui.zIndex.value || element.z_index);
    element.visible = ui.visible.checked;

    if (element.type !== "imagen") {
      element.texto = ui.texto.value;
      element.font_size = Number(ui.fontSize.value || element.font_size);
      element.font_family = ui.fontFamily.value || element.font_family;
      element.font_weight = ui.bold.checked ? "700" : "400";
      element.color = ui.color.value || element.color;
      element.align = ui.align.value || element.align;
    }

    state.elements[state.selectedKey] = normalizeElement(element);
    renderCanvas();
    renderLayerPanel();
    syncSidebar();
    if (element.type !== "imagen") {
      refreshFontInCanvas(state.elements[state.selectedKey].font_family);
    }
  }

  function commitDeferredNumericField(input) {
    if (!input) {
      return;
    }
    input.addEventListener("change", updateSelectedFromSidebar);
    input.addEventListener("blur", updateSelectedFromSidebar);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        input.blur();
      }
    });
  }

  async function uploadSelectedImage(file, targetKey) {
    if (!file) {
      return;
    }
    if (!state.uploadUrl) {
      notify("No hay una ruta configurada para subir imágenes del editor.", "error");
      return;
    }

    const buttonToDisable = targetKey ? ui.replaceImage : ui.addImage;
    const originalLabel = buttonToDisable ? buttonToDisable.textContent : "";
    if (buttonToDisable) {
      buttonToDisable.disabled = true;
      buttonToDisable.textContent = targetKey ? "Subiendo..." : "Cargando...";
    }
    setFeedback("Subiendo imagen...", "neutral");

    try {
      const formData = new FormData();
      formData.append("image", file);
      const token = csrfToken();
      const response = await fetch(state.uploadUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: token ? { "X-CSRFToken": token } : {},
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok || !payload.success) {
        throw new Error(payload.error || "No se pudo subir la imagen.");
      }

      if (targetKey && state.elements[targetKey]) {
        state.elements[targetKey].image_url = payload.image_url;
        state.elements[targetKey].label = ui.label.value || state.elements[targetKey].label;
        state.elements[targetKey] = normalizeElement(state.elements[targetKey]);
        selectElement(targetKey);
        setFeedback("Imagen reemplazada correctamente. Guarda el diseño para persistir el cambio.", "success");
      } else {
        const newElement = createCustomImageElement(payload.image_url);
        state.elements[newElement.key] = newElement;
        selectElement(newElement.key);
        setFeedback("Imagen agregada al lienzo. Ajusta posición/tamaño y guarda el diseño.", "success");
      }
      renderCanvas();
      renderLayerPanel();
      syncSidebar();
    } catch (error) {
      notify(error.message || "No se pudo subir la imagen.", "error");
      setFeedback(error.message || "No se pudo subir la imagen.", "error");
    } finally {
      if (buttonToDisable) {
        buttonToDisable.disabled = false;
        buttonToDisable.textContent = originalLabel;
      }
      if (ui.imageInput) {
        ui.imageInput.value = "";
      }
      state.pendingImageTarget = null;
    }
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

  ui.tabButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setActiveSidebarTab(button.dataset.tabTarget);
    });
  });

  [ui.label, ui.texto, ui.fontFamily, ui.bold, ui.color, ui.align, ui.zIndex, ui.visible].forEach(function (input) {
    if (!input) {
      return;
    }
    input.addEventListener("input", updateSelectedFromSidebar);
    input.addEventListener("change", updateSelectedFromSidebar);
  });

  [ui.x, ui.y, ui.width, ui.height, ui.fontSize].forEach(commitDeferredNumericField);

  if (ui.addText) {
    ui.addText.addEventListener("click", function () {
      const newElement = createCustomTextElement();
      state.elements[newElement.key] = newElement;
      selectElement(newElement.key);
      setFeedback("Texto agregado al lienzo. Edita sus propiedades y guarda el diseño.", "success");
    });
  }

  if (ui.addImage && ui.imageInput) {
    ui.addImage.addEventListener("click", function () {
      state.pendingImageTarget = null;
      ui.imageInput.click();
    });
  }

  if (ui.replaceImage && ui.imageInput) {
    ui.replaceImage.addEventListener("click", function () {
      if (!state.selectedKey || !state.elements[state.selectedKey] || state.elements[state.selectedKey].type !== "imagen") {
        return;
      }
      state.pendingImageTarget = state.selectedKey;
      ui.imageInput.click();
    });
  }

  if (ui.imageInput) {
    ui.imageInput.addEventListener("change", function () {
      const file = ui.imageInput.files && ui.imageInput.files[0];
      uploadSelectedImage(file, state.pendingImageTarget);
    });
  }

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
    setFeedback("Se restauró el estado guardado más reciente del editor.", "neutral");
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
        notify(payload.error || "No se pudo guardar el diseño.", "error");
        setFeedback(payload.error || "No se pudo guardar el diseño.", "error");
        return;
      }

      state.elements = payload.elementos ? JSON.parse(JSON.stringify(payload.elementos)) : state.elements;
      state.pristine = JSON.parse(JSON.stringify(state.elements));
      renderCanvas();
      renderLayerPanel();
      syncSidebar();
    } catch (error) {
      notify("Ocurrió un error al guardar el diseño.", "error");
      setFeedback("Ocurrió un error al guardar el diseño.", "error");
    } finally {
      ui.save.disabled = false;
      ui.save.textContent = originalLabel;
    }
  });

  renderCanvas();
  renderLayerPanel();
  setActiveSidebarTab("layers");
  const firstKey = Object.keys(state.elements).find(function (key) {
    return key !== "fondo_diploma";
  });
  if (firstKey) {
    selectElement(firstKey);
  } else {
    syncSidebar();
  }
})();
