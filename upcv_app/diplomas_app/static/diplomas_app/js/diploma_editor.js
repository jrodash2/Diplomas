(function () {
  const payloadNode = document.getElementById("diplomaDesignDefinition");
  const canvas = document.getElementById("diplomaEditorCanvas");
  if (!payloadNode || !canvas) {
    return;
  }

  const SCALE = 0.28;
  const definition = JSON.parse(payloadNode.textContent || "{}");

  function hydrateElementsFromDom() {
    const hydrated = {};
    canvas.querySelectorAll(".diploma-editor-element").forEach(function (node) {
      const style = window.getComputedStyle(node);
      const key = node.dataset.key;
      if (!key) {
        return;
      }
      hydrated[key] = {
        key,
        label: node.dataset.label || key,
        type: node.dataset.type || "texto",
        visible: node.dataset.visible !== "false",
        x: parseFloat(node.style.left || 0),
        y: parseFloat(node.style.top || 0),
        width: parseFloat(node.style.width || 200),
        height: parseFloat(node.style.height || 80),
        font_size: parseFloat(node.dataset.fontSize || node.style.fontSize || 24),
        color: node.dataset.color || style.color || "#111827",
        align: node.dataset.align || style.textAlign || "center",
        z_index: parseInt(node.dataset.zIndex || style.zIndex || 1, 10),
        token: node.dataset.token || "",
        texto: node.dataset.texto || "",
        image_url: node.dataset.imageUrl || "",
      };
    });
    return hydrated;
  }

  const initialElements = definition.elements && Object.keys(definition.elements).length
    ? definition.elements
    : hydrateElementsFromDom();

  const state = {
    canvasWidth: Number(canvas.dataset.canvasWidth || 3508),
    canvasHeight: Number(canvas.dataset.canvasHeight || 2480),
    saveUrl: canvas.dataset.saveUrl,
    elements: initialElements,
    selectedKey: null,
    drag: null,
    pristine: JSON.parse(JSON.stringify(initialElements)),
  };

  const ui = {
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
    const match = document.cookie.match(/(^|;)\s*csrftoken=([^;]+)/);
    return match ? decodeURIComponent(match[2]) : "";
  }

  function clamp(value, min, max) {
    const numeric = Number(value);
    if (Number.isNaN(numeric)) {
      return min;
    }
    return Math.min(Math.max(numeric, min), max);
  }

  function normalizeElement(element) {
    const width = clamp(element.width, 20, state.canvasWidth);
    const height = clamp(element.height, 20, state.canvasHeight);
    element.width = width;
    element.height = height;
    element.x = clamp(element.x, 0, Math.max(state.canvasWidth - width, 0));
    element.y = clamp(element.y, 0, Math.max(state.canvasHeight - height, 0));
    element.font_size = clamp(element.font_size || 24, 8, 300);
    element.z_index = clamp(element.z_index || 1, 0, 9999);
    element.align = element.align || "center";
    element.color = element.color || "#111827";
    element.visible = element.visible !== false;
  }

  function previewText(element) {
    return element.texto || element.token || element.label || element.key;
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
    const elements = Object.values(state.elements)
      .sort((left, right) => left.z_index - right.z_index)
      .map((element) => {
        normalizeElement(element);
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

    canvas.style.backgroundImage = state.elements.fondo_diploma && state.elements.fondo_diploma.image_url
      ? `url("${state.elements.fondo_diploma.image_url}")`
      : "none";
    canvas.innerHTML = elements;
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

    normalizeElement(element);
    renderCanvas();
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
      key,
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

    const deltaX = (event.clientX - state.drag.startX) / SCALE;
    const deltaY = (event.clientY - state.drag.startY) / SCALE;
    element.x = state.drag.originX + deltaX;
    element.y = state.drag.originY + deltaY;
    normalizeElement(element);
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

  [
    ui.texto,
    ui.x,
    ui.y,
    ui.width,
    ui.height,
    ui.fontSize,
    ui.color,
    ui.align,
    ui.zIndex,
    ui.visible,
  ].forEach(function (input) {
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
      : Object.keys(state.elements)[0];
    renderCanvas();
    if (availableKey) {
      selectElement(availableKey);
    } else {
      syncSidebar();
    }
  });

  ui.save.addEventListener("click", async function () {
    const response = await fetch(state.saveUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: JSON.stringify({ elements: state.elements }),
    });
    const payload = await response.json();
    if (!response.ok || !payload.success) {
      window.alert(payload.error || "No se pudo guardar el diseño.");
      return;
    }
    state.elements = payload.definition.elements || state.elements;
    state.pristine = JSON.parse(JSON.stringify(state.elements));
    renderCanvas();
    syncSidebar();
    window.alert("Diseño guardado correctamente.");
  });

  renderCanvas();
  const firstKey = Object.keys(state.elements).find(function (key) {
    return key !== "fondo_diploma";
  });
  if (firstKey) {
    selectElement(firstKey);
  } else {
    syncSidebar();
  }
})();
