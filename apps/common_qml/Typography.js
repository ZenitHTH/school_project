.pragma library

var baseSizes = new Map();
var baseHeights = new Map();
var origFamilies = new Map();
var defaultFamily = "";
var currentConfig = { family: "", factor: 1.0 };

function extractBaselineSize(obj, factor) {
    var raw = obj.font.pixelSize > 0 ? obj.font.pixelSize : 14;
    var safeFactor = (factor && factor > 0) ? factor : 1.0;
    return safeFactor !== 1.0 ? Math.round(raw / safeFactor) : raw;
}

function recordBaseHeight(obj, factor) {
    if (obj.implicitHeight === undefined || baseHeights.has(obj) || obj.implicitHeight <= 0) return;
    var isEligible = (obj.background !== undefined || obj.contentItem !== undefined || obj.placeholderText !== undefined);
    if (!isEligible) return;
    var safeFactor = (factor && factor > 0) ? factor : 1.0;
    var baseH = safeFactor !== 1.0 ? Math.round(obj.implicitHeight / safeFactor) : obj.implicitHeight;
    baseHeights.set(obj, baseH);
}

function recordDefaults(obj) {
    if (!obj || !obj.font) return;
    var currentFactor = (currentConfig && currentConfig.factor) ? currentConfig.factor : 1.0;
    if (!baseSizes.has(obj)) {
        baseSizes.set(obj, extractBaselineSize(obj, currentFactor));
    }
    if (!origFamilies.has(obj)) {
        origFamilies.set(obj, obj.font.family || "");
    }
    if (!defaultFamily && obj.font.family && obj.font.family !== "monospace") {
        defaultFamily = obj.font.family;
    }
    recordBaseHeight(obj, currentFactor);
}

function resolveTargetFamily(obj, configFamily) {
    var orig = origFamilies.get(obj);
    if (orig === "monospace") return "monospace";
    if (configFamily) return configFamily;
    return orig || defaultFamily;
}

function applyHeightScale(obj, factor) {
    if (!baseHeights.has(obj)) return;
    try {
        var baseH = baseHeights.get(obj);
        obj.implicitHeight = Math.max(baseH, Math.round(baseH * factor));
    } catch (e) {}
}

function applyToNode(obj, config) {
    if (!obj || obj.font === undefined) return;
    recordDefaults(obj);
    obj.font.family = resolveTargetFamily(obj, config.family);
    var base = baseSizes.get(obj) || 14;
    obj.font.pixelSize = Math.max(8, Math.round(base * config.factor));
    applyHeightScale(obj, config.factor);
}

function visitProps(obj, ctx) {
    var props = ["contentItem", "header", "footer", "background"];
    for (var i = 0; i < props.length; i++) {
        var p = props[i];
        if (obj[p] && typeof obj[p] === "object") traverseNode(obj[p], ctx);
    }
}

function visitList(list, ctx) {
    if (!list || !list.length) return;
    for (var i = 0; i < list.length; i++) traverseNode(list[i], ctx);
}

function traverseNode(obj, ctx) {
    if (!obj || obj === ctx.skipNode || ctx.visited.has(obj)) return;
    ctx.visited.add(obj);
    applyToNode(obj, ctx.config);
    visitProps(obj, ctx);
    visitList(obj.children, ctx);
    visitList(obj.data, ctx);
    visitList(obj.resources, ctx);
    visitList(obj.contentChildren, ctx);
    visitList(obj.contentData, ctx);
}

function applyToTree(root, config, skipNode) {
    if (!root) return;
    if (config) currentConfig = config;
    var ctx = { config: currentConfig, skipNode: skipNode, visited: new Set() };
    traverseNode(root, ctx);
}

function applyToItem(item) {
    if (!item || !currentConfig) return;
    traverseNode(item, { config: currentConfig, skipNode: null, visited: new Set() });
}

function scale(basePx) {
    var f = (currentConfig && currentConfig.factor) ? currentConfig.factor : 1.0;
    return Math.max(8, Math.round(basePx * f));
}
