#!/usr/bin/env python3
# NOTA: copia del generar_web.py del sistema legislativo, usada acá solo como biblioteca (agenda, OD, sanciones, cruces).
# Lee SIEMPRE los datos propios de este repo (data/). No se conecta con el repo de Mariano.
"""
generar_web.py — Genera index.html (Fase 2 · sección Proyectos Ingresados)
==========================================================================
Lee data/proyectos.json y construye una web autosuficiente (datos embebidos
como `var DATA = [...]`, sin fetch en runtime) con:

  Navegación principal (4 pestañas):
    Proyectos (activa) · Comisiones · Agenda · Ayuda Memoria (placeholders)

  Dentro de Proyectos (3 sub-pestañas):
    Dashboard · Tabla dinámica · Buscador

Sistema de diseño idéntico al repo anterior (Proyectos-ingresados): Poppins,
azul institucional #1B5EA2, vanilla JS, mobile-first.
"""

import json
import os
import re
import unicodedata
import urllib.request
from datetime import datetime, timezone, timedelta

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "data")
INDEX = os.path.join(REPO_ROOT, "index.html")

TIPOS = {
    "PL": "Proyecto de Ley",
    "PD": "Proyecto de Declaración",
    "PC": "Proyecto de Comunicación",
    "PR": "Proyecto de Resolución",
    "CA": "Com. de Auditoría",
    "AC": "Acuerdo",
    "CV": "Com. Varias",
}

# ── Estilos ───────────────────────────────────────────────────────────────────

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Poppins',Calibri,sans-serif;background:#F5F7FA;color:#4A4A4A;font-size:15px;line-height:1.5}

/* ── Topbar: header + navegación principal (sticky en bloque) ──────────── */
.topbar{position:sticky;top:0;z-index:100}
.header{background:#1B5EA2;padding:12px 16px;border-bottom:2px solid #0d3f73}
.header-row{display:flex;justify-content:space-between;align-items:center;gap:8px;flex-wrap:wrap}
.header-inst{font-size:10px;font-weight:600;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:2px}
.header-dep{font-size:10px;font-weight:700;color:rgba(255,255,255,0.82);text-transform:uppercase;letter-spacing:2px}
.header-title{font-size:19px;font-weight:700;color:#fff;margin-top:5px}
.header-sub{font-size:11px;color:rgba(255,255,255,0.8);margin-top:1px}

.main-nav{display:flex;background:#0d3f73;padding:0 8px;gap:2px;overflow-x:auto}
.mtab-btn{padding:11px 20px;background:transparent;border:none;color:rgba(255,255,255,0.55);font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;border-bottom:3px solid transparent;transition:all .2s;text-transform:uppercase;letter-spacing:1px;white-space:nowrap}
.mtab-btn.active{color:#fff;border-bottom-color:#fff}
.mtab-btn:hover{color:rgba(255,255,255,0.85)}
.mtab-content{display:none}
.mtab-content.active{display:block}

/* ── Sub-navegación dentro de Proyectos ───────────────────────────────── */
.sub-nav,.am-sub-nav{display:flex;background:#fff;border-bottom:1px solid #D6E4F0;padding:0 12px;gap:4px;overflow-x:auto;box-shadow:0 1px 3px rgba(0,0,0,0.04)}
.sub-btn,.am-sub-btn{padding:10px 18px;background:transparent;border:none;color:#888;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;border-bottom:3px solid transparent;transition:all .2s;white-space:nowrap}
.sub-btn.active,.am-sub-btn.active{color:#1B5EA2;border-bottom-color:#1B5EA2}
.sub-btn:hover,.am-sub-btn:hover{color:#2E75B6}
.sub-content,.am-sub-content{display:none}
.sub-content.active,.am-sub-content.active{display:block}

/* ── Placeholders ─────────────────────────────────────────────────────── */
.placeholder{text-align:center;padding:80px 20px;color:#9aacbd}
.placeholder-icon{font-size:42px;margin-bottom:14px;opacity:.5}
.placeholder h3{color:#2E75B6;font-size:18px;margin-bottom:6px;font-weight:600}
.placeholder p{font-size:13px;color:#9aacbd}

/* ── Bloques de sección ───────────────────────────────────────────────── */
.section-block{background:#fff;margin:12px;border-radius:10px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,0.08)}
.section-header{background:#1B5EA2;padding:10px 16px;display:flex;justify-content:space-between;align-items:center}
.section-header h2{font-size:11px;font-weight:700;color:#fff;text-transform:uppercase;letter-spacing:1.5px}
.section-hint{font-size:10px;color:rgba(255,255,255,0.65)}
.section-body{padding:16px}

/* ── Dashboard de análisis ────────────────────────────────────────────── */
.dash-toolbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 auto 14px;max-width:1500px}
.dash-anio-label{font-size:10px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:1px;margin-right:2px}
.dash-total{margin-left:auto;font-size:12px;color:#888}
.dash-total strong{color:#1B5EA2;font-size:16px}
.dash-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;max-width:1500px;margin:0 auto;align-items:start}
.dash-grid .span6{grid-column:1 / -1}
.dash-grid .span3{grid-column:span 3}
.dash-grid .span2{grid-column:span 2}
@media(max-width:1100px){.dash-grid .span2{grid-column:span 3}}
@media(max-width:900px){.dash-grid{grid-template-columns:1fr}.dash-grid .span6,.dash-grid .span3,.dash-grid .span2{grid-column:auto}}
.dash-anio-btn{padding:8px 20px;border-radius:8px;border:2px solid #1B5EA2;background:#fff;color:#1B5EA2;font-family:inherit;font-size:14px;font-weight:700;cursor:pointer;transition:all .15s}
.dash-anio-btn.on{background:#1B5EA2;color:#fff;box-shadow:0 2px 8px rgba(27,94,162,0.3)}
.dash-anio-btn:hover{background:#EAF0FA}
.dash-anio-btn.on:hover{background:#2E75B6}
.treemap-breadcrumb{font-size:12px;color:#1B5EA2;margin-bottom:8px;font-weight:600}
.treemap-breadcrumb a{color:#2E75B6;cursor:pointer;text-decoration:underline}
.treemap-breadcrumb .curr{color:#0d3f73}
.viz-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.06);padding:14px}
.viz-head{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px;flex-wrap:wrap}
.viz-title{font-size:12px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:.8px}
.viz-svg{width:100%;height:auto;display:block;overflow:visible}
.viz-legend{display:flex;flex-wrap:wrap;gap:7px 14px;margin-top:10px}
.legend-item{display:flex;align-items:center;gap:5px;font-size:11px;color:#4A4A4A}
.legend-swatch{width:11px;height:11px;border-radius:3px;flex-shrink:0}
.viz-toggle{display:flex;gap:4px}
.viz-toggle button{padding:4px 12px;border-radius:14px;border:1.5px solid #D6E4F0;background:#fff;font-family:inherit;font-size:11px;color:#4A4A4A;cursor:pointer;transition:all .15s}
.viz-toggle button.on{background:#1B5EA2;border-color:#1B5EA2;color:#fff;font-weight:600}
.viz-empty{font-size:12px;color:#aaa;text-align:center;padding:30px 10px}
.dash-cross{display:none}
.dash-cross.active{display:inline-flex;align-items:center;gap:6px;cursor:pointer;background:#EAF0FA;color:#1B5EA2;border:1px solid #c8daf0;border-radius:14px;padding:4px 12px;font-size:11px;font-weight:600}
.dash-cross.active:hover{background:#D6E4F0}
.legend-item.clk{cursor:pointer}
.legend-item.clk:hover{text-decoration:underline}
.topcom-row.clk{cursor:pointer}
.topcom-row.clk:hover{background:#F0F4FA}
/* SVG text helpers */
.viz-axis{font-size:10px;fill:#999}
.viz-gridline{stroke:#EEF2F8;stroke-width:1}
.hm-label{font-size:10px;fill:#4A4A4A}
/* tooltip flotante compartido */
.dash-tooltip{position:fixed;pointer-events:none;background:#0d3f73;color:#fff;font-size:11px;line-height:1.5;padding:7px 10px;border-radius:7px;box-shadow:0 4px 14px rgba(0,0,0,0.28);z-index:300;opacity:0;transition:opacity .1s;max-width:260px}
.dash-tooltip.show{opacity:1}
.dash-tt-title{font-weight:700;margin-bottom:4px;border-bottom:1px solid rgba(255,255,255,0.25);padding-bottom:3px}
.dash-tt-row{display:flex;align-items:center;gap:6px;white-space:nowrap}
.dash-tt-dot{width:8px;height:8px;border-radius:2px;flex-shrink:0}
.dash-tt-row .v{margin-left:auto;font-weight:700;padding-left:10px}
/* top comisiones + sparkline */
.topcom-row{display:flex;align-items:center;gap:10px;padding:7px 2px;border-bottom:1px solid #EEF2F8}
.topcom-row:last-child{border-bottom:none}
.topcom-rank{font-size:11px;font-weight:700;color:#9aacbd;width:18px;text-align:right;flex-shrink:0}
.topcom-name{font-size:12px;color:#4A4A4A;flex:1;line-height:1.25}
.topcom-count{font-size:14px;font-weight:700;color:#1B5EA2;width:36px;text-align:right;flex-shrink:0}
.topcom-spark{width:92px;height:26px;flex-shrink:0}

/* ── Ranking bloques × tipo (heatmap, reusa estilo de la ex tabla dinámica) ── */
.pivot-scroll{overflow:auto;max-height:calc(100vh - 250px);border:1px solid #D6E4F0;border-radius:10px;background:#fff}
.pivot-table{border-collapse:separate;border-spacing:0;font-size:12px;width:100%}
.pivot-table th,.pivot-table td{border-right:1px solid #EEF2F8;border-bottom:1px solid #EEF2F8;padding:6px 10px;text-align:center;white-space:nowrap}
.pivot-table thead th{position:sticky;top:0;background:#1B5EA2;color:#fff;font-weight:600;font-size:11px;z-index:2}
.pivot-table .pv-corner{position:sticky;left:0;top:0;z-index:3;background:#0d3f73;text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.5px}
.pivot-table .pv-rowhead{position:sticky;left:0;background:#F5F8FC;color:#1B5EA2;font-weight:600;text-align:left;z-index:1;max-width:260px;overflow:hidden;text-overflow:ellipsis}
.pv-cell{color:#4A4A4A;transition:outline .1s}
.pv-click{cursor:pointer}
.pv-click:hover{outline:2px solid #2E75B6;outline-offset:-2px}
.pv-empty{color:#cfd8e3}
.pv-tot{font-weight:700;background:#EAF0FA;color:#1B5EA2}
.pivot-table .pv-totrow th,.pivot-table .pv-totrow td{background:#D6E4F0;border-top:2px solid #1B5EA2}
.pv-grand{font-weight:700;background:#1B5EA2!important;color:#fff!important}

/* ── Buscador: filtros arriba + grid de resultados ────────────────────── */
.detalle-layout{padding:12px}
.filters-top{background:#fff;border-radius:10px;box-shadow:0 1px 4px rgba(0,0,0,0.08);padding:14px 16px;margin-bottom:14px}
.filters-primary{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start}
.filters-primary .search-box{flex:2 1 240px;margin-bottom:0}
.filters-primary .select-wrapper{flex:1 1 170px;margin-bottom:0}
.checkbox-filter{display:flex;align-items:center;gap:7px;padding:8px 14px;border:1.5px solid #D6E4F0;border-radius:8px;font-size:12px;color:#4A4A4A;cursor:pointer;white-space:nowrap;flex:0 0 auto;user-select:none}
.checkbox-filter:has(input:checked){border-color:#1B5EA2;background:#EAF0FA;color:#1B5EA2;font-weight:600}
.checkbox-filter input{cursor:pointer;accent-color:#1B5EA2}
.filters-more{margin-top:10px;border-top:1px dashed #D6E4F0;padding-top:10px}
.filters-more summary{cursor:pointer;font-size:11px;font-weight:700;color:#1B5EA2;list-style:none;display:inline-flex;align-items:center;gap:6px;user-select:none}
.filters-more summary::-webkit-details-marker{display:none}
.filters-more summary:before{content:'▸';font-size:10px;display:inline-block;transition:transform .15s}
.filters-more[open] summary:before{transform:rotate(90deg)}
.filters-more-count{background:#1B5EA2;color:#fff;font-size:10px;font-weight:700;border-radius:10px;padding:1px 7px}
.filters-more-body{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px}
.filter-group{min-width:170px;flex:1}
.filter-group .filter-label{margin-top:0}
.active-chips{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px}
.active-chip{display:inline-flex;align-items:center;gap:5px;background:#EAF0FA;color:#1B5EA2;border:1px solid #c8daf0;border-radius:14px;padding:4px 6px 4px 11px;font-size:11px;font-weight:600}
.active-chip button{background:none;border:none;color:#1B5EA2;cursor:pointer;font-size:13px;line-height:1;padding:0 2px;font-weight:700}
.results-panel{min-width:0}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
/* Aísla el layout de la grilla de resultados: sin esto, cualquier cambio de
   DOM en OTRA sección de la página (ej. un modal) fuerza al navegador a
   recalcular también el layout de esta grilla. Sólo un límite de layout. */
#list{contain:content}
.pagination{display:flex;align-items:center;justify-content:center;gap:6px;flex-wrap:wrap;margin:18px 0 8px}
.page-btn{min-width:32px;height:32px;padding:0 8px;border-radius:7px;border:1.5px solid #D6E4F0;background:#fff;color:#4A4A4A;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer}
.page-btn.on{background:#1B5EA2;border-color:#1B5EA2;color:#fff}
.page-btn:disabled{opacity:.4;cursor:default}
.page-ellipsis{color:#aaa;font-size:12px;padding:0 3px}
@media(max-width:900px){
  .filters-primary{flex-direction:column}
  .filters-primary .select-wrapper,.filters-primary .search-box{flex-basis:auto;width:100%}
  .filters-more-body{flex-direction:column}
  .cards-grid{grid-template-columns:1fr}
}

.search-box{width:100%;padding:10px 12px;border:1.5px solid #D6E4F0;border-radius:8px;font-family:inherit;font-size:13px;color:#4A4A4A;outline:none;margin-bottom:10px;background:#fff}
.search-box:focus{border-color:#1B5EA2}
.filter-label{font-size:10px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:1px;margin-bottom:5px;margin-top:10px}
.filter-label:first-child{margin-top:0}
.filter-row{display:flex;gap:5px;flex-wrap:wrap;margin-bottom:4px}
.chip{padding:6px 11px;border-radius:20px;border:1.5px solid #D6E4F0;background:#fff;font-family:inherit;font-size:11px;color:#4A4A4A;cursor:pointer;transition:all .15s;white-space:nowrap;-webkit-appearance:none;line-height:1.2}
.chip.on{background:#1B5EA2;border-color:#1B5EA2;color:#fff;font-weight:600}
.results-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;flex-wrap:wrap;gap:8px}
.results-count{font-size:12px;color:#888}
.btn-export{padding:7px 14px;border-radius:8px;border:1.5px solid #1B5EA2;background:#fff;color:#1B5EA2;font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-export:hover{background:#1B5EA2;color:#fff}
/* ── Ficha de reunión (temario + checklist de integrantes, imprimible) ── */
.ficha-overlay{position:fixed;inset:0;background:#fff;z-index:300;overflow-y:auto;padding:20px 24px 60px}
body.ficha-activa>*:not(.ficha-overlay){display:none!important}
.ficha-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-bottom:18px;padding-bottom:14px;border-bottom:1px dashed #D6E4F0}
.ficha-toolbar button{padding:9px 16px;border-radius:8px;font-family:inherit;font-size:13px;font-weight:600;cursor:pointer;border:1.5px solid #1B5EA2}
.ficha-toolbar .btn-brass{background:#1B5EA2;color:#fff}
.ficha-toolbar .btn-neutral{background:#fff;color:#1B5EA2}
.ficha-buscar{padding:8px 12px;border-radius:8px;border:1.5px solid #D6E4F0;font-family:inherit;font-size:13px;min-width:200px;flex:1;max-width:280px}
.ficha-hint{font-size:11px;color:#9aa1a6;flex-basis:100%}
.ficha-view h1{font-size:19px;color:#1B5EA2;margin:0 0 14px;text-transform:uppercase;letter-spacing:.03em}
.ficha-plenaria-banner{display:inline-block;background:#0d3f73;color:#fff;font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;padding:6px 14px;border-radius:20px;margin:-6px 0 14px}
.ficha-meta{font-size:13px;color:#4A4A4A;line-height:1.7;margin-bottom:18px}
.ficha-meta strong{color:#1B5EA2}
.ficha-section-label{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:#9aa1a6;margin:18px 0 8px;padding-top:10px;border-top:1px solid #EEF3F8}
.ficha-temario{font-size:13px;color:#4A4A4A;line-height:1.55}
.ficha-tema{margin-bottom:8px}
.ficha-tema strong{color:#1B5EA2}
.ficha-comision{margin-bottom:22px}
.ficha-comision-head{display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px;background:#1B5EA2;color:#fff;padding:8px 12px;border-radius:8px 8px 0 0;break-after:avoid;break-inside:avoid}
.ficha-comision-head h3{font-size:14px;margin:0;font-weight:700}
.ficha-comision-meta{font-size:11px;color:#D6E4F0}
.ficha-table{width:100%;border-collapse:collapse;font-size:12.5px;break-inside:avoid}
.ficha-table thead{display:table-header-group}
.ficha-table th{text-align:left;font-size:10px;text-transform:uppercase;letter-spacing:.04em;color:#9aa1a6;padding:6px 8px;border-bottom:1.5px solid #D6E4F0;background:#F5F8FC}
.ficha-table td{padding:6px 8px;border-bottom:1px solid #EEF3F8;vertical-align:middle}
.ficha-table tr{break-inside:avoid}
.ficha-check{width:26px}
.ficha-checkbox{display:inline-block;width:14px;height:14px;border:1.5px solid #9aa1a6;border-radius:3px}
.ficha-apellido{font-weight:600;color:#4A4A4A;white-space:nowrap}
.ficha-apellido .senador-avatar{margin-right:6px}
.ficha-cargo{font-size:11px;color:#1B5EA2;font-weight:600;white-space:nowrap}
.ficha-provincia{width:110px;max-width:110px;font-size:10.5px;color:#4A4A4A;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ficha-dpp{font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:10px;background:#FFF3CD;color:#7A5200;white-space:nowrap}
.ficha-row-vacante{opacity:.6}
.ficha-vacante{font-style:italic;color:#9aa1a6}
.ficha-row-repetido{background-image:repeating-linear-gradient(45deg,rgba(27,94,162,0.07),rgba(27,94,162,0.07) 4px,transparent 4px,transparent 9px)}
.ficha-repetido-marca{color:#1B5EA2;font-weight:700}
.ficha-repetido-nota{font-size:10.5px;color:#9aa1a6;padding:6px 8px;font-style:italic}
.ficha-expositores{margin-top:10px;padding-top:8px;border-top:1px dashed #EEF3F8;font-size:12.5px}
.ficha-row-clickable{cursor:pointer;user-select:none}
.ficha-row-clickable:hover{background:#F5F8FC}
.ficha-checked .ficha-checkbox{background:#1B5EA2;border-color:#1B5EA2;position:relative}
.ficha-checked .ficha-checkbox::after{content:'';position:absolute;left:4px;top:1px;width:4px;height:8px;border:solid #fff;border-width:0 2px 2px 0;transform:rotate(45deg)}
.ficha-checked .ficha-apellido{color:#1B5EA2}
.ficha-presentes-count{font-size:11px;color:#D6E4F0;font-weight:600}
.ficha-quorum-ok{color:#8DE38F}
@media print{
  .no-print{display:none!important}
  .ficha-overlay{position:static;padding:0}
  .ficha-overlay *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
@media (max-width:640px){
  .ficha-overlay{padding:14px}
  .ficha-comision-head{flex-direction:column;align-items:flex-start}
  .ficha-table{display:block;overflow-x:auto;white-space:nowrap}
}
.select-wrapper{position:relative;display:block;margin-bottom:4px}
.filter-select{width:100%;padding:8px 32px 8px 11px;border:1.5px solid #D6E4F0;border-radius:8px;font-family:inherit;font-size:12px;color:#4A4A4A;background:#fff;outline:none;cursor:pointer;-webkit-appearance:none;appearance:none;transition:border-color .15s}
.filter-select:focus,.filter-select.on{border-color:#1B5EA2;background:#EAF0FA;color:#1B5EA2;font-weight:600}
.select-arrow{position:absolute;right:10px;top:50%;transform:translateY(-50%);pointer-events:none;color:#888;font-size:12px}
.date-range{display:flex;flex-direction:column;gap:5px;margin-bottom:4px}
.date-input{width:100%;padding:7px 10px;border:1.5px solid #D6E4F0;border-radius:8px;font-family:inherit;font-size:12px;color:#4A4A4A;background:#fff;outline:none}
.date-input:focus{border-color:#1B5EA2}
.date-sep{font-size:10px;color:#888;font-weight:600;text-transform:uppercase;letter-spacing:1px}

.card{background:#fff;border-radius:10px;margin-bottom:0;overflow:hidden;border:1px solid #D6E4F0;box-shadow:0 1px 3px rgba(0,0,0,0.05);cursor:pointer;transition:box-shadow .15s,border-color .15s;display:flex;flex-direction:column}
.card:hover{box-shadow:0 3px 12px rgba(27,94,162,0.16);border-color:#9db8d8}
.card-exp{display:flex;align-items:center;justify-content:space-between;padding:8px 12px 6px;border-bottom:1px solid #EEF2F8;background:#F5F8FC}
.exp-id{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.exp-badge{font-size:11px;font-weight:700;padding:4px 9px;border-radius:4px;flex-shrink:0;letter-spacing:.5px}
.exp-nro{font-size:13px;font-weight:700;color:#1B5EA2}
.exp-link{font-size:11px;color:#2E75B6;text-decoration:none;font-weight:600;border:1px solid #2E75B6;padding:3px 9px;border-radius:12px;white-space:nowrap;transition:all .15s}
.exp-link:hover{background:#2E75B6;color:#fff}
.exp-fecha{font-size:11px;color:#888}
.card-body{padding:10px 12px 4px;flex:1}
.extracto{font-size:12.5px;font-weight:500;color:#3a3a3a;line-height:1.35;margin-bottom:8px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card-meta{display:flex;flex-direction:column;gap:4px;padding-bottom:8px}
.meta-row{display:flex;gap:6px;align-items:flex-start;flex-wrap:wrap}
.meta-bold{font-size:13px;font-weight:600;color:#4A4A4A}
.btag{display:inline-block;font-size:11px;font-weight:600;padding:3px 8px;border-radius:4px;margin-right:4px;margin-bottom:3px}
.ctag{display:inline-block;font-size:11px;padding:3px 8px;border-radius:4px;margin-right:4px;margin-bottom:3px;background:#EAF0FA;color:#1B5EA2;border:1px solid #c8daf0}
.no-results{text-align:center;padding:48px 16px;color:#aaa;font-size:14px}
.footer{text-align:center;padding:20px 16px;font-size:11px;color:#aaa;font-style:italic}

/* ── Comisiones ───────────────────────────────────────────────────────── */
.com-nivel{display:none}
.com-nivel.active{display:block}
.stats-bar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:14px}
.stat-card{flex:1;min-width:130px;background:#fff;border:1.5px solid #D6E4F0;border-radius:10px;padding:12px 16px;cursor:pointer;transition:all .15s;text-align:center}
.stat-card:hover{border-color:#2E75B6}
.stat-card.active{background:#1B5EA2;border-color:#1B5EA2}
.stat-card.active .stat-num,.stat-card.active .stat-label{color:#fff}
.stat-num{font-size:24px;font-weight:800;color:#1B5EA2;line-height:1.1}
.stat-label{font-size:10.5px;font-weight:600;color:#888;text-transform:uppercase;letter-spacing:.5px;margin-top:3px}
.com-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:14px}
.senator-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:10px;margin-top:14px}
.senator-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:12px 14px}
.senator-name{font-size:13px;font-weight:700;color:#1B5EA2;margin-bottom:4px}
.senator-bloque-tag{display:inline-block;font-size:10px;padding:2px 8px;border-radius:10px;margin-bottom:8px;font-weight:600}
.senator-chips{display:flex;flex-wrap:wrap;gap:4px}
.senator-count{font-size:11px;color:#9CA3AF;margin-top:6px}
.cross-vacantes td,.cross-vacantes .blq-name{border-top:2px solid #D6E4F0;font-weight:700}
.com-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:14px 16px;cursor:pointer;transition:all .15s;box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;align-items:center;min-height:100%}
.com-card:nth-child(even){background:#F5F9FC}
.com-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px -12px rgba(27,94,162,0.35);border-color:#1B5EA2}
.com-card-nombre{font-size:14px;font-weight:700;color:#1B5EA2;line-height:1.3}
.btn-volver{padding:7px 14px;border-radius:8px;border:1.5px solid #fff;background:transparent;color:#fff;font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;transition:all .15s}
.btn-volver:hover{background:#fff;color:#1B5EA2}
.com-panel-title{font-size:11px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid #D6E4F0}
.com-sub-nav{display:flex;gap:4px;border-bottom:1px solid #D6E4F0;margin:16px 0 16px;overflow-x:auto}
.com-sub-btn{padding:10px 16px;background:transparent;border:none;color:#888;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;border-bottom:3px solid transparent;transition:all .2s;white-space:nowrap}
.com-sub-btn.active{color:#1B5EA2;border-bottom-color:#1B5EA2}
.com-sub-btn:hover{color:#2E75B6}
.com-sub-content{display:none}
.com-sub-content.active{display:block}
#com-integrantes-list{max-width:760px;margin:0 auto}
.member-row{display:flex;align-items:center;gap:8px;padding:8px 4px;border-bottom:1px solid #EEF2F8;flex-wrap:wrap}
.senador-avatar{border-radius:50%;object-fit:cover;flex-shrink:0;background:#EEF2F8;vertical-align:middle}
.member-row:last-child{border-bottom:none}
.bloque-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.member-name{font-size:13px;font-weight:600;color:#4A4A4A;flex:1;min-width:160px}
.rol-badge{font-size:9.5px;font-weight:700;padding:2px 7px;border-radius:10px;text-transform:uppercase;letter-spacing:.4px;white-space:nowrap;flex-shrink:0}
.member-row-vacante{opacity:.65}
.vacante-dot{border:1.5px dashed #b0bac5;background:transparent}
.vacante-label{font-style:italic;font-weight:500;color:#9aa1a6}
.rol-Presidente{background:#1B5EA2;color:#fff}
.rol-Vicepresidente{background:#D6E4F0;color:#1B5EA2}
.rol-Secretario{background:#EAF0FA;color:#2E75B6}
.rol-Vocal{background:#F5F7FA;color:#9aacbd}
.com-proy-cats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px}
.com-proy-cat-btn{padding:10px 16px;border-radius:8px;border:1.5px solid #D6E4F0;background:#fff;color:#4A4A4A;font-family:inherit;font-size:12.5px;font-weight:600;cursor:pointer;transition:all .15s}
.com-proy-cat-btn:hover{border-color:#1B5EA2;color:#1B5EA2}
.com-proy-cat-btn.active{background:#1B5EA2;border-color:#1B5EA2;color:#fff}
.com-proy-cat-btn .cnt{opacity:.75;font-weight:400}
.com-tratado-tag{font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;padding:2px 8px;border-radius:10px}
.com-tratado-tag.ok{background:#E8F5E9;color:#1B5E20}
.com-tratado-tag.pend{background:#FFF8E1;color:#F57F17}
.com-proximareunion{margin-top:16px;background:#D6E4F0;border-left:3px solid #2E75B6;border-radius:6px;padding:12px 16px;font-size:12.5px;color:#0d3f73;display:flex;flex-wrap:wrap;gap:6px 18px;align-items:center}
.com-proximareunion strong{color:#1B5EA2}
.com-empty{text-align:center;padding:40px 16px;color:#aaa;font-size:13px}
.dpp-badge{font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px;background:#FFF3CD;color:#7A5200;border:none;font-family:inherit;cursor:pointer;white-space:nowrap;flex-shrink:0;letter-spacing:.3px}
.dpp-badge:hover{background:#FFE9A8}
.dpp-modal-overlay{display:none;position:fixed;inset:0;background:rgba(13,63,115,0.45);z-index:400;align-items:center;justify-content:center;padding:16px}
.dpp-modal-overlay.open{display:flex}
.dpp-modal{background:#fff;border-radius:12px;max-width:480px;width:100%;max-height:70vh;display:flex;flex-direction:column;box-shadow:0 10px 40px rgba(0,0,0,0.3);overflow:hidden}
.dpp-modal-head{background:#1B5EA2;color:#fff;padding:12px 16px;font-size:13px;font-weight:600;display:flex;justify-content:space-between;align-items:center;gap:10px}
.dpp-modal-close{background:none;border:none;color:#fff;font-size:15px;cursor:pointer;padding:2px 6px;flex-shrink:0}
.dpp-modal-body{padding:14px 16px;overflow-y:auto}
.dpp-hist-entry{background:#D6E4F0;border-left:3px solid #2E75B6;border-radius:6px;padding:9px 12px;margin-bottom:8px}
.dpp-hist-entry:last-child{margin-bottom:0}
.dpp-hist-dpp{font-size:12px;font-weight:700;color:#1B5EA2}
.dpp-hist-fecha{font-size:10px;font-weight:400;color:#4A6A8A;margin-left:8px}
.dpp-hist-detalle{font-size:12px;color:#0d3f73;margin-top:2px}

/* ── Ficha de proyecto (modal) ─────────────────────────────────────────── */
.ficha-modal{max-width:640px;max-height:85vh}
.ficha-stepper{display:flex;align-items:flex-start;padding:18px 18px 6px;gap:0}
.step-node{flex:1;display:flex;flex-direction:column;align-items:center;text-align:center;position:relative}
.step-dot{width:22px;height:22px;border-radius:50%;background:#D6E4F0;color:#7d8a99;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;z-index:1}
.step-node.done .step-dot{background:#1B5EA2;color:#fff}
.step-node.final-sanc .step-dot{background:#1B5E20;color:#fff}
.step-node.final-arch .step-dot{background:#9CA3AF;color:#fff}
.step-node:not(:last-child):after{content:'';position:absolute;top:11px;left:calc(50% + 14px);right:calc(-50% + 14px);height:2px;background:#D6E4F0}
.step-node.done:not(:last-child):after{background:#1B5EA2}
.step-label{font-size:10px;color:#888;margin-top:6px;font-weight:600;line-height:1.3}
.step-node.done .step-label{color:#1B5EA2}
.step-node.final-sanc .step-label{color:#1B5E20}
.step-node.final-arch .step-label{color:#6B7280}
.step-sub{font-size:9.5px;color:#aaa;margin-top:1px}
.ficha-body{padding:8px 20px 20px}
.ficha-extracto{font-size:14px;font-weight:600;color:#2C2C2C;line-height:1.45;margin-bottom:14px}
.ficha-kv{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
.ficha-kv-row{display:flex;gap:10px;align-items:flex-start}
.ficha-kv-label{font-size:10px;font-weight:700;color:#888;text-transform:uppercase;letter-spacing:.5px;width:92px;flex-shrink:0;padding-top:2px}
.ficha-kv-val{font-size:12.5px;color:#4A4A4A;flex:1}
.ficha-links{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}

/* ── Proyección de votación (adaptado de comisiones-senado) ───────────── */
.proy-panel{margin-top:16px}
.proy-controls{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:16px 20px;margin-bottom:16px;display:flex;flex-wrap:wrap;gap:12px;align-items:flex-end}
.proy-control-group{display:flex;flex-direction:column;gap:4px}
.proy-control-group label{font-size:11px;font-weight:600;color:#1B5EA2;text-transform:uppercase;letter-spacing:.5px}
.proy-input{height:36px;padding:0 12px;border:1px solid #D6E4F0;border-radius:6px;font-family:inherit;font-size:13px;color:#4A4A4A;background:#F5F7FA;outline:none;min-width:260px}
.proy-input:focus{border-color:#1B5EA2}
.dictamen-banner{border-radius:10px;padding:14px 20px;margin-bottom:16px;display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;border-width:2px;border-style:solid}
.dictamen-banner.no-dictamen{background:#FEE2E2;border-color:#FCA5A5}
.dictamen-banner.hay-dictamen{background:#D1FAE5;border-color:#6EE7B7}
.dictamen-status{font-size:22px;font-weight:800;letter-spacing:1px}
.dictamen-banner.no-dictamen .dictamen-status{color:#991B1B}
.dictamen-banner.hay-dictamen .dictamen-status{color:#065F46}
.dictamen-counter{font-size:13px;font-weight:500;color:#4B5563}
.dictamen-counter span{font-weight:700}
.proy-actions{display:flex;gap:8px;margin-bottom:12px;align-items:center;flex-wrap:wrap}
.btn-reset-proy{height:36px;padding:0 14px;background:#F3F4F6;color:#4A4A4A;border:1px solid #D6E4F0;border-radius:6px;font-family:inherit;font-size:12px;font-weight:500;cursor:pointer;transition:background .15s}
.btn-reset-proy:hover{background:#E5E7EB}
.btn-pdf{display:flex;align-items:center;gap:6px;height:34px;padding:0 14px;background:#1B5EA2;color:#fff;border:none;border-radius:6px;font-family:inherit;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap;transition:background .15s}
.btn-pdf:hover{background:#2E75B6}
.proy-mayoria-label{font-size:12px;color:#6B7280;margin-left:auto}
.proy-bloque-panel{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:14px 20px;margin-bottom:14px;display:none}
.proy-bloque-panel-title{font-size:10px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:.8px;margin-bottom:10px}
.proy-bloque-row{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid #F1F5F9;flex-wrap:wrap}
.proy-bloque-row:last-child{border-bottom:none}
.proy-bloque-name{flex:1;min-width:160px;font-size:12px;font-weight:500;color:#4A4A4A;display:flex;align-items:center;gap:6px}
.bloque-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
.proy-vote-btns{display:flex;gap:4px;flex-wrap:wrap}
.vote-btn{padding:4px 10px;border:1px solid;border-radius:5px;font-family:inherit;font-size:11px;font-weight:600;cursor:pointer;transition:background .12s,color .12s}
.vote-btn.mayoria{border-color:#059669;color:#059669;background:#fff}
.vote-btn.mayoria.active{background:#D1FAE5;border-color:#059669;color:#065F46}
.vote-btn.mayoria_dis{border-color:#D97706;color:#D97706;background:#fff}
.vote-btn.mayoria_dis.active{background:#FEF3C7;border-color:#D97706;color:#92400E}
.vote-btn.minoria{border-color:#DC2626;color:#DC2626;background:#fff}
.vote-btn.minoria.active{background:#FEE2E2;border-color:#DC2626;color:#991B1B}
.vote-btn.sin{border-color:#9CA3AF;color:#6B7280;background:#fff}
.vote-btn.sin.active{background:#F3F4F6;border-color:#6B7280;color:#374151}
.proy-table-wrap{background:#fff;border:1px solid #D6E4F0;border-radius:10px;overflow:hidden;overflow-x:auto}
.proy-table{width:100%;border-collapse:collapse;font-size:13px}
.proy-table th{background:#1B5EA2;color:#fff;padding:9px 14px;text-align:left;font-weight:600;font-size:11px;text-transform:uppercase;letter-spacing:.3px;white-space:nowrap}
.proy-table td{padding:8px 14px;border-bottom:1px solid #F1F5F9;vertical-align:middle}
.proy-table tr:last-child td{border-bottom:none}
.proy-table tr:hover td{background:#F8FAFF}
.proy-empty{text-align:center;padding:40px;color:#9CA3AF;font-size:14px}
@media(max-width:700px){.proy-controls{padding:12px}.proy-input{min-width:100%}}

/* ── Representación por bloques ──────────────────────────────────────── */
.repr-titulo{font-size:11px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:1px;margin:18px 0 8px;padding-bottom:5px;border-bottom:1px solid #D6E4F0}
.repr-titulo:first-child{margin-top:0}
.repr-hint{font-size:11px;color:#888;margin-bottom:8px}
.repr-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;border:1px solid #D6E4F0;border-radius:10px}
table.repr-table{width:100%;border-collapse:collapse;font-size:12px}
table.repr-table th{background:#1B5EA2;color:#fff;padding:8px 12px;text-align:left;font-weight:600;font-size:11px;white-space:nowrap}
table.repr-table th.num,table.repr-table td.num{text-align:center}
table.repr-table td{padding:7px 12px;border-bottom:1px solid #EEF2F8;vertical-align:middle}
table.repr-table tr:last-child td{border-bottom:none}
table.repr-table tr:hover td{background:#F5F8FC}
.repr-bloque-cell{display:flex;align-items:center;gap:7px;white-space:nowrap}
.repr-dot{width:10px;height:10px;border-radius:50%;flex-shrink:0}
table.cross-table{border-collapse:collapse;font-size:11px}
table.cross-table th.blq-col{text-align:left;padding:8px 12px;background:#1B5EA2;color:#fff;white-space:nowrap;position:sticky;left:0;z-index:2;min-width:150px}
table.cross-table th.com-col{background:#1B5EA2;color:#fff;padding:0 3px 8px;width:30px;min-width:30px;max-width:30px;vertical-align:bottom;text-align:center}
table.cross-table th.com-col span{display:block;writing-mode:vertical-rl;transform:rotate(180deg);font-size:9.5px;font-weight:500;line-height:1;white-space:nowrap;max-height:110px;overflow:hidden}
table.cross-table td.blq-name{padding:6px 12px;white-space:nowrap;font-size:11px;font-weight:600;position:sticky;left:0;border-right:1px solid #EEF2F8}
table.cross-table td.val{text-align:center;padding:5px 3px;border-bottom:1px solid #EEF2F8;border-right:1px solid #EEF2F8;font-size:11.5px;width:30px}
table.cross-table tr:last-child td{border-bottom:none}

/* ── Agenda ───────────────────────────────────────────────────────────── */
.agenda-seccion-title{font-size:13px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:1px;margin:4px 12px 6px;padding-bottom:8px;border-bottom:2px solid #1B5EA2}
.agenda-seccion+.agenda-seccion{margin-top:8px}
.agenda-seccion-asesores{opacity:.92}
.agenda-seccion-asesores .agenda-seccion-title{color:#8a97a6;border-bottom-color:#D6E4F0;font-size:12px}
.agenda-seccion-hint{font-size:10px;color:#aaa;font-weight:400;text-transform:none;letter-spacing:0;margin-left:6px}
.agenda-grupo-title{font-size:11px;font-weight:700;color:#1B5EA2;text-transform:uppercase;letter-spacing:1px;margin:18px 12px 8px;padding-bottom:5px;border-bottom:1px solid #D6E4F0}
.agenda-seccion-asesores .agenda-grupo-title{color:#9aacbd}
.agenda-grupo-title:first-child{margin-top:0}
.agenda-grupo-count{color:#9aacbd;font-weight:600}
.agenda-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:12px 16px;margin:0 12px 10px;cursor:pointer;transition:all .15s;box-shadow:0 1px 3px rgba(0,0,0,0.05)}
.agenda-card:hover{border-color:#1B5EA2;box-shadow:0 2px 8px rgba(27,94,162,0.15)}
.agenda-card.agenda-pasada{opacity:.62}
.agenda-card-top{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.agenda-fecha{font-size:12px;font-weight:600;color:#4A4A4A}
.agenda-card-com{font-size:13.5px;font-weight:600;color:#2C2C2C;margin-bottom:4px;line-height:1.35}
.agenda-card-salon{font-size:11px;color:#888}
.agenda-pasada-tag{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#9aacbd;border:1px solid #D6E4F0;border-radius:10px;padding:1px 7px;margin-left:4px}
.agenda-detalle-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:6px}
.btn-copiar-link{margin-left:auto;padding:5px 12px;border-radius:20px;border:1.5px solid #D6E4F0;background:#fff;color:#1B5EA2;font-family:inherit;font-size:11px;font-weight:600;cursor:pointer}
.btn-copiar-link:hover{background:#EAF0FA}
.agenda-detalle-salon{font-size:12px;color:#888;margin-bottom:4px}
.temario-item{padding:10px 4px;border-bottom:1px solid #EEF2F8;font-size:13px;color:#4A4A4A;line-height:1.4}
.temario-item:last-child{border-bottom:none}
.temario-item.clk{cursor:pointer}
.temario-item.clk:hover{background:#F5F8FC}
.temario-num{display:inline-block;font-size:12px;font-weight:700;color:#1B5EA2;margin-right:8px}
.card-footer{padding:0 14px 12px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.reunion-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#D6E4F0;color:#1B5EA2}
.od-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#E8F4E8;color:#0F6E56;border:1px solid #5DCAA5;text-decoration:none}
.od-badge:hover{background:#dcefdc}
.pref-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#FFF8E1;color:#F57F17;border:1px solid #F9A825}
.sancionado-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#E8F5E9;color:#1B5E20;border:1px solid #4CAF50;text-decoration:none;cursor:pointer}
.sancionado-badge:hover{background:#dcefdc}
.sanc-ley-badge{display:inline-block;font-size:11px;font-weight:700;padding:4px 10px;border-radius:6px;background:#1B5E20;color:#fff}
.diputados-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#E3F2FD;color:#0D47A1;border:1px solid #1976D2}
.dadocuenta-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#E8F5E9;color:#1B5E20;border:1px solid #4CAF50}
.pendientecuenta-badge{display:inline-block;font-size:11px;font-weight:600;padding:4px 10px;border-radius:6px;background:#FFF8E1;color:#F57F17;border:1px solid #F9A825}
.sanc-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;align-items:start}
.od-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:14px 16px 12px;box-shadow:0 1px 3px rgba(0,0,0,0.05);display:flex;flex-direction:column;transition:all .15s}
.od-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px -12px rgba(27,94,162,0.35);border-color:#1B5EA2}
.od-card-top{display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:8px}
.od-nro{font-size:14px;font-weight:700;color:#1B5EA2;text-decoration:none}
.od-nro:hover{text-decoration:underline}
.od-tipo-tag{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;color:#9aacbd;border:1px solid #D6E4F0;border-radius:10px;padding:1px 7px}
.od-exp-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:2px}
.od-exp-link{font-size:12px;color:#2E75B6;text-decoration:none;font-weight:600}
.od-exp-link:hover{text-decoration:underline}
.od-exp-extracto{font-size:12.5px;color:#4A4A4A;line-height:1.44;margin:0 0 10px;flex:1;display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden}
.sanc-fecha{font-size:11px;color:#9aacbd}
.sanc-obs{font-size:12px;color:#4A4A4A;margin-top:2px}
.sanc-obs.ley{color:#1B5EA2;font-weight:700}
.sanc-card-bottom{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-top:auto;padding-top:8px;border-top:1px solid #EEF3F8}
.sanc-solicitante{font-size:11px;font-weight:600;color:#1B5EA2}
.agenda-badges{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.plenaria-badge{display:inline-block;font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:10px;background:#0d3f73;color:#fff}
.suspendida-badge{display:inline-block;font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:10px;background:#FEE2E2;color:#991B1B}
.agenda-card.agenda-suspendida{opacity:.75}
.editada-badge{display:inline-block;font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.5px;padding:2px 8px;border-radius:10px;background:#FBEADD;color:#C2650C}
.hora-vieja{text-decoration:line-through;color:#9aacbd;font-weight:400}
.hora-nueva{color:#C2650C;font-weight:700}
.agenda-nota{margin-top:8px;padding:8px 12px;background:#FBEADD;border-left:3px solid #C2650C;border-radius:6px;font-size:12.5px;color:#7A4A0F}
/* ── Agenda: hoy (vista por defecto) ──────────────────────────────────── */
.agenda-hoy-header{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.agenda-hoy-titulo{font-size:15px;font-weight:700;color:#1B5EA2}
/* ── Agenda: calendario ──────────────────────────────────────────────── */
.agenda-cal-controls{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px}
.cal-header{display:flex;align-items:center;justify-content:center;gap:18px;margin:4px 0 10px}
.cal-mes-label{font-size:15px;font-weight:700;color:#1B5EA2;min-width:170px;text-align:center}
.cal-nav{width:32px;height:32px;border-radius:50%;border:1px solid #D6E4F0;background:#fff;color:#1B5EA2;font-size:17px;line-height:1;cursor:pointer;transition:all .15s;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.cal-nav:hover:not(:disabled){background:#1B5EA2;color:#fff;border-color:#1B5EA2}
.cal-nav:disabled{opacity:.3;cursor:default}
.cal-dow-row{display:grid;grid-template-columns:repeat(5,1fr) 0.4fr 0.4fr;gap:4px;margin-bottom:4px}
.cal-dow{text-align:center;font-size:10.5px;font-weight:700;color:#9aacbd;text-transform:uppercase;letter-spacing:.5px;padding:4px 0}
.cal-dow.weekend{color:#c98a4b}
.cal-grid{display:grid;grid-template-columns:repeat(5,1fr) 0.4fr 0.4fr;gap:4px;margin-bottom:8px}
.cal-day{min-width:0;min-height:92px;border:1px solid #EEF2F8;border-radius:8px;padding:5px 5px 4px;background:#fff;display:flex;flex-direction:column;gap:3px;overflow:hidden}
.cal-day.weekend{background:#F7F5F0;padding:5px 2px 4px}
.cal-day.outside{background:#FAFBFC;opacity:.4}
.cal-day.has-items{cursor:pointer}
.cal-day.has-items:hover{border-color:#1B5EA2;box-shadow:0 2px 6px rgba(27,94,162,0.15)}
.cal-day.today .cal-day-num{background:#1B5EA2;color:#fff}
.cal-day-num{font-size:12px;font-weight:700;color:#4A4A4A;width:20px;height:20px;display:flex;align-items:center;justify-content:center;border-radius:50%;flex-shrink:0}
.cal-day-items{display:flex;flex-direction:column;gap:2px;min-width:0;overflow:hidden}
.cal-pill{display:block;width:100%;box-sizing:border-box;font-size:9.5px;font-weight:600;padding:1.5px 5px;border-radius:5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;line-height:1.5}
.cal-day.weekend .cal-pill{padding:1.5px 2px}
.cal-more{font-size:9px;color:#9aacbd;font-weight:600;padding-left:2px}
@media(max-width:700px){
  .cal-day{min-height:52px;padding:3px}
  .cal-day-items{flex-direction:row;flex-wrap:wrap;gap:2px}
  .cal-pill{display:inline-block;width:6px;font-size:0;padding:0;height:6px;min-width:6px;border-radius:50%}
  .cal-more{display:none}
}
.agenda-dia-modal{max-width:520px;max-height:82vh}
.agenda-dia-modal .dpp-modal-body{padding:14px 0}
/* ── Colapsables (grupos pasados / sección asesores) ──────────────────── */
.colapsable-head{cursor:pointer;user-select:none;display:flex;align-items:center;gap:7px}
.colapsable-head:hover{color:#2E75B6}
.agenda-chevron{display:inline-block;transition:transform .15s;font-size:10px;color:#9aacbd;flex-shrink:0}
.agenda-colapsable:not(.collapsed)>.colapsable-head .agenda-chevron{transform:rotate(90deg)}
.agenda-colapsable.collapsed>.agenda-colapsable-body{display:none}

/* ── Ayuda Memoria (tarjetas + stories) ────────────────────────────────── */
.am-controls{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin-bottom:12px}
.am-controls .search-box{flex:1;min-width:220px;margin-bottom:0}
.am-controls .select-wrapper{width:auto;min-width:200px;max-width:260px}
.am-chips{display:flex;flex-wrap:wrap;gap:7px;margin-bottom:10px}
.am-count{font-size:12px;color:#9aacbd}
.am-count-row{display:flex;align-items:center;justify-content:space-between;gap:10px;flex-wrap:wrap;margin-bottom:12px}
.am-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px}
.am-card{background:#fff;border:1px solid #D6E4F0;border-radius:10px;padding:14px 16px 12px;cursor:pointer;transition:all .15s;box-shadow:0 1px 3px rgba(0,0,0,0.05)}
.am-card:hover{transform:translateY(-2px);box-shadow:0 8px 20px -12px rgba(27,94,162,0.35);border-color:#1B5EA2}
.am-card-top{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;margin-bottom:8px}
.am-badge{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.4px;padding:3px 8px;border-radius:6px;white-space:nowrap}
.am-exp-num{font-size:11px;color:#9aacbd;font-weight:600;white-space:nowrap}
.am-od-num{background:#EAF0FA;color:#1B5EA2;padding:3px 9px;border-radius:20px;box-shadow:0 1px 4px rgba(27,94,162,0.35)}
.am-minoria-tag{font-size:9.5px;font-weight:700;text-transform:uppercase;letter-spacing:.3px;padding:3px 8px;border-radius:20px;background:#FFF3E0;color:#B25E09}
.am-autor{font-size:11px;font-weight:700;color:#1B5EA2;margin:0 0 4px;text-transform:uppercase;letter-spacing:.02em}
.am-desc{font-size:13px;color:#4A4A4A;line-height:1.48;margin:0 0 10px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.am-card-bottom{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:#9aacbd;gap:8px}
.am-comision{font-weight:600;color:#1B5EA2;max-width:70%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.am-read-hint{color:#1B5EA2;font-weight:600;white-space:nowrap}
.am-card-footer{margin-top:8px;padding-top:8px;border-top:1px solid #EEF3F8;display:flex;flex-wrap:wrap;gap:6px}

.am-scrim{position:fixed;inset:0;background:rgba(20,30,45,0.55);display:none;align-items:center;justify-content:center;z-index:200;padding:20px}
.am-scrim.open{display:flex}
.am-story{width:520px;max-width:100%;min-height:300px;max-height:92vh;background:#fff;border-radius:18px;overflow:hidden;position:relative;display:flex;flex-direction:column;box-shadow:0 30px 60px -20px rgba(0,0,0,0.35);font-family:inherit}
.am-progress{display:flex;gap:4px;padding:14px 16px 0}
.am-progress .bar{flex:1;height:3px;background:#D6E4F0;border-radius:2px;overflow:hidden}
.am-progress .bar .fill{height:100%;width:0%;background:#1B5EA2;transition:width .2s}
.am-story-head{display:flex;justify-content:space-between;align-items:center;padding:12px 18px 8px}
.am-story-head .id{font-size:11px;color:#1B5EA2;font-weight:700;letter-spacing:.04em}
.am-story-head .close{background:none;border:none;color:#9aacbd;font-size:20px;cursor:pointer;line-height:1}
.am-story-nav{position:absolute;top:56px;bottom:66px;width:32%;background:transparent;border:none;cursor:pointer}
.am-story-nav.prev{left:0}.am-story-nav.next{right:0}
.am-story-body{flex:1;padding:6px 26px 20px;overflow-y:auto;color:#4A4A4A}
.am-step-label{font-size:10.5px;letter-spacing:.1em;text-transform:uppercase;color:#1B5EA2;margin-bottom:10px;font-weight:700}
.am-story-body h2{font-size:19px;line-height:1.35;margin:0 0 14px;font-weight:700;color:#1B5EA2}
.am-badges-row{display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px}
.am-badges-row span{font-size:10.5px;padding:3px 8px;border-radius:5px;background:#D6E4F0;color:#1B5EA2;font-weight:600}
.am-story-body p{font-size:14px;line-height:1.62;color:#4A4A4A;margin:0 0 14px}
.am-kv{display:grid;grid-template-columns:auto 1fr;gap:8px 14px;font-size:13px;margin-bottom:6px}
.am-kv dt{color:#9aacbd;font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;align-self:start;padding-top:2px}
.am-kv dd{margin:0;color:#4A4A4A;line-height:1.5}
.am-link-row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px;position:relative;z-index:2}
.am-link-btn{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:600;color:#fff;background:#1B5EA2;padding:8px 12px;border-radius:8px;text-decoration:none;position:relative;z-index:2}
.am-link-btn:hover{background:#164a87}
.am-firmantes-bloque{margin-bottom:14px}
.am-firmantes-bloque .bl-name{font-size:11px;font-weight:700;padding:2px 8px;border-radius:5px;display:inline-block;margin-bottom:6px}
.am-firmantes-bloque .bl-list{font-size:13px;color:#4A4A4A;line-height:1.6}
.am-disidencia{margin-top:18px;padding-top:12px;border-top:1px dashed #D6E4F0}
.am-disid-title{font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:#C2650C;margin-bottom:8px}
.am-story-foot{display:flex;justify-content:space-between;align-items:center;padding:14px 18px;border-top:1px solid #D6E4F0}
.am-story-foot button{font-size:12.5px;font-weight:600;color:#1B5EA2;background:#fff;border:1.5px solid #D6E4F0;padding:8px 14px;border-radius:8px;cursor:pointer}
.am-story-foot button:disabled{opacity:.35;cursor:default}
.am-dots{display:flex;gap:6px}
.am-dot{width:6px;height:6px;border-radius:50%;background:#D6E4F0}
.am-dot.active{background:#1B5EA2}
@media (max-width:560px){.am-story{height:100%;border-radius:0}.am-story-nav{top:50px;bottom:60px}}

/* ── Tablero de Votación (artefacto) ─────────────────────────────────── */
@font-face {
    font-family: "Montserrat";
    font-style: normal;
    font-weight: 100 900;
    font-display: swap;
    src: url(data:font/woff2;base64,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) format("woff2");
  }
#main-votacion {
    /* Paleta institucional: Manual de Marca 2026 - Senado de la Nación */
    --brand-primary: #005ca9;
    --brand-deep: #1555a3;
    --brand-sky: #86d1f5;
    --brand-sky-pale: #d6eefb;
    --brand-gray: #575756;
    --brand-gray-light: #c7c7c9;

    --bg: #eaf4fc;
    --bg-elevated: #f5fafe;
    --panel: #ffffff;
    --ink: #4b4b4a;
    --ink-muted: #74797c;
    --ink-faint: #9aa1a6;
    --brass: var(--brand-primary);
    --brass-strong: var(--brand-deep);
    --border: #cfe3f2;
    --border-soft: #e3f1fb;

    --vote-positive: #2f7d4f;
    --vote-negative: #a83f2a;
    --vote-abstention: #b98a24;
    --vote-absent: #8b8577;
    --vote-pending-fill: #ffffff;
    --vote-pending-stroke: #a19a86;

    --chamber-a: #1555a3;
    --chamber-b: #00263f;

    --font-display: "Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    --font-ui: "Montserrat", -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
  }
body.print-view-active #main-votacion .page{display:none}
body.print-view-active > *:not(#main-votacion){display:none !important}
#main-votacion * { box-sizing: border-box; }
#main-votacion {
    margin: 0;
    background: var(--bg);
    color: var(--ink);
    font-family: var(--font-ui);
    -webkit-font-smoothing: antialiased;
  }
#main-votacion .page {
    max-width: 1040px;
    margin: 0 auto;
    padding: 1.5rem 1rem 3rem;
  }
#main-votacion header.masthead {
    text-align: center;
    margin-bottom: 1.5rem;
  }
#main-votacion .brand-mark {
    width: 56px;
    height: auto;
    margin-bottom: 0.4rem;
  }
#main-votacion .eyebrow {
    font-size: 0.66rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--brass);
    font-weight: 600;
  }
#main-votacion h1 {
    font-family: var(--font-display);
    font-weight: 800;
    text-transform: uppercase;
    font-size: clamp(1.5rem, 6.5vw, 2.3rem);
    margin: 0.35rem 0 0.4rem;
    color: var(--brand-deep);
    text-wrap: balance;
    letter-spacing: 0.01em;
    line-height: 1.15;
  }
#main-votacion .subhead {
    color: var(--ink-muted);
    font-size: 0.88rem;
    max-width: 46ch;
    margin: 0 auto;
    line-height: 1.5;
  }
#main-votacion .card {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    box-shadow: 0 1px 2px rgba(20, 20, 10, 0.04), 0 10px 30px -18px rgba(20, 20, 10, 0.35);
    overflow: hidden;
  }
#main-votacion .controls {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.6rem;
    padding: 1rem;
    border-bottom: 1px solid var(--border-soft);
  }
#main-votacion .controls-left {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }
#main-votacion select {
    appearance: none;
    width: 100%;
    font: inherit;
    font-size: 0.9rem;
    color: var(--ink);
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 2.1rem 0.7rem 0.85rem;
    min-height: 44px;
    cursor: pointer;
    background-image: linear-gradient(45deg, transparent 50%, var(--ink-muted) 50%), linear-gradient(135deg, var(--ink-muted) 50%, transparent 50%);
    background-position: calc(100% - 16px) 55%, calc(100% - 11px) 55%;
    background-size: 5px 5px, 5px 5px;
    background-repeat: no-repeat;
  }
#main-votacion input[type="search"] {
    width: 100%;
    font: inherit;
    font-size: 0.9rem;
    color: var(--ink);
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 0.85rem;
    min-height: 44px;
  }
#main-votacion input[type="search"]::placeholder { color: var(--ink-faint); }
#main-votacion input[type="search"]:focus-visible {
    outline: 2px solid var(--brass);
    outline-offset: 2px;
  }
#main-votacion .scenario-bar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding: 0.85rem 1rem;
    background: var(--bg-elevated);
    border-bottom: 1px solid var(--border-soft);
  }
#main-votacion .scenario-bar select { width: auto; flex: 1 1 180px; min-height: 40px; padding: 0.5rem 2.1rem 0.5rem 0.7rem; font-size: 0.82rem; }
#main-votacion .scenario-actions { display: flex; flex-wrap: wrap; gap: 0.4rem; }
#main-votacion .scenario-actions button { min-height: 40px; padding: 0.5rem 0.7rem; font-size: 0.78rem; }
#main-votacion .scenario-status {
    font-size: 0.75rem;
    color: var(--ink-faint);
    flex-basis: 100%;
  }
#main-votacion .history-bar {
    padding: 0.75rem 1rem 0;
  }
#main-votacion button.btn-undo {
    width: 100%;
    background: var(--bg-elevated);
    color: var(--brand-deep);
    border-color: var(--border);
  }
#main-votacion button.btn-undo:disabled {
    color: var(--ink-faint);
    cursor: not-allowed;
    opacity: 0.6;
  }
#main-votacion button.btn-undo:not(:disabled):hover { border-color: var(--brass-strong); }
#main-votacion select:focus-visible, #main-votacion button:focus-visible, #main-votacion .roster-item:focus-visible {
    outline: 2px solid var(--brass);
    outline-offset: 2px;
  }
#main-votacion .result {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 0.4rem;
    text-align: center;
    font-size: 0.85rem;
    font-weight: 600;
    padding: 0.6rem 0.85rem;
    border-radius: 8px;
    border: 1px solid transparent;
  }
#main-votacion .result.approved {
    color: var(--vote-positive);
    background: color-mix(in srgb, var(--vote-positive) 12%, transparent);
    border-color: color-mix(in srgb, var(--vote-positive) 30%, transparent);
  }
#main-votacion .result.rejected {
    color: var(--vote-negative);
    background: color-mix(in srgb, var(--vote-negative) 12%, transparent);
    border-color: color-mix(in srgb, var(--vote-negative) 30%, transparent);
  }
#main-votacion .result .detail {
    font-weight: 400;
    color: var(--ink-muted);
  }
#main-votacion .bulk-actions {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.5rem;
    padding: 0.75rem 1rem 1rem;
  }
#main-votacion button {
    font: inherit;
    font-size: 0.85rem;
    font-weight: 600;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 0.65rem 0.9rem;
    min-height: 44px;
    cursor: pointer;
    transition: filter 0.15s ease, background 0.15s ease;
  }
#main-votacion button.btn-positive { background: var(--vote-positive); color: #fff; }
#main-votacion button.btn-negative { background: var(--vote-negative); color: #fff; }
#main-votacion button.btn-neutral { background: var(--bg-elevated); color: var(--ink-muted); border-color: var(--border); }
#main-votacion button.btn-brass { background: var(--brass); color: #fff; }
#main-votacion button:hover { filter: brightness(1.06); }
#main-votacion button.btn-neutral:hover { filter: none; border-color: var(--ink-faint); }
#main-votacion .pdf-bar {
    padding: 0 1rem 1rem;
  }
#main-votacion .pdf-bar button { width: 100%; }
#main-votacion .chamber-wrap {
    position: relative;
    margin: 0 0.75rem 1rem;
    border-radius: 10px;
    background:
      radial-gradient(120% 95% at 50% 108%, var(--chamber-a) 0%, var(--chamber-b) 70%);
  }
#main-votacion .chamber-scroll {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    border-radius: 10px;
  }
#main-votacion .chamber-wrap svg {
    display: block;
    width: 720px;
    min-width: 720px;
    height: auto;
  }
#main-votacion .tooltip {
    position: absolute;
    top: 12px;
    left: 12px;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 0.75rem;
    font-size: 0.78rem;
    line-height: 1.4;
    box-shadow: 0 8px 24px -10px rgba(0,0,0,0.4);
    pointer-events: none;
    max-width: 220px;
  }
#main-votacion .tooltip .name { font-weight: 700; color: var(--ink); }
#main-votacion .tooltip .bloque { color: var(--brass-strong); }
#main-votacion .tooltip .prov { color: var(--ink-muted); }
#main-votacion .seat { cursor: pointer; }
#main-votacion .seat-ring, #main-votacion .seat-highlight { transition: stroke 0.15s ease, stroke-width 0.15s ease; }
#main-votacion .seat-badge { fill: var(--panel); stroke: rgba(0,0,0,0.15); stroke-width: 1; }
#main-votacion .seat-badge-text {
    font-family: var(--font-ui);
    font-size: 8.5px;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    fill: var(--ink);
    pointer-events: none;
    user-select: none;
  }
#main-votacion .seat:hover { opacity: 0.88 !important; }
#main-votacion .dais {
    fill: rgba(255,255,255,0.05);
    stroke: rgba(255,255,255,0.22);
    stroke-width: 1;
  }
#main-votacion .dais-label {
    fill: rgba(255,255,255,0.55);
    font-size: 9px;
    letter-spacing: 0.14em;
    font-family: var(--font-ui);
  }
#main-votacion .roster {
    margin: 0 0.75rem 1rem;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: var(--bg-elevated);
  }
#main-votacion .roster-head {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.6rem;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border-soft);
  }
#main-votacion .roster-head .label {
    font-size: 0.85rem;
    font-weight: 700;
  }
#main-votacion .roster-head .count {
    font-weight: 400;
    color: var(--ink-muted);
  }
#main-votacion .roster-actions {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.4rem;
  }
#main-votacion .roster-actions button {
    font-size: 0.68rem;
    padding: 0.55rem 0.4rem;
    min-height: 40px;
  }
#main-votacion .roster-grid {
    display: grid;
    grid-template-columns: 1fr;
    gap: 0.5rem;
    padding: 0.85rem 1rem 1rem;
  }
#main-votacion .roster-item {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 0.65rem;
    min-height: 44px;
    font-size: 0.8rem;
    text-align: left;
    color: var(--ink);
    cursor: pointer;
  }
#main-votacion .roster-item:hover { border-color: var(--brass); }
#main-votacion .dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }
#main-votacion .roster-item .who { overflow: hidden; }
#main-votacion .roster-item .who .n { font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#main-votacion .roster-item .who .p { color: var(--ink-faint); font-size: 0.7rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
#main-votacion .tallies {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1px;
    background: var(--border-soft);
    border-top: 1px solid var(--border-soft);
  }
#main-votacion .tally {
    background: var(--panel);
    padding: 0.85rem 0.5rem;
    text-align: center;
  }
#main-votacion .tally:last-child { grid-column: 1 / -1; }
#main-votacion .tally .num {
    font-size: 1.4rem;
    font-weight: 700;
    font-variant-numeric: tabular-nums;
    font-family: var(--font-display);
  }
#main-votacion .tally .lbl {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--ink-muted);
    margin-top: 0.15rem;
  }
#main-votacion footer.credit {
    text-align: center;
    color: var(--ink-faint);
    font-size: 0.75rem;
    margin-top: 1.5rem;
  }
@media (prefers-reduced-motion: reduce) {
#main-votacion * { transition: none !important; }
}
@media (min-width: 560px) {
#main-votacion .tallies { grid-template-columns: repeat(3, 1fr); }
#main-votacion .tally:last-child { grid-column: auto; }
#main-votacion .roster-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 640px) {
#main-votacion .page { padding: 2.5rem 1.5rem 4rem; }
#main-votacion header.masthead { margin-bottom: 2rem; }
#main-votacion .eyebrow { font-size: 0.72rem; }
#main-votacion .subhead { font-size: 0.92rem; }
#main-votacion .controls {
      flex-direction: row;
      align-items: center;
      justify-content: space-between;
      gap: 0.75rem;
      padding: 1.25rem 1.5rem;
    }
#main-votacion .controls-left { flex-direction: row; flex-wrap: wrap; gap: 0.6rem; }
#main-votacion select { width: auto; min-height: 0; }
#main-votacion .result { justify-content: flex-start; text-align: left; }
#main-votacion .bulk-actions {
      grid-template-columns: none;
      display: flex;
      flex-wrap: wrap;
      gap: 0.55rem;
      padding: 1rem 1.5rem;
    }
#main-votacion button { min-height: 0; }
#main-votacion .chamber-wrap { margin: 0 1.5rem 1.25rem; }
#main-votacion .chamber-wrap svg { width: 100%; min-width: 0; }
#main-votacion .roster { margin: 0 1.5rem 1.25rem; }
#main-votacion .roster-head { flex-direction: row; align-items: center; justify-content: space-between; }
#main-votacion .roster-actions { grid-template-columns: none; display: flex; gap: 0.5rem; }
#main-votacion .roster-actions button { font-size: 0.72rem; padding: 0.4rem 0.6rem; min-height: 0; }
#main-votacion .roster-grid { grid-template-columns: repeat(auto-fill, minmax(190px, 1fr)); }
#main-votacion .roster-item { padding: 0.45rem 0.6rem; min-height: 0; font-size: 0.78rem; }
#main-votacion .pdf-bar { padding: 0 1.5rem 1.25rem; }
#main-votacion .pdf-bar button { width: auto; }
}
@media (min-width: 860px) {
#main-votacion .tallies { grid-template-columns: repeat(5, 1fr); }
}
#main-votacion.print-view-active .page { display: none; }
#main-votacion .print-view {
    background: #fff;
    color: #111;
    min-height: 100vh;
    padding: 1.5rem;
    font-family: var(--font-ui);
  }
#main-votacion .print-view h1 {
    font-family: var(--font-display);
    font-weight: 800;
    text-transform: uppercase;
    font-size: 1.4rem;
    margin: 0 0 0.2rem;
    color: var(--brand-deep);
  }
#main-votacion .pv-toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.5rem;
    padding-bottom: 1rem;
    border-bottom: 1px dashed #bbb;
  }
#main-votacion .pv-toolbar button { min-height: 44px; }
#main-votacion .pv-hint {
    flex-basis: 100%;
    margin: 0.25rem 0 0;
    font-size: 0.8rem;
    color: #555;
  }
#main-votacion .pv-meta { font-size: 0.8rem; color: #444; margin-bottom: 0.75rem; }
#main-votacion .pv-result {
    display: inline-block;
    font-size: 0.95rem;
    font-weight: 700;
    padding: 0.5rem 0.75rem;
    border: 1.5px solid var(--brand-deep);
    color: var(--brand-deep);
    border-radius: 999px;
    margin-bottom: 1rem;
  }
#main-votacion .pv-tally {
    display: flex;
    flex-wrap: wrap;
    gap: 0 1.25rem;
    font-size: 0.85rem;
    margin-bottom: 0.85rem;
  }
#main-votacion .pv-chamber-wrap {
    margin-bottom: 1rem;
    break-inside: avoid;
  }
#main-votacion .pv-chamber-bg {
    border-radius: 10px;
    padding: 10px;
    background: radial-gradient(120% 95% at 50% 108%, var(--chamber-a) 0%, var(--chamber-b) 70%);
  }
#main-votacion .pv-chamber {
    display: block;
    width: 100%;
    max-width: 480px;
    margin: 0 auto;
  }
#main-votacion .pv-legend {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 0 1.25rem;
    font-size: 0.78rem;
    color: #444;
    margin-top: 0.5rem;
  }
#main-votacion .pv-legend-item { display: inline-flex; align-items: center; gap: 0.35rem; }
#main-votacion .pv-legend-dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
#main-votacion .pv-bloque-table { max-width: 600px; margin: 0 auto; }
#main-votacion .pv-bloque-table td:not(:first-child), #main-votacion .pv-bloque-table th:not(:first-child) { text-align: center; }
#main-votacion .print-view table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78rem;
  }
#main-votacion .print-view th, #main-votacion .print-view td {
    text-align: left;
    padding: 0.22rem 0.4rem;
    border-bottom: 1px solid #ccc;
    font-variant-numeric: tabular-nums;
  }
#main-votacion .print-view th {
    border-bottom: 1.5px solid var(--brand-primary);
    color: var(--brand-deep);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
#main-votacion .print-view tbody tr { break-inside: avoid; }
@media print {
#main-votacion .no-print { display: none !important; }
#main-votacion.print-view-active .print-view { padding: 0; }
}
body.print-view-active #main-votacion #herr-root { display: none; }
#main-votacion .print-view .pv-subheading {
    font-family: var(--font-display);
    font-weight: 700;
    font-size: 0.95rem;
    text-transform: uppercase;
    letter-spacing: 0.03em;
    color: var(--brand-deep);
    margin: 1.25rem 0 0.4rem;
  }

/* ── Cálculo de 2/3 ───────────────────────────────────────────────────── */
#main-votacion .dt-page { max-width: 480px; }
#main-votacion .dt-card {
    padding: 1.75rem 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
    align-items: center;
  }
#main-votacion .dt-field { display: flex; flex-direction: column; gap: 0.4rem; width: 100%; max-width: 220px; }
#main-votacion .dt-field label { font-size: 0.8rem; font-weight: 600; color: var(--ink-muted); }
#main-votacion .dt-field input[type="number"] {
    font: inherit;
    font-size: 1.1rem;
    text-align: center;
    color: var(--ink);
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem;
    min-height: 44px;
  }
#main-votacion .dt-field input[type="number"]:focus-visible { outline: 2px solid var(--brass); outline-offset: 2px; }
#main-votacion .dt-result { text-align: center; }
#main-votacion .dt-result-num { font-family: var(--font-display); font-weight: 800; font-size: 3rem; color: var(--brass-strong); line-height: 1; }
#main-votacion .dt-result-lbl { font-size: 0.9rem; color: var(--ink-muted); margin-top: 0.4rem; }
#main-votacion .dt-result-lbl strong { color: var(--ink); }

/* ── Cálculo de tiempos ───────────────────────────────────────────────── */
#main-votacion .tiempos-config {
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
    align-items: center;
    padding: 0.85rem 1rem;
    border-bottom: 1px solid var(--border-soft);
    background: var(--bg-elevated);
  }
#main-votacion .tiempos-config label { display: flex; flex-direction: column; gap: 0.3rem; font-size: 0.78rem; font-weight: 600; color: var(--ink-muted); }
#main-votacion .tiempos-config input[type="time"] {
    font: inherit;
    font-size: 0.9rem;
    color: var(--ink);
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.5rem 0.7rem;
    min-height: 40px;
  }
#main-votacion .tiempos-fin { font-size: 0.85rem; color: var(--ink); }
#main-votacion .tiempos-fin strong { color: var(--brass-strong); font-variant-numeric: tabular-nums; }
#main-votacion .tiempos-add { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.85rem 1rem; border-bottom: 1px solid var(--border-soft); }
#main-votacion .tiempos-add select { flex: 1 1 220px; }
#main-votacion .tiempos-add input[type="number"] {
    width: 90px;
    font: inherit;
    font-size: 0.9rem;
    color: var(--ink);
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem;
    min-height: 44px;
    text-align: center;
  }
#main-votacion .tiempos-add button { flex: 0 0 auto; }
#main-votacion .tiempos-pdf-import { display: flex; flex-wrap: wrap; align-items: center; gap: 0.6rem; padding: 0 1rem 0.85rem; border-bottom: 1px solid var(--border-soft); }
#main-votacion .tiempos-pdf-status { font-size: 0.8rem; color: var(--ink-muted); }
#main-votacion .oradores-list { display: flex; flex-direction: column; gap: 0.4rem; padding: 0.85rem 1rem; }
#main-votacion .orador-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.6rem;
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 8px;
    font-size: 0.82rem;
  }
#main-votacion .orador-nombre { flex: 1 1 140px; min-width: 0; }
#main-votacion .orador-row.dragging { opacity: 0.4; }
#main-votacion .orador-row.is-hablo { border-color: var(--vote-positive); }
#main-votacion .orador-row.is-no-habla { opacity: 0.55; }
#main-votacion .orador-row.is-no-habla .orador-nombre .n { text-decoration: line-through; }
#main-votacion .orador-drag { cursor: grab; color: var(--ink-faint); font-size: 1rem; }
#main-votacion .orador-orden { font-weight: 700; color: var(--brass-strong); min-width: 1.4em; text-align: center; }
#main-votacion .orador-nombre .n { font-weight: 600; color: var(--ink); }
#main-votacion .orador-nombre .b { font-size: 0.72rem; color: var(--ink-muted); }
#main-votacion .orador-minutos { display: flex; align-items: center; gap: 0.3rem; font-size: 0.75rem; color: var(--ink-muted); white-space: nowrap; }
#main-votacion .orador-minutos-input { width: 52px; font: inherit; font-size: 0.82rem; text-align: center; border: 1px solid var(--border); border-radius: 6px; padding: 0.3rem; background: var(--panel); }
#main-votacion .orador-horario { font-variant-numeric: tabular-nums; color: var(--ink-muted); white-space: nowrap; }
#main-votacion .orador-estado { display: flex; gap: 0.3rem; }
#main-votacion .orador-check, #main-votacion .orador-cross {
    min-height: 32px;
    min-width: 32px;
    padding: 0;
    font-size: 0.85rem;
    background: var(--panel);
    color: var(--ink-faint);
    border: 1px solid var(--border);
  }
#main-votacion .orador-check.on { background: var(--vote-positive); color: #fff; border-color: var(--vote-positive); }
#main-votacion .orador-cross.on { background: var(--vote-negative); color: #fff; border-color: var(--vote-negative); }
#main-votacion .orador-remove { background: transparent; border: none; color: var(--ink-faint); min-height: 32px; padding: 0.2rem; }
#main-votacion .orador-remove:hover { color: var(--vote-negative); }

/* ── Reglamento HSN (PDF) ─────────────────────────────────────────────── */
#main-votacion .reg-toolbar { display: flex; flex-wrap: wrap; gap: 0.5rem; padding: 0.85rem 1rem; border-bottom: 1px solid var(--border-soft); background: var(--bg-elevated); }
#main-votacion .reg-toolbar a { text-decoration: none; }
#main-votacion .reg-frame-wrap { padding: 0.75rem; }
#main-votacion .reg-frame { display: block; width: 100%; height: 75vh; min-height: 420px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg-elevated); }
#main-votacion .reg-fallback { padding: 0 1rem 1rem; font-size: 0.8rem; color: var(--ink-muted); }

"""

# ── JavaScript (vanilla) ───────────────────────────────────────────────────────

JS = r"""
var TIPOS={PL:'Proy. de Ley',PD:'Declaración',PC:'Comunicación',PR:'Resolución',CA:'Com. Auditoría',AC:'Acuerdo',CV:'Com. Varias',CC:'Com. de Comisiones',CD:'Com. de Diputados',CE:'Com. del P.E.',CM:'Com. de Ministerios',CO:'Com. de Senadores',DC:'Decreto',MS:'Mensaje de Senado',MD:'Mensaje de Diputados',PP:'Petición',DE:'Proy. de Decreto',RC:'Resolución Conjunta',RP:'Respuesta de Presidencia'};
var TIPO_FG={PL:'#1B5EA2',PD:'#2E75B6',PC:'#0d7a4a',PR:'#5B4DA0',CA:'#1a7a4a',AC:'#7a5c1a',CV:'#7a1a3a',CC:'#2f7a7a',CD:'#8a4a1a',CE:'#4a4a8a',CM:'#7a4a4a',CO:'#4a7a2f',DC:'#8a1a5c',MS:'#1a5c8a',MD:'#5c8a1a',PP:'#8a5c1a',DE:'#5c1a8a',RC:'#1a8a7a',RP:'#8a1a1a'};
var TIPO_BG={PL:'#D6E4F0',PD:'#EAF0FA',PC:'#DCF0E8',PR:'#EDE8FA',CA:'#E0F4EC',AC:'#F9F0DA',CV:'#FAE0EA',CC:'#DFF3F3',CD:'#F5E8DA',CE:'#E2E2F5',CM:'#F2E4E4',CO:'#E4F2DD',DC:'#F5DCEC',MS:'#DCEBF5',MD:'#EBF5DC',PP:'#F5EBDC',DE:'#EBDCF5',RC:'#DCF5EF',RP:'#F5DCDC'};
var ORIGEN_LABEL={S:'Senado',PE:'Poder Ejecutivo',CD:'Diputados',OV:'Otros',P:'Particulares',JGM:'Jefatura de Gabinete',OVD:'Oficiales Varios Diputados'};
var REUNION_TIPO_LABEL={senadores:'Reunión de senadores',asesores:'Reunión de asesores',bicameral:'Reunión bicameral'};
var REUNION_TIPO_COLOR={senadores:{fg:'#1B5EA2',bg:'#D6E4F0'},asesores:{fg:'#0d7a4a',bg:'#DCF0E8'},bicameral:{fg:'#5B4DA0',bg:'#EDE8FA'}};
/* Colores por bloque — mismo mapa que el repo comisiones-senado */
var BLOQUE_COLORS={
  'LA LIBERTAD AVANZA':                      {dot:'#7030A0', bg:'#F3E8FA', badge:'#4A1870'},
  'JUSTICIALISTA':                           {dot:'#1F4E9C', bg:'#E6EDF8', badge:'#0D2A5E'},
  'JUSTICIA SOCIAL FEDERAL':                 {dot:'#00B0F0', bg:'#E5F7FE', badge:'#005F80'},
  'UCR - UNIÓN CÍVICA RADICAL':              {dot:'#FF0000', bg:'#FFE8E8', badge:'#8B0000'},
  'CONVICCIÓN FEDERAL':                      {dot:'#5B9BD5', bg:'#EBF3FB', badge:'#1A4A70'},
  'FRENTE PRO':                              {dot:'#FFD700', bg:'#FFFBE6', badge:'#6B5600'},
  'PROVINCIAS UNIDAS':                       {dot:'#ED7D31', bg:'#FDF0E7', badge:'#7A3800'},
  'FRENTE RENOVADOR DE LA CONCORDIA SOCIAL': {dot:'#70AD47', bg:'#EDF5E7', badge:'#2E5018'},
  'FRENTE CÍVICO POR SANTIAGO':              {dot:'#548235', bg:'#EAF2E3', badge:'#2D4A1A'},
  'MOVERE POR SANTA CRUZ':                   {dot:'#00B050', bg:'#E6F5ED', badge:'#005A28'},
  'DESPIERTA CHUBUT':                        {dot:'#7B3F00', bg:'#F5EBE4', badge:'#4A2400'},
  'INDEPENDENCIA':                           {dot:'#4472C4', bg:'#EAF0FA', badge:'#1B3A7A'},
  'LA NEUQUINIDAD':                          {dot:'#FF69B4', bg:'#FDE8F3', badge:'#8B0050'},
  'PRIMERO LOS SALTEÑOS':                    {dot:'#92D050', bg:'#F0FAE6', badge:'#3A6010'},
  'MOVIMIENTO POR MISIONES':                 {dot:'#C00000', bg:'#FBE5E5', badge:'#6B0000'}
};
var BLOQUE_COLOR_DEFAULT={dot:'#9CA3AF', bg:'#F9FAFB', badge:'#374151'};
function normBloque(b){return String(b||'').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim()}
/* ── Fotos de senadores (extraídas del despliegue oficial 2026) ─────── */
function normNombreFoto(s){return String(s||'').toUpperCase().normalize('NFD').replace(/[̀-ͯ]/g,'').trim()}
function fotoSenadorUrl(nombre){
  var f=FOTOS_SENADORES[normNombreFoto(nombre)];
  return f?'data/fotos/'+f:null;
}
function avatarHtml(nombre,size){
  var url=fotoSenadorUrl(nombre);
  if(!url)return '';
  size=size||26;
  return '<img class="senador-avatar" src="'+escAttr(url)+'" width="'+size+'" height="'+size+'" loading="lazy" alt="" onerror="this.remove()">';
}
var BLOQUE_COLORS_NORM={};
Object.keys(BLOQUE_COLORS).forEach(function(k){BLOQUE_COLORS_NORM[normBloque(k)]=BLOQUE_COLORS[k]});
var ALL_BLOQUES=[];
var dashAnio='2026',dashEvoMode='tipo',dashCross={dim:'',val:''};
var activeTipos={},activeBloque='',activeOrigen='',activeProvincia='',activeAnio='',activeAcuerdoEstado='',activeConOD=false;
var pageBuscador=1,PAGE_SIZE=25;
var DATA_INDEX={};
function claveP(p){return p.origen+'~'+p.nro+'~'+p.anio+'~'+p.tipo;}

/* ── Escapado HTML básico ──────────────────────────────────────────── */
function esc(s){return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')}
/* Comisiones unicamerales vienen con el prefijo "DE " (ej. "DE DEFENSA NACIONAL");
   las bicamerales no lo tienen. Sólo cosmético, no toca el dato subyacente. */
function comLabel(s){return String(s||'').replace(/^DE\s+/i,'');}
function escAttr(s){return esc(s).replace(/"/g,'&quot;')}

/* ── Navegación ────────────────────────────────────────────────────── */
function activateMain(id){
  if(!document.getElementById('main-'+id))return false;
  document.querySelectorAll('.mtab-btn').forEach(function(b){b.classList.remove('active')});
  document.querySelectorAll('.mtab-content').forEach(function(c){c.classList.remove('active')});
  document.getElementById('main-'+id).classList.add('active');
  var btnNav=document.querySelector('[data-main="'+id+'"]');
  btnNav.classList.add('active');
  /* con 7 pestañas la barra desborda en el celular: centrar la activa */
  var nav=btnNav.parentNode;
  if(nav&&nav.scrollWidth>nav.clientWidth){
    nav.scrollLeft=btnNav.getBoundingClientRect().left-nav.getBoundingClientRect().left+nav.scrollLeft-(nav.clientWidth-btnNav.offsetWidth)/2;
  }
  return true;
}
function switchMain(id){
  if(!activateMain(id))return;
  if(location.hash!=='#'+id)history.pushState({main:id},'','#'+id);
}
window.addEventListener('popstate',function(){
  if(document.body.classList.contains('ficha-activa')&&location.hash.indexOf('#f/')!==0){
    document.body.classList.remove('ficha-activa');
    document.getElementById('fichaReunionOverlay').hidden=true;
  }
  if(window.pjSyncHash&&window.pjSyncHash())return;
  if(abrirReunionDesdeHash())return;
  var id=(location.hash||'#proyectos').slice(1).split('/')[0];
  activateMain(id);
  if(id==='agenda'){
    document.getElementById('agenda-nivel2').classList.remove('active');
    document.getElementById('agenda-nivel1').classList.add('active');
  }
});
function switchSub(id){
  document.querySelectorAll('.sub-btn').forEach(function(b){b.classList.remove('active')});
  document.querySelectorAll('.sub-content').forEach(function(c){c.classList.remove('active')});
  document.getElementById('sub-'+id).classList.add('active');
  document.querySelector('[data-sub="'+id+'"]').classList.add('active');
  if(id==='estadisticas')renderDashboard();
}

function init(){
  var bset={};
  DATA.forEach(function(p){p.bloques.forEach(function(b){if(b)bset[b]=1})});
  ALL_BLOQUES=Object.keys(bset).sort();

  var cset1={},csetAdic={};
  DATA.forEach(function(p){
    if(p.comisiones[0])cset1[p.comisiones[0]]=1;
    if(p.comisiones[1])csetAdic[p.comisiones[1]]=1;
    if(p.comisiones[2])csetAdic[p.comisiones[2]]=1;
  });
  fillSelectLabeled('com-select-1',Object.keys(cset1).sort(),comLabel);
  fillSelectLabeled('com-select-adic',Object.keys(csetAdic).sort(),comLabel);

  refreshAutorSelect();

  fillSelect('bloque-select',ALL_BLOQUES);

  var provSet={};
  DATA.forEach(function(p){(p.provincias||[]).forEach(function(pv){if(pv)provSet[pv]=1})});
  fillSelect('provincia-select',Object.keys(provSet).sort());

  var oset={};
  DATA.forEach(function(p){if(p.origen)oset[p.origen]=1});
  fillSelectLabeled('origen-select',Object.keys(oset).sort(),function(o){return ORIGEN_LABEL[o]||o});

  var tset0={};
  DATA.forEach(function(p){tset0[p.tipo]=1});
  fillSelectLabeled('tipo-select',Object.keys(tset0).sort(),function(t){return t+' · '+(TIPOS[t]||t);});

  DATA.forEach(function(p){DATA_INDEX[claveP(p)]=p});

  renderDashboard();
  syncFilterUI();
  renderList();
  renderStatsBar();
  renderComisionesList();
  renderRepresentacion();
  agendaInit();
  amInit();
  renderSancChips();
  renderSanciones();
  renderPrefChips();
  renderPreferencias();
}
function fillSelect(id,values){
  var sel=document.getElementById(id);
  values.forEach(function(v){
    var o=document.createElement('option');o.value=v;o.textContent=v;sel.appendChild(o);
  });
}
function fillSelectLabeled(id,values,labelFn){
  var sel=document.getElementById(id);
  values.forEach(function(v){
    var o=document.createElement('option');o.value=v;o.textContent=labelFn(v);sel.appendChild(o);
  });
}
function blqColor(b){return BLOQUE_COLORS_NORM[normBloque(b)]||BLOQUE_COLOR_DEFAULT}
function getBloqueColor(b){return blqColor(b).dot}

/* ── Dashboard de análisis ─────────────────────────────────────── */
var MESES=['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
function crossMatch(p){
  if(!dashCross.dim)return true;
  if(dashCross.dim==='tipo')return p.tipo===dashCross.val;
  if(dashCross.dim==='bloque')return p.bloques.indexOf(dashCross.val)>=0||bloqueOf(p)===dashCross.val;
  if(dashCross.dim==='com')return (p.comisiones[0]||'')===dashCross.val;
  return true;
}
function dashData(){return DATA.filter(function(p){return String(p.anio)===dashAnio&&crossMatch(p);})}
function jsStr(s){return String(s).replace(/\\/g,'\\\\').replace(/'/g,"\\'");}
function crossClick(dim,val){
  if(!val)return;
  if(dashCross.dim===dim&&dashCross.val===val)dashCross={dim:'',val:''};
  else dashCross={dim:dim,val:val};
  renderDashboard();
}
function clearCross(){dashCross={dim:'',val:''};renderDashboard();}
function setDashAnio(y){
  dashAnio=y;dashCross={dim:'',val:''};treemapDrillBloque=null;
  ['2026','2025'].forEach(function(a){
    var el=document.getElementById('dash-anio-'+a);
    if(el)el.className='dash-anio-btn'+(dashAnio===a?' on':'');
  });
  renderDashboard();
}
function setEvoMode(m){
  dashEvoMode=m;
  document.getElementById('evo-tipo').className=(m==='tipo'?'on':'');
  document.getElementById('evo-bloque').className=(m==='bloque'?'on':'');
  renderEvolucion(dashData());
}
function renderDashboard(){
  var data=dashData();
  document.getElementById('dash-total').innerHTML='<strong>'+data.length+'</strong> proyectos en '+dashAnio;
  var ci=document.getElementById('dash-cross');
  if(dashCross.dim){
    var dimL={tipo:'tipo',bloque:'bloque',com:'comisión'}[dashCross.dim];
    var valL=dashCross.dim==='tipo'?(TIPOS[dashCross.val]||dashCross.val):dashCross.val;
    ci.innerHTML='Filtrando por: <strong>'+esc(valL)+'</strong> <span style="opacity:.65">('+dimL+')</span> &#x2715;';
    ci.className='dash-cross active';
  }else{ci.className='dash-cross';ci.innerHTML='';}
  renderEvolucion(data);
  renderTreemap(data);
  renderRankingBloques(data);
  renderStacked(data);
  renderDonut(data);
  renderTopComs(data);
}
/* tooltip flotante compartido */
function showTip(html,ev){
  var t=document.getElementById('dash-tooltip');
  t.innerHTML=html;t.className='dash-tooltip show';
  var x=ev.clientX,y=ev.clientY,w=t.offsetWidth,h=t.offsetHeight;
  if(x+w+18>window.innerWidth)x=x-w-14;else x=x+14;
  if(y+h+18>window.innerHeight)y=y-h-14;else y=y+14;
  t.style.left=x+'px';t.style.top=y+'px';
}
function hideTip(){document.getElementById('dash-tooltip').className='dash-tooltip';}
/* helpers de agregación */
function topSeries(counts,n){
  /* counts: {clave:total}; devuelve top n claves + 'Otros' si sobra */
  var keys=Object.keys(counts).sort(function(a,b){return counts[b]-counts[a]});
  if(keys.length<=n)return{keys:keys,hasOtros:false};
  return{keys:keys.slice(0,n),hasOtros:true};
}
/* ── Viz 1: Evolución temporal (líneas) ──────────────────────── */
var EVO=null;
function monthOf(p){if(!p.fecha)return -1;var pp=p.fecha.split('/');return pp.length===3?parseInt(pp[1],10)-1:-1;}
function evoKey(p){return dashEvoMode==='tipo'?p.tipo:(p.bloques[0]||(ORIGEN_LABEL[p.origen]||'Otros'));}
function evoColor(k){if(k==='__otros')return '#9aacbd';return dashEvoMode==='tipo'?(TIPO_FG[k]||'#888'):getBloqueColor(k);}
function evoLabel(k){if(k==='__otros')return 'Resto';return dashEvoMode==='tipo'?(TIPOS[k]||k):k;}
function renderEvolucion(data){
  var totals={};
  data.forEach(function(p){var k=evoKey(p);totals[k]=(totals[k]||0)+1;});
  var sel=topSeries(totals,5),keys=sel.keys.slice(),useOtros=sel.hasOtros;
  var lastM=0,any=false;
  data.forEach(function(p){var m=monthOf(p);if(m>=0){any=true;if(m>lastM)lastM=m;}});
  var nM=any?lastM+1:1;
  var series={};keys.forEach(function(k){series[k]=[];for(var j=0;j<nM;j++)series[k].push(0);});
  if(useOtros){series['__otros']=[];for(var j=0;j<nM;j++)series['__otros'].push(0);}
  data.forEach(function(p){
    var m=monthOf(p);if(m<0||m>=nM)return;
    var k=evoKey(p);
    if(keys.indexOf(k)>=0)series[k][m]++;else if(useOtros)series['__otros'][m]++;
  });
  var order=keys.slice();if(useOtros)order.push('__otros');
  var maxY=1;order.forEach(function(k){series[k].forEach(function(v){if(v>maxY)maxY=v;});});

  var W=600,H=240,L=38,R=14,T=12,B=26,pw=W-L-R,ph=H-T-B;
  function X(i){return nM>1?L+i/(nM-1)*pw:L+pw/2;}
  function Y(v){return T+ph-(v/maxY)*ph;}
  var svg='<svg class="viz-svg" viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet">';
  [0,0.5,1].forEach(function(f){var v=Math.round(maxY*f),y=Y(v);
    svg+='<line class="viz-gridline" x1="'+L+'" y1="'+y+'" x2="'+(W-R)+'" y2="'+y+'"/>';
    svg+='<text class="viz-axis" x="'+(L-6)+'" y="'+(y+3)+'" text-anchor="end">'+v+'</text>';});
  for(var i=0;i<nM;i++)svg+='<text class="viz-axis" x="'+X(i)+'" y="'+(H-8)+'" text-anchor="middle">'+MESES[i]+'</text>';
  order.forEach(function(k){
    var pts=series[k].map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1);}).join(' ');
    var c=evoColor(k);
    svg+='<polyline points="'+pts+'" fill="none" stroke="'+c+'" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>';
    series[k].forEach(function(v,i){svg+='<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="2.6" fill="'+c+'"/>';});
  });
  svg+='<line id="evo-guide" x1="0" y1="'+T+'" x2="0" y2="'+(T+ph)+'" stroke="#1B5EA2" stroke-width="1" stroke-dasharray="3 3" opacity="0"/>';
  for(var i=0;i<nM;i++){
    var bw=nM>1?pw/(nM-1):pw, bx=nM>1?X(i)-bw/2:L;
    svg+='<rect x="'+bx.toFixed(1)+'" y="'+T+'" width="'+bw.toFixed(1)+'" height="'+ph+'" fill="transparent" onmousemove="evoHover(event,'+i+')" onmouseleave="evoOut()"/>';
  }
  svg+='</svg>';
  document.getElementById('viz-evolucion').innerHTML=svg;
  var leg='';var edim=dashEvoMode==='tipo'?'tipo':'bloque';
  order.forEach(function(k){
    var clk=(k!=='__otros');
    var on=clk&&dashCross.dim===edim&&dashCross.val===k;
    var oc=clk?' class="legend-item clk" onclick="crossClick(\''+edim+'\',\''+jsStr(k)+'\')"':' class="legend-item"';
    leg+='<span'+oc+(on?' style="font-weight:700;color:#1B5EA2"':'')+'><span class="legend-swatch" style="background:'+evoColor(k)+'"></span>'+esc(evoLabel(k))+'</span>';
  });
  document.getElementById('evo-legend').innerHTML=leg;
  EVO={nM:nM,order:order,series:series,xs:[]};for(var i=0;i<nM;i++)EVO.xs.push(X(i));
}
function evoHover(ev,i){
  if(!EVO)return;
  var g=document.getElementById('evo-guide');
  if(g){g.setAttribute('x1',EVO.xs[i]);g.setAttribute('x2',EVO.xs[i]);g.setAttribute('opacity','1');}
  var rows='';
  EVO.order.forEach(function(k){
    rows+='<div class="dash-tt-row"><span class="dash-tt-dot" style="background:'+evoColor(k)+'"></span>'+esc(evoLabel(k))+'<span class="v">'+EVO.series[k][i]+'</span></div>';
  });
  showTip('<div class="dash-tt-title">'+MESES[i]+' '+dashAnio+'</div>'+rows,ev);
}
function evoOut(){var g=document.getElementById('evo-guide');if(g)g.setAttribute('opacity','0');hideTip();}
/* ── Viz 2: Treemap por bloque, subdividido por tipo ─────────── */
function bloqueOf(p){return p.bloques[0]||(ORIGEN_LABEL[p.origen]||'Otros');}
function trunc(s,n){s=String(s);return s.length>n?s.slice(0,n-1)+'…':s;}
/* treemap "squarified" (tiles casi cuadrados, sin librerías) */
function treemapLayout(items,x,y,w,h){
  if(!items.length)return [];
  var total=0;items.forEach(function(it){total+=it.value;});
  if(total<=0)return [];
  var scale=(w*h)/total;
  var rem=items.map(function(it){return {key:it.key,value:it.value,area:it.value*scale};});
  var area={x:x,y:y,w:w,h:h},out=[];
  function worst(row,side){
    var s=0,mx=-Infinity,mn=Infinity;
    row.forEach(function(r){s+=r.area;if(r.area>mx)mx=r.area;if(r.area<mn)mn=r.area;});
    var s2=s*s,l2=side*side;
    return Math.max(l2*mx/s2,s2/(l2*mn));
  }
  while(rem.length){
    var side=Math.min(area.w,area.h),row=[];
    while(rem.length){
      if(row.length===0||worst(row,side)>=worst(row.concat([rem[0]]),side))row.push(rem.shift());
      else break;
    }
    var rs=0;row.forEach(function(r){rs+=r.area;});
    if(area.w>=area.h){
      var dw=rs/area.h,yy=area.y;
      row.forEach(function(r){var rh=r.area/dw;out.push({key:r.key,value:r.value,x:area.x,y:yy,w:dw,h:rh});yy+=rh;});
      area.x+=dw;area.w-=dw;
    }else{
      var dh=rs/area.w,xx=area.x;
      row.forEach(function(r){var rw=r.area/dh;out.push({key:r.key,value:r.value,x:xx,y:area.y,w:rw,h:dh});xx+=rw;});
      area.y+=dh;area.h-=dh;
    }
  }
  return out;
}
var treemapDrillBloque=null;
function volverTreemap(){treemapDrillBloque=null;renderTreemap(dashData());}
function renderTreemap(data){
  var box=document.getElementById('viz-treemap');
  var bc=document.getElementById('treemap-breadcrumb');
  /* solo bloques políticos: expedientes de origen Senado (S) con bloque asignado */
  var dS=data.filter(function(p){return p.origen==='S'&&p.bloques[0];});
  var W=1000,H=300,pad=3;

  if(treemapDrillBloque){
    bc.innerHTML='<a onclick="volverTreemap()">Bloques</a> &#9656; '
      +'<span class="curr" onclick="volverTreemap()" title="Volver a todos los bloques">'+esc(treemapDrillBloque)+' &#10005;</span>';
    var dB=dS.filter(function(p){return p.bloques[0]===treemapDrillBloque;});
    var tipoTot={};dB.forEach(function(p){tipoTot[p.tipo]=(tipoTot[p.tipo]||0)+1;});
    var tkeys=Object.keys(tipoTot).sort(function(a,b){return tipoTot[b]-tipoTot[a];});
    if(!tkeys.length){box.innerHTML='<div class="viz-empty">Sin datos para este bloque.</div>';document.getElementById('treemap-legend').innerHTML='';return;}
    var titems=tkeys.map(function(k){return {key:k,value:tipoTot[k]};});
    var trects=treemapLayout(titems,0,0,W,H);
    var tsvg='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" style="display:block;width:100%;height:auto;max-height:380px">';
    trects.forEach(function(r){
      var t=r.key,x=r.x+pad/2,y=r.y+pad/2,w=Math.max(0,r.w-pad),h=Math.max(0,r.h-pad);
      var sc=TIPO_FG[t]||'#888';
      var on=(dashCross.dim==='tipo'&&dashCross.val===t);
      tsvg+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+sc+'" stroke="'+(on?'#0d3f73':'#fff')+'" stroke-width="'+(on?3:1.5)+'" style="cursor:pointer" onclick="crossClick(\'tipo\',\''+jsStr(t)+'\')"><title>'+esc(TIPOS[t]||t)+': '+r.value+'</title></rect>';
      if(w>62&&h>28){
        tsvg+='<text x="'+(x+5).toFixed(1)+'" y="'+(y+15).toFixed(1)+'" style="font-size:11px;font-weight:700;fill:#fff;pointer-events:none">'+esc(TIPOS[t]||t)+'</text>';
        tsvg+='<text x="'+(x+5).toFixed(1)+'" y="'+(y+30).toFixed(1)+'" style="font-size:12px;font-weight:700;fill:#fff;opacity:.85;pointer-events:none">'+r.value+'</text>';
      }
    });
    tsvg+='</svg>';
    box.innerHTML=tsvg;
    document.getElementById('treemap-legend').innerHTML='';
    return;
  }

  bc.innerHTML='';
  var blTot={};dS.forEach(function(p){var b=p.bloques[0];blTot[b]=(blTot[b]||0)+1;});
  var keys=Object.keys(blTot).sort(function(a,b){return blTot[b]-blTot[a];});
  if(!keys.length){box.innerHTML='<div class="viz-empty">Sin datos para este a&ntilde;o.</div>';document.getElementById('treemap-legend').innerHTML='';return;}
  var items=keys.map(function(k){return {key:k,value:blTot[k]};});
  var rects=treemapLayout(items,0,0,W,H);
  var svg='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" style="display:block;width:100%;height:auto;max-height:380px">';
  rects.forEach(function(r){
    var bl=r.key,x=r.x+pad/2,y=r.y+pad/2,w=Math.max(0,r.w-pad),h=Math.max(0,r.h-pad);
    var c=getBloqueColor(bl);
    svg+='<rect x="'+x.toFixed(1)+'" y="'+y.toFixed(1)+'" width="'+w.toFixed(1)+'" height="'+h.toFixed(1)+'" fill="'+c+'" stroke="#fff" stroke-width="1.5" style="cursor:pointer" onclick="treemapDrillBloque=\''+jsStr(bl)+'\';renderTreemap(dashData())"><title>'+esc(bl)+': '+r.value+' &middot; clic para ver desglose por tipo</title></rect>';
    if(w>62&&h>28){
      svg+='<text x="'+(x+5).toFixed(1)+'" y="'+(y+15).toFixed(1)+'" style="font-size:11px;font-weight:700;fill:#fff;pointer-events:none">'+esc(trunc(bl,Math.floor(w/7)))+'</text>';
      svg+='<text x="'+(x+5).toFixed(1)+'" y="'+(y+30).toFixed(1)+'" style="font-size:12px;font-weight:700;fill:#fff;opacity:.85;pointer-events:none">'+r.value+'</text>';
    }
  });
  svg+='</svg>';
  box.innerHTML=svg;
  document.getElementById('treemap-legend').innerHTML='';
}
function renderRankingBloques(data){
  var dS=data.filter(function(p){return p.origen==='S'&&p.bloques[0];});
  var cols=['PL','PC','PD','PR'];
  var cells={},rowTot={},colTot={PL:0,PC:0,PD:0,PR:0},grand=0,rowSet={};
  dS.forEach(function(p){
    if(cols.indexOf(p.tipo)<0)return;
    var rk=p.bloques[0];
    rowSet[rk]=1;
    cells[rk+'~|~'+p.tipo]=(cells[rk+'~|~'+p.tipo]||0)+1;
    rowTot[rk]=(rowTot[rk]||0)+1;colTot[p.tipo]++;grand++;
  });
  var rowKeys=Object.keys(rowSet).sort(function(a,b){return (rowTot[b]||0)-(rowTot[a]||0)});
  var maxCell=0;
  rowKeys.forEach(function(rk){cols.forEach(function(ck){var v=cells[rk+'~|~'+ck]||0;if(v>maxCell)maxCell=v})});
  var h='<table class="pivot-table"><thead><tr><th class="pv-corner">Bloque</th>';
  cols.forEach(function(ck){h+='<th>'+ck+'</th>'});
  h+='<th class="pv-tot">Total</th></tr></thead><tbody>';
  rowKeys.forEach(function(rk){
    h+='<tr><th class="pv-rowhead" title="'+escAttr(rk)+'">'+esc(rk)+'</th>';
    cols.forEach(function(ck){
      var v=cells[rk+'~|~'+ck]||0;
      var style='',cls='pv-cell';
      if(v){
        cls+=' pv-click';
        var intensity=maxCell?v/maxCell:0;
        style='background:rgba(27,94,162,'+(0.06+intensity*0.74).toFixed(3)+')';
        if(intensity>0.55)style+=';color:#fff';
      }else{cls+=' pv-empty'}
      h+='<td class="'+cls+'" style="'+style+'"'+(v?' onclick="drillRanking(\''+jsStr(rk)+'\',\''+ck+'\')"':'')+'>'+(v||'')+'</td>';
    });
    h+='<td class="pv-tot">'+rowTot[rk]+'</td></tr>';
  });
  h+='<tr class="pv-totrow"><th class="pv-rowhead">Total general</th>';
  cols.forEach(function(ck){h+='<td class="pv-tot">'+colTot[ck]+'</td>'});
  h+='<td class="pv-grand">'+grand+'</td></tr></tbody></table>';
  document.getElementById('ranking-body').innerHTML=grand?h:'<div class="no-results">Sin datos para este a&ntilde;o.</div>';
}
function drillRanking(bloque,tipo){
  resetBuscadorOnly();
  activeBloque=bloque;setSelVal('bloque-select',bloque);
  refreshAutorSelect();
  activeTipos={};activeTipos[tipo]=1;
  applyAll();
  switchSub('buscador');
  window.scrollTo({top:0,behavior:'smooth'});
}
/* ── Viz 3: Barras apiladas horizontales (Tipo por Bloque) ───── */
function renderStacked(data){
  var box=document.getElementById('viz-stacked');
  var tipoTot={};data.forEach(function(p){tipoTot[p.tipo]=(tipoTot[p.tipo]||0)+1;});
  var tipos=Object.keys(tipoTot).sort(function(a,b){return tipoTot[b]-tipoTot[a];});
  if(!tipos.length){box.innerHTML='<div class="viz-empty">Sin datos.</div>';document.getElementById('stacked-legend').innerHTML='';return;}
  var blTot={};data.forEach(function(p){var b=bloqueOf(p);blTot[b]=(blTot[b]||0)+1;});
  var selB=topSeries(blTot,6),topB=selB.keys,useResto=selB.hasOtros;
  var m={};
  data.forEach(function(p){
    var t=p.tipo,b=bloqueOf(p),key=topB.indexOf(b)>=0?b:'__resto';
    (m[t]=m[t]||{});m[t][key]=(m[t][key]||0)+1;
  });
  var order=topB.slice();if(useResto)order.push('__resto');
  var maxT=tipos.reduce(function(mx,t){return Math.max(mx,tipoTot[t]);},1);
  var W=600,L=46,R=46,T=6,rowH=30,barH=18,pw=W-L-R,H=T+tipos.length*rowH+2;
  function sc(c){return c==='__resto'?'#9aacbd':getBloqueColor(c);}
  function sl(c){return c==='__resto'?'Resto':c;}
  var svg='<svg viewBox="0 0 '+W+' '+H+'" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block">';
  tipos.forEach(function(t,ti){
    var cy=T+ti*rowH+rowH/2,barY=cy-barH/2,xacc=L;
    var ton=(dashCross.dim==='tipo'&&dashCross.val===t);
    svg+='<text x="0" y="'+(cy+4)+'" style="cursor:pointer;font-size:12px;font-weight:700;fill:'+(ton?'#0d3f73':(TIPO_FG[t]||'#888'))+(ton?';text-decoration:underline':'')+'" onclick="crossClick(\'tipo\',\''+jsStr(t)+'\')">'+esc(t)+'</text>';
    order.forEach(function(b){
      var v=(m[t]&&m[t][b])||0;if(!v)return;
      var w=v/maxT*pw,clk=(b!=='__resto');
      var oc=clk?' style="cursor:pointer" onclick="crossClick(\'bloque\',\''+jsStr(b)+'\')"':'';
      svg+='<rect x="'+xacc.toFixed(1)+'" y="'+barY+'" width="'+w.toFixed(1)+'" height="'+barH+'" fill="'+sc(b)+'"'+oc+'><title>'+esc(sl(b))+' &middot; '+esc(TIPOS[t]||t)+': '+v+' ('+Math.round(v/tipoTot[t]*100)+'%)</title></rect>';
      xacc+=w;
    });
    svg+='<text x="'+(L+tipoTot[t]/maxT*pw+5).toFixed(1)+'" y="'+(cy+4)+'" style="font-size:11px;font-weight:700;fill:#1B5EA2">'+tipoTot[t]+'</text>';
  });
  svg+='</svg>';
  box.innerHTML=svg;
  var leg='';order.forEach(function(b){
    var clk=(b!=='__resto'),on=clk&&dashCross.dim==='bloque'&&dashCross.val===b;
    var oc=clk?' class="legend-item clk" onclick="crossClick(\'bloque\',\''+jsStr(b)+'\')"':' class="legend-item"';
    leg+='<span'+oc+(on?' style="font-weight:700;color:#1B5EA2"':'')+'><span class="legend-swatch" style="background:'+sc(b)+'"></span>'+esc(trunc(sl(b),22))+'</span>';
  });
  document.getElementById('stacked-legend').innerHTML=leg;
}
/* ── Viz 5: Donut — distribución por tipo de proyecto ────────── */
function renderDonut(data){
  var box=document.getElementById('viz-donut');
  var tipoTot={};data.forEach(function(p){tipoTot[p.tipo]=(tipoTot[p.tipo]||0)+1;});
  var tipos=Object.keys(tipoTot).sort(function(a,b){return tipoTot[b]-tipoTot[a];});
  var total=data.length;
  if(!total){box.innerHTML='<div class="viz-empty">Sin datos para este a&ntilde;o.</div>';return;}
  var cx=100,cy=100,R=70,SW=28,C=2*Math.PI*R,cum=0;
  var svg='<svg viewBox="0 0 200 200" style="width:150px;height:150px;flex-shrink:0"><g transform="rotate(-90 '+cx+' '+cy+')">';
  tipos.forEach(function(t){
    var frac=tipoTot[t]/total,dash=frac*C,c=TIPO_FG[t]||'#888';
    svg+='<circle cx="'+cx+'" cy="'+cy+'" r="'+R+'" fill="none" stroke="'+c+'" stroke-width="'+SW+'" stroke-dasharray="'+dash.toFixed(2)+' '+(C-dash).toFixed(2)+'" stroke-dashoffset="'+(-cum*C).toFixed(2)+'" style="cursor:pointer" onclick="crossClick(\'tipo\',\''+jsStr(t)+'\')"><title>'+esc(TIPOS[t]||t)+': '+tipoTot[t]+' ('+Math.round(frac*100)+'%)</title></circle>';
    cum+=frac;
  });
  svg+='</g><text x="'+cx+'" y="'+(cy-1)+'" text-anchor="middle" style="font-size:30px;font-weight:700;fill:#1B5EA2">'+total+'</text>';
  svg+='<text x="'+cx+'" y="'+(cy+17)+'" text-anchor="middle" style="font-size:11px;fill:#888">proyectos</text></svg>';
  var leg='<div class="viz-legend" style="flex:1;margin-top:0;flex-direction:column;gap:5px;min-width:130px">';
  tipos.forEach(function(t){
    var pct=Math.round(tipoTot[t]/total*100),on=dashCross.dim==='tipo'&&dashCross.val===t;
    leg+='<span class="legend-item clk" style="justify-content:flex-start'+(on?';font-weight:700;color:#1B5EA2':'')+'" onclick="crossClick(\'tipo\',\''+jsStr(t)+'\')"><span class="legend-swatch" style="background:'+(TIPO_FG[t]||'#888')+'"></span>'+esc(TIPOS[t]||t)+' &middot; <strong style="margin-left:3px">'+tipoTot[t]+'</strong> ('+pct+'%)</span>';
  });
  leg+='</div>';
  box.innerHTML='<div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap;justify-content:center">'+svg+leg+'</div>';
}
/* ── Viz 4: Top 10 comisiones con sparkline de tendencia ─────── */
function fmtDM(d){return ('0'+d.getDate()).slice(-2)+'/'+('0'+(d.getMonth()+1)).slice(-2);}
function sparkline(vals,bins){
  var w=92,h=26,p=3,n=vals.length,mx=Math.max.apply(null,vals)||1;
  function X(i){return p+(n>1?i/(n-1)*(w-2*p):(w-2*p)/2);}
  function Y(v){return h-p-(v/mx)*(h-2*p);}
  var pts=vals.map(function(v,i){return X(i).toFixed(1)+','+Y(v).toFixed(1);}).join(' ');
  var s='<svg class="topcom-spark" viewBox="0 0 '+w+' '+h+'">';
  s+='<line x1="'+p+'" y1="'+(h-p)+'" x2="'+(w-p)+'" y2="'+(h-p)+'" stroke="#E3EAF3" stroke-width="1"/>';
  s+='<polyline points="'+pts+'" fill="none" stroke="#2E75B6" stroke-width="1.5" stroke-linejoin="round" stroke-linecap="round"/>';
  vals.forEach(function(v,i){
    var last=i===n-1;
    s+='<circle cx="'+X(i).toFixed(1)+'" cy="'+Y(v).toFixed(1)+'" r="'+(last?2.4:1.4)+'" fill="'+(last?'#1B5EA2':'#2E75B6')+'"><title>Semana '+fmtDM(bins[i][0])+'–'+fmtDM(bins[i][1])+': '+v+'</title></circle>';
  });
  s+='</svg>';
  return s;
}
function renderTopComs(data){
  var box=document.getElementById('viz-topcoms');
  var comC={};data.forEach(function(p){var c=p.comisiones[0];if(c)comC[c]=(comC[c]||0)+1;});
  var coms=Object.keys(comC).sort(function(a,b){return comC[b]-comC[a];}).slice(0,10);
  if(!coms.length){box.innerHTML='<div class="viz-empty">Sin datos para este a&ntilde;o.</div>';return;}
  var maxD=null;data.forEach(function(p){var d=parseFecha(p.fecha);if(d&&(!maxD||d>maxD))maxD=d;});
  if(!maxD)maxD=new Date();
  var WEEKS=8,MS=7*24*3600*1000;
  var bins=[];for(var i=0;i<WEEKS;i++){var end=new Date(maxD.getTime()-(WEEKS-1-i)*MS);bins.push([new Date(end.getTime()-6*MS),end]);}
  function binOf(d){var idx=WEEKS-1-Math.floor((maxD-d)/MS);return (idx>=0&&idx<WEEKS)?idx:-1;}
  var series={};coms.forEach(function(c){series[c]=[];for(var i=0;i<WEEKS;i++)series[c].push(0);});
  data.forEach(function(p){var c=p.comisiones[0];if(coms.indexOf(c)<0)return;var d=parseFecha(p.fecha);if(!d)return;var b=binOf(d);if(b>=0)series[c][b]++;});
  var rango=fmtDM(bins[0][0])+' &ndash; '+fmtDM(bins[WEEKS-1][1]);
  var html='<div style="font-size:10px;color:#888;margin-bottom:6px">Tendencia &uacute;ltimas 8 semanas ('+rango+') &middot; conteo total por 1er giro</div>';
  coms.forEach(function(c,i){
    var on=dashCross.dim==='com'&&dashCross.val===c;
    html+='<div class="topcom-row clk" onclick="crossClick(\'com\',\''+jsStr(c)+'\')"><span class="topcom-rank">'+(i+1)+'</span><span class="topcom-name"'+(on?' style="font-weight:700;color:#1B5EA2"':'')+'>'+esc(c)+'</span><span class="topcom-count">'+comC[c]+'</span>'+sparkline(series[c],bins)+'</div>';
  });
  box.innerHTML=html;
}

/* ── Tabla dinámica (pivot table) ──────────────────────────────── */
/* Dimensiones disponibles para Filas / Columnas */
/* Limpia los filtros propios del buscador (no los compartidos año/tipo/origen) */
function resetBuscadorOnly(){
  activeBloque='';activeProvincia='';activeConOD=false;
  setSelVal('bloque-select','');setSelVal('provincia-select','');
  setSelVal('com-select-1','');setSelVal('com-select-adic','');setSelVal('autor-select','');
  document.getElementById('search').value='';
  document.getElementById('fecha-desde').value='';
  document.getElementById('fecha-hasta').value='';
  var conOdEl=document.getElementById('con-od-check');if(conOdEl)conOdEl.checked=false;
  refreshAutorSelect();
}
function setSelVal(id,v){var el=document.getElementById(id);if(el){el.value=v;el.className=v?'filter-select on':'filter-select';}}

/* ── Estado de filtros compartido (año/tipo/origen) ─────────────── */
function applyAll(){pageBuscador=1;syncFilterUI();renderList();}
function syncFilterUI(){
  ['all','2025','2026'].forEach(function(a){
    var el=document.getElementById('anio-det-'+a);
    if(el)el.className='chip'+(activeAnio===(a==='all'?'':a)?' on':'');
  });
  var os=document.getElementById('origen-select');
  if(os){os.value=activeOrigen;os.className=activeOrigen?'filter-select on':'filter-select';}
  var ts=document.getElementById('tipo-select');
  var tv=Object.keys(activeTipos)[0]||'';
  if(ts){ts.value=tv;ts.className=tv?'filter-select on':'filter-select';}
  renderFilters();
}
function setAnioShared(v){activeAnio=v;applyAll();}
function setOrigenShared(v){activeOrigen=v;applyAll();}

/* ── Buscador: filtros ─────────────────────────────────────────── */
function renderFilters(){
  var tk=Object.keys(activeTipos);
  var soloAC=tk.length===1&&tk[0]==='AC';
  var acBox=document.getElementById('acuerdo-estado-filter');
  if(acBox){
    acBox.style.display=soloAC?'':'none';
    if(!soloAC){activeAcuerdoEstado=''}
    var ah='<button class="chip'+(activeAcuerdoEstado===''?' on':'')+'" onclick="setAcuerdoEstado(\'\')">Todos</button>'
      +'<button class="chip'+(activeAcuerdoEstado==='dado'?' on':'')+'" onclick="setAcuerdoEstado(\'dado\')">Dado cuenta</button>'
      +'<button class="chip'+(activeAcuerdoEstado==='pendiente'?' on':'')+'" onclick="setAcuerdoEstado(\'pendiente\')">Pendiente de dar cuenta</button>';
    document.getElementById('acuerdo-estado-chips').innerHTML=ah;
  }
}
function setAcuerdoEstado(v){activeAcuerdoEstado=v;pageBuscador=1;renderFilters();renderList();}
function setTipoSelect(v){
  activeTipos={};if(v)activeTipos[v]=1;
  var el=document.getElementById('tipo-select');
  if(el)el.className=v?'filter-select on':'filter-select';
  applyAll();
}
/* Recalcula las opciones de Autor según el bloque activo (si hay uno) —
   sólo autores que efectivamente tengan proyectos con ese bloque. */
function refreshAutorSelect(){
  var sel=document.getElementById('autor-select');
  if(!sel)return;
  var prev=sel.value;
  var aset={};
  DATA.forEach(function(p){
    if(activeBloque&&p.bloques.indexOf(activeBloque)<0)return;
    p.autores.forEach(function(a){aset[a]=1});
  });
  var opciones=Object.keys(aset).sort();
  sel.innerHTML='<option value="">Todos los autores</option>';
  opciones.forEach(function(a){var o=document.createElement('option');o.value=a;o.textContent=a;sel.appendChild(o)});
  var val=opciones.indexOf(prev)>=0?prev:'';
  sel.value=val;
  sel.className=val?'filter-select on':'filter-select';
}
function setBloque(val){
  activeBloque=val;
  var el=document.getElementById('bloque-select');
  if(el)el.className=val?'filter-select on':'filter-select';
  refreshAutorSelect();
  pageBuscador=1;renderList();
}
function setConOD(val){activeConOD=val;pageBuscador=1;renderList();}
function clearConOD(){var el=document.getElementById('con-od-check');if(el)el.checked=false;setConOD(false);}
function setProvincia(val){
  activeProvincia=val;
  var el=document.getElementById('provincia-select');
  if(el)el.className=val?'filter-select on':'filter-select';
  pageBuscador=1;renderList();
}
/* Filtros que sólo viven en el DOM (com1/comAdic/autor/búsqueda/fechas):
   reaplican estilo "on" al select y resetean a página 1. */
function onFilterChange(){
  ['com-select-1','com-select-adic','autor-select'].forEach(function(id){
    var el=document.getElementById(id);
    if(el)el.className=el.value?'filter-select on':'filter-select';
  });
  pageBuscador=1;renderList();
}
function clearSearch(){document.getElementById('search').value='';onFilterChange();}
function clearCom1(){setSelVal('com-select-1','');onFilterChange();}
function clearComAdic(){setSelVal('com-select-adic','');onFilterChange();}
function clearAutor(){setSelVal('autor-select','');onFilterChange();}
function clearFechas(){document.getElementById('fecha-desde').value='';document.getElementById('fecha-hasta').value='';onFilterChange();}
function parseFecha(s){
  if(!s)return null;
  var p=s.split('/');
  if(p.length!==3)return null;
  return new Date(parseInt(p[2]),parseInt(p[1])-1,parseInt(p[0]));
}
function getFiltered(){
  var q=document.getElementById('search').value.toLowerCase().trim();
  var selCom1=document.getElementById('com-select-1').value;
  var selComAdic=document.getElementById('com-select-adic').value;
  var selAutor=document.getElementById('autor-select').value;
  var dDesde=document.getElementById('fecha-desde').value;
  var dHasta=document.getElementById('fecha-hasta').value;
  var fDesde=dDesde?new Date(dDesde):null;
  var fHasta=dHasta?new Date(dHasta+'T23:59:59'):null;

  return DATA.filter(function(p){
    if(activeAnio&&String(p.anio)!==activeAnio)return false;
    if(Object.keys(activeTipos).length&&!activeTipos[p.tipo])return false;
    if(activeBloque&&p.bloques.indexOf(activeBloque)<0)return false;
    if(activeOrigen&&p.origen!==activeOrigen)return false;
    if(activeProvincia&&(!p.provincias||p.provincias.indexOf(activeProvincia)<0))return false;
    if(activeAcuerdoEstado==='dado'&&p.dado_cuenta!==true)return false;
    if(activeAcuerdoEstado==='pendiente'&&p.dado_cuenta!==false)return false;
    if(activeConOD&&!p.od)return false;
    if(selCom1&&p.comisiones[0]!==selCom1)return false;
    if(selComAdic&&p.comisiones.slice(1).indexOf(selComAdic)<0)return false;
    if(selAutor&&p.autores.indexOf(selAutor)<0)return false;
    if(fDesde||fHasta){
      var fp=parseFecha(p.fecha);
      if(fp){
        if(fDesde&&fp<fDesde)return false;
        if(fHasta&&fp>fHasta)return false;
      }
    }
    if(q){
      var hay=(p.extracto+' '+p.autores.join(' ')+' '+p.comisiones.join(' ')+' '+expNroOf(p)).toLowerCase();
      if(hay.indexOf(q)<0)return false;
    }
    return true;
  });
}
function expNroOf(p){return p.origen+'-'+p.nro+'/'+String(p.anio).slice(-2);}
function cardBadgesHtml(p){
  var html='';
  if(p.reuniones&&p.reuniones.length){
    var r=p.reuniones[0];
    var extra=p.reuniones.length>1?' (+'+(p.reuniones.length-1)+' anteriores)':'';
    html+='<span class="reunion-badge">Tratado en reuni&oacute;n: '+esc(r.comision)+' &middot; '+esc(r.fecha)+extra+'</span>';
  }
  if(p.od){
    html+='<a class="od-badge" href="'+escAttr(p.od.url_pdf)+'" target="_blank" onclick="event.stopPropagation()">OD N&ordm; '+esc(p.od.nro_od+'/'+String(p.od.anio_od).slice(-2))+'</a>';
  }
  if(p.badge_preferencia){
    var solTxt=p.badge_preferencia.solicitante?(' por '+esc(p.badge_preferencia.solicitante)):'';
    html+='<span class="pref-badge">Preferencia solicitada'+solTxt+' &middot; sesi&oacute;n del '+esc(p.badge_preferencia.fecha)+'</span>';
  }
  if(p.badge_sancionado){
    var txtSanc=p.badge_sancionado.ley?('Sancionado &middot; '+esc(p.badge_sancionado.ley)):('Sancionado &middot; sesi&oacute;n del '+esc(p.badge_sancionado.fecha));
    html+='<a class="sancionado-badge" onclick="event.stopPropagation();irASanciones(\''+jsStr(expNroOf(p))+'\')">'+txtSanc+'</a>';
  }
  if(p.badge_diputados){
    html+='<span class="diputados-badge">Enviado a Diputados &middot; sesi&oacute;n del '+esc(p.badge_diputados.fecha)+'</span>';
  }
  if(p.tipo==='AC'&&p.dado_cuenta===true){
    html+='<span class="dadocuenta-badge">Dado cuenta &middot; sesi&oacute;n del '+esc(p.fecha_dado_cuenta)+'</span>';
  }
  if(p.tipo==='AC'&&p.dado_cuenta===false){
    html+='<span class="pendientecuenta-badge">Pendiente de dar cuenta</span>';
  }
  return html;
}
function cardFooterHtml(p){
  var html=cardBadgesHtml(p);
  return html?'<div class="card-footer">'+html+'</div>':'';
}
function buildCard(p){
  var fg=TIPO_FG[p.tipo]||'#888',bg=TIPO_BG[p.tipo]||'#eee';
  var autoresTxt=p.autores.slice(0,3).join(' · ')+(p.autores.length>3?' +'+(p.autores.length-3)+' más':'');
  var btags='',ctags='';
  p.bloques.forEach(function(b){
    var c=blqColor(b);
    btags+='<span class="btag" style="background:'+c.bg+';color:'+c.badge+'">'+esc(b)+'</span>';
  });
  p.comisiones.forEach(function(c){ctags+='<span class="ctag">'+esc(comLabel(c))+'</span>'});
  var expNro=expNroOf(p);
  var linkBtn=p.url?'<a class="exp-link" href="'+escAttr(p.url)+'" target="_blank" onclick="event.stopPropagation()">Ver en Senado &#8599;</a>':'';
  return '<div class="card" onclick="abrirFicha(\''+jsStr(claveP(p))+'\')"><div class="card-exp"><div class="exp-id"><span class="exp-badge" style="background:'+bg+';color:'+fg+'">'+esc(p.tipo)+'</span><span class="exp-nro">'+esc(expNro)+'</span>'+(p.fecha?'<span class="exp-fecha">'+esc(p.fecha)+'</span>':'')+'</div>'+linkBtn+'</div><div class="card-body"><div class="extracto">'+esc(p.extracto)+'</div><div class="card-meta">'+(autoresTxt?'<div class="meta-row"><span class="meta-bold">'+esc(autoresTxt)+'</span></div>':'')+(btags?'<div class="meta-row">'+btags+'</div>':'')+(ctags?'<div class="meta-row">'+ctags+'</div>':'')+'</div></div>'+cardFooterHtml(p)+'</div>';
}
function renderList(){
  var filtered=getFiltered();
  var tot=filtered.length;
  document.getElementById('results-count').innerHTML=tot+' proyecto'+(tot!==1?'s':'')+' encontrado'+(tot!==1?'s':'');
  renderActiveChips();
  if(!filtered.length){
    document.getElementById('list').innerHTML='<div class="no-results">Sin resultados para este filtro.</div>';
    document.getElementById('pagination').innerHTML='';
    return;
  }
  var totalPages=Math.max(1,Math.ceil(tot/PAGE_SIZE));
  if(pageBuscador>totalPages)pageBuscador=totalPages;
  if(pageBuscador<1)pageBuscador=1;
  var pageItems=filtered.slice((pageBuscador-1)*PAGE_SIZE,pageBuscador*PAGE_SIZE);
  var html='';
  pageItems.forEach(function(p){html+=buildCard(p)});
  document.getElementById('list').innerHTML=html;
  renderPagination(totalPages);
}
function goToPage(n){pageBuscador=n;renderList();window.scrollTo({top:document.getElementById('list').offsetTop-90,behavior:'smooth'});}
function renderPagination(totalPages){
  var box=document.getElementById('pagination');
  if(totalPages<=1){box.innerHTML='';return;}
  var h='<button class="page-btn" '+(pageBuscador===1?'disabled':'onclick="goToPage('+(pageBuscador-1)+')"')+'>&#8249; Anterior</button>';
  var pages=[];
  for(var i=1;i<=totalPages;i++){
    if(i===1||i===totalPages||Math.abs(i-pageBuscador)<=1)pages.push(i);
    else if(pages[pages.length-1]!=='…')pages.push('…');
  }
  pages.forEach(function(p){
    if(p==='…')h+='<span class="page-ellipsis">&hellip;</span>';
    else h+='<button class="page-btn'+(p===pageBuscador?' on':'')+'" onclick="goToPage('+p+')">'+p+'</button>';
  });
  h+='<button class="page-btn" '+(pageBuscador===totalPages?'disabled':'onclick="goToPage('+(pageBuscador+1)+')"')+'>Siguiente &#8250;</button>';
  box.innerHTML=h;
}
/* ── Chips de filtros activos (incluye los que viven sólo en el DOM) ──── */
function renderActiveChips(){
  var box=document.getElementById('active-chips');
  if(!box)return;
  var chips=[];
  if(activeAnio)chips.push(['Año: '+activeAnio,'setAnioShared(\'\')']);
  Object.keys(activeTipos).forEach(function(t){
    chips.push(['Tipo: '+t,'setTipoSelect(\'\')']);
  });
  if(activeBloque)chips.push(['Bloque: '+activeBloque,'setBloque(\'\')']);
  if(activeProvincia)chips.push(['Provincia: '+activeProvincia,'setProvincia(\'\')']);
  if(activeOrigen)chips.push(['Origen: '+(ORIGEN_LABEL[activeOrigen]||activeOrigen),'setOrigenShared(\'\')']);
  if(activeAcuerdoEstado)chips.push(['Acuerdo: '+(activeAcuerdoEstado==='dado'?'Dado cuenta':'Pendiente'),'setAcuerdoEstado(\'\')']);
  if(activeConOD)chips.push(['Con OD','clearConOD()']);
  var com1=document.getElementById('com-select-1').value;
  if(com1)chips.push(['Comisión: '+comLabel(com1),'clearCom1()']);
  var comAdic=document.getElementById('com-select-adic').value;
  if(comAdic)chips.push(['Giro adicional: '+comLabel(comAdic),'clearComAdic()']);
  var autor=document.getElementById('autor-select').value;
  if(autor)chips.push(['Autor: '+autor,'clearAutor()']);
  var dDesde=document.getElementById('fecha-desde').value,dHasta=document.getElementById('fecha-hasta').value;
  if(dDesde||dHasta)chips.push(['Fechas: '+(dDesde||'…')+' a '+(dHasta||'…'),'clearFechas()']);
  var q=document.getElementById('search').value.trim();
  if(q)chips.push(['Texto: "'+q+'"','clearSearch()']);
  box.innerHTML=chips.map(function(c){
    return '<span class="active-chip">'+esc(c[0])+'<button onclick="'+c[1]+'" title="Quitar filtro">&#10005;</button></span>';
  }).join('');
  var secCount=(activeAnio?1:0)+(activeProvincia?1:0)
    +(document.getElementById('com-select-adic').value?1:0)
    +((document.getElementById('fecha-desde').value||document.getElementById('fecha-hasta').value)?1:0)
    +(activeAcuerdoEstado?1:0);
  var cntEl=document.getElementById('filters-more-count');
  if(cntEl)cntEl.textContent=secCount?('('+secCount+')'):'';
}

/* ── Exportar a Excel ──────────────────────────────────────────── */
function exportarExcel(){
  var filtered=getFiltered();
  if(!filtered.length){alert('No hay datos para exportar.');return}
  var headers=['Tipo','Nro','Origen','Fecha','Bloque','Autor','Coautor','Extracto','Giro 1','Giro 2','Giro 3'];
  var rows=[headers],urls=[];
  filtered.forEach(function(p){
    rows.push([
      p.tipo,p.nro+'/'+String(p.anio).slice(-2),p.origen,p.fecha,
      p.bloques.join('; '),p.autores.join('; '),(p.coautores||[]).join('; '),
      p.extracto,p.comisiones[0]||'',p.comisiones[1]||'',p.comisiones[2]||''
    ]);
    urls.push(p.url||'');
  });
  var wb=XLSX.utils.book_new();
  var ws=XLSX.utils.aoa_to_sheet(rows);
  for(var i=0;i<filtered.length;i++){
    if(urls[i]){
      var cellRef=XLSX.utils.encode_cell({r:i+1,c:1});
      if(ws[cellRef]){ws[cellRef].l={Target:urls[i]}}
    }
  }
  ws['!cols']=[{wch:6},{wch:10},{wch:8},{wch:12},{wch:28},{wch:35},{wch:35},{wch:60},{wch:30},{wch:30},{wch:30}];
  XLSX.utils.book_append_sheet(wb,ws,'Proyectos');
  XLSX.writeFile(wb,'proyectos_filtrados.xlsx');
}

/* ── Comisiones ────────────────────────────────────────────────── */
function normCom(s){return String(s||'').toUpperCase().trim()}
function nombreCom(s){return String(s||'').replace(/^De\s+/,'')}
/* ── Barra de stats (filtro rápido: constituidas / sin constituir / con vacantes) ── */
var comFiltroStat='';
function comisionPasaStat(c){
  if(comFiltroStat==='constituida')return c.integrantes.length>0;
  if(comFiltroStat==='sinconstituir')return c.integrantes.length===0;
  if(comFiltroStat==='vacante')return c.integrantes.length<c.cupo;
  return true;
}
function setComFiltroStat(v){comFiltroStat=(comFiltroStat===v?'':v);renderStatsBar();renderComisionesList();}
function renderStatsBar(){
  var nConst=0,nSin=0,nVac=0;
  COMISIONES.forEach(function(c){
    if(c.integrantes.length>0)nConst++;else nSin++;
    if(c.integrantes.length<c.cupo)nVac++;
  });
  function card(key,num,label){
    return '<div class="stat-card'+(comFiltroStat===key?' active':'')+'" onclick="setComFiltroStat(\''+key+'\')">'
      +'<div class="stat-num">'+num+'</div><div class="stat-label">'+label+'</div></div>';
  }
  document.getElementById('com-stats-bar').innerHTML=
    card('constituida',nConst,'Constituidas')+card('sinconstituir',nSin,'Sin constituir')+card('vacante',nVac,'Con vacantes');
}
function renderComisionesList(){
  var q=(document.getElementById('com-search').value||'').toLowerCase().trim();
  var lista=COMISIONES.filter(function(c){return (!q||nombreCom(c.nombre).toLowerCase().indexOf(q)>=0)&&comisionPasaStat(c)});
  var el=document.getElementById('com-list');
  if(!lista.length){el.innerHTML='<div class="com-empty">Sin comisiones para este filtro.</div>';return}
  var html='';
  lista.forEach(function(c,i){
    var idx=COMISIONES.indexOf(c);
    html+='<div class="com-card" onclick="abrirComision('+idx+')">'
      +'<div class="com-card-nombre">'+esc(nombreCom(c.nombre))+'</div>'
      +'</div>';
  });
  el.innerHTML=html;
}
function abrirComision(idx){
  var c=COMISIONES[idx];
  if(!c)return;
  document.getElementById('com-detalle-nombre').textContent=nombreCom(c.nombre);
  document.getElementById('com-nivel1').classList.remove('active');
  document.getElementById('com-nivel2').classList.add('active');
  renderIntegrantes(c);
  renderProximaReunion(c);
  document.getElementById('proyTema').value='';
  renderProyeccion();
  switchComSub('integrantes');
  initProyectosComision(c);
}
function volverComisiones(){
  document.getElementById('com-nivel2').classList.remove('active');
  document.getElementById('com-nivel1').classList.add('active');
}
function switchHerrVista(id){
  var root=document.getElementById('herr-root');
  root.querySelectorAll(':scope > .sub-nav .sub-btn').forEach(function(b){b.classList.remove('active')});
  root.querySelectorAll(':scope > .sub-content').forEach(function(c){c.classList.remove('active')});
  root.querySelector('[data-herrvista="'+id+'"]').classList.add('active');
  document.getElementById('herr-vista-'+id).classList.add('active');
}
function switchComVista(id){
  var root=document.getElementById('com-nivel1');
  root.querySelectorAll(':scope > .sub-nav .sub-btn').forEach(function(b){b.classList.remove('active')});
  root.querySelectorAll(':scope > .sub-content').forEach(function(c){c.classList.remove('active')});
  root.querySelector('[data-comvista="'+id+'"]').classList.add('active');
  document.getElementById('com-vista-'+id).classList.add('active');
  if(id==='estadisticas'){renderRepresentacion();renderComisionesPorSenador();}
}
function switchComEstad(id){
  var root=document.getElementById('com-vista-estadisticas');
  root.querySelectorAll('.com-sub-btn').forEach(function(b){b.classList.remove('active')});
  root.querySelectorAll('.com-sub-content').forEach(function(c){c.classList.remove('active')});
  root.querySelector('[data-comestad="'+id+'"]').classList.add('active');
  document.getElementById('com-estad-'+id).classList.add('active');
}
function switchComSub(id){
  var root=document.getElementById('com-nivel2');
  root.querySelectorAll('.com-sub-btn').forEach(function(b){b.classList.remove('active')});
  root.querySelectorAll('.com-sub-content').forEach(function(c){c.classList.remove('active')});
  root.querySelector('[data-comsub="'+id+'"]').classList.add('active');
  document.getElementById('com-sub-'+id).classList.add('active');
}
var comisionAbierta=null;
/* Orden fijo pedido por Mariano: cargos de mesa primero, después LLA, después
   UCR, después el resto de bloques ("varios"), y al final —de arriba para
   abajo— Convicción Federal, Justicia Social Federal, Frente Cívico por
   Santiago y, en el último lugar, Justicialista. */
var CARGO_ORDEN={'Presidente':0,'Vicepresidente':1,'Secretario':2};
var COM_ORDEN_TOP=['LA LIBERTAD AVANZA','UCR - UNION CIVICA RADICAL'];
var COM_ORDEN_BOTTOM=['CONVICCION FEDERAL','JUSTICIA SOCIAL FEDERAL','FRENTE CIVICO POR SANTIAGO','JUSTICIALISTA'];
function ordenIntegrante(m){
  if(CARGO_ORDEN.hasOwnProperty(m.rol))return CARGO_ORDEN[m.rol];
  var nb=normBloque(m.bloque);
  var top=COM_ORDEN_TOP.indexOf(nb);if(top>=0)return 10+top;
  var bot=COM_ORDEN_BOTTOM.indexOf(nb);if(bot>=0)return 1000+bot;
  return 100;
}
/* Integrantes reales + una fila placeholder por cada vacante (cupo - integrantes
   cargados), para que tanto la vista como el export a PDF muestren cuántos
   lugares quedan libres en la comisión, no sólo quién ya está. */
function conVacantes(c){
  var lista=c.integrantes.slice();
  var vac=(c.cupo||0)-lista.length;
  for(var k=0;k<vac;k++)lista.push({nombre:'Vacante',bloque:'',rol:'',vacante:true});
  return lista;
}
function renderIntegrantes(c){
  comisionAbierta=c;
  var conIdx=conVacantes(c).map(function(m,i){return {m:m,i:i};});
  conIdx.sort(function(a,b){
    if(!!a.m.vacante!==!!b.m.vacante)return a.m.vacante?1:-1;
    var oa=ordenIntegrante(a.m),ob=ordenIntegrante(b.m);
    if(oa!==ob)return oa-ob;
    return (a.m.nombre||'').localeCompare(b.m.nombre||'');
  });
  var html='';
  conIdx.forEach(function(pair){
    var m=pair.m,i=pair.i;
    if(m.vacante){
      html+='<div class="member-row member-row-vacante">'
        +'<span class="bloque-dot vacante-dot"></span>'
        +'<span class="member-name vacante-label">Vacante</span>'
        +'</div>';
      return;
    }
    var col=blqColor(m.bloque);
    var rolHtml=(m.rol&&m.rol!=='Vocal')?'<span class="rol-badge rol-'+m.rol+'">'+esc(m.rol)+'</span>':'';
    html+='<div class="member-row">'
      +avatarHtml(m.nombre,30)
      +'<span class="bloque-dot" style="background:'+col.dot+'"></span>'
      +'<span class="member-name">'+esc(m.nombre)+'</span>'
      +'<span class="btag" style="background:'+col.bg+';color:'+col.badge+'">'+esc(m.bloque)+'</span>'
      +rolHtml
      +(m.dpp?'<button class="dpp-badge" onclick="mostrarDppHist('+i+')" title="Ver historial de DPP">DPP-'+esc(m.dpp)+'</button>':'')
      +'</div>';
  });
  document.getElementById('com-integrantes-list').innerHTML=html||'<div class="com-empty">Sin integrantes cargados.</div>';
}
var DPP_TIPO_LABEL={add:'Designado/a',replace:'Designado/a',remove:'Dado/a de baja',rewrite:'Confirmado/a en recomposici&oacute;n'};
function abrirDppModal(titulo,hist){
  document.getElementById('dpp-modal-title').textContent=titulo;
  var body='';
  if(hist&&hist.length){
    hist.forEach(function(h){
      var detalle=DPP_TIPO_LABEL[h.tipo]||h.tipo;
      if(h.tipo==='replace'&&h.reemplaza)detalle+=' en reemplazo de '+esc(h.reemplaza);
      body+='<div class="dpp-hist-entry">'
        +'<div class="dpp-hist-dpp">DPP-'+esc(h.dpp)+(h.fecha?'<span class="dpp-hist-fecha">'+esc(h.fecha)+'</span>':'')+'</div>'
        +'<div class="dpp-hist-detalle">'+detalle+'</div>'
        +'</div>';
    });
  }else{
    body='<div class="com-empty">Miembro incorporado en la constituci&oacute;n original.</div>';
  }
  document.getElementById('dpp-modal-body').innerHTML=body;
  document.getElementById('dpp-modal-overlay').classList.add('open');
}
function mostrarDppHist(i){
  if(!comisionAbierta)return;
  var m=comisionAbierta.integrantes[i];
  if(!m)return;
  abrirDppModal(m.nombre+' — '+nombreCom(comisionAbierta.nombre),m.hist);
}
function cerrarDppModal(e){
  if(e&&e.target!==document.getElementById('dpp-modal-overlay'))return;
  document.getElementById('dpp-modal-overlay').classList.remove('open');
}

/* ── Ficha de proyecto (modal con stepper de estado parlamentario) ────── */
function fichaPasos(p){
  var pasos=[
    {label:'Ingreso',done:true,sub:p.fecha||''},
    {label:'En comisión',done:!!(p.comisiones&&p.comisiones.length),sub:(p.comisiones&&p.comisiones[0])?comLabel(p.comisiones[0]):''},
    {label:'Orden del Día',done:!!p.od,sub:p.od?('N° '+p.od.nro_od+'/'+String(p.od.anio_od).slice(-2)):''}
  ];
  var fin={label:'En trámite',done:false,sub:'',cls:''};
  if(p.sancionado){fin={label:'Sancionado',done:true,sub:p.ley_numero?('Ley '+p.ley_numero):(p.fecha_ley||''),cls:'final-sanc'};}
  else if(p.caduca){fin={label:'Caducado',done:true,sub:p.fecha_caduca||'',cls:'final-arch'};}
  else if(p.archivado){fin={label:'Archivado',done:true,sub:p.fecha_archivo||'',cls:'final-arch'};}
  pasos.push(fin);
  return pasos;
}
function abrirFicha(clave){
  var p=DATA_INDEX[clave];
  if(!p)return;
  var fg=TIPO_FG[p.tipo]||'#888',bg=TIPO_BG[p.tipo]||'#eee';
  document.getElementById('ficha-titulo').innerHTML='<span class="exp-badge" style="background:'+bg+';color:'+fg+'">'+esc(p.tipo)+'</span> '+esc(expNroOf(p))+(p.fecha?' &middot; '+esc(p.fecha):'');
  var stepHtml=fichaPasos(p).map(function(s){
    return '<div class="step-node'+(s.done?' done':'')+(s.cls?' '+s.cls:'')+'">'
      +'<div class="step-dot">'+(s.done?'&#10003;':'')+'</div>'
      +'<div class="step-label">'+esc(s.label)+'</div>'
      +(s.sub?'<div class="step-sub">'+esc(s.sub)+'</div>':'')
      +'</div>';
  }).join('');
  document.getElementById('ficha-stepper').innerHTML=stepHtml;
  var btags='';
  p.bloques.forEach(function(b){var c=blqColor(b);btags+='<span class="btag" style="background:'+c.bg+';color:'+c.badge+'">'+esc(b)+'</span>';});
  var kv=[];
  if(p.autores.length)kv.push(['Autor(es)',esc(p.autores.join(' · '))]);
  if(btags)kv.push(['Bloque(s)',btags]);
  if(p.provincias&&p.provincias.length)kv.push(['Provincia(s)',esc(p.provincias.join(' · '))]);
  if(p.comisiones.length)kv.push(['Comisiones',esc(p.comisiones.map(comLabel).join(' · '))]);
  if(p.dae)kv.push(['DAE',esc(p.dae)]);
  var links='';
  if(p.url)links+='<a class="am-link-btn" href="'+escAttr(p.url)+'" target="_blank" rel="noopener">&#128196; Ver expediente en el Senado</a>';
  if(p.od&&p.od.url_pdf)links+='<a class="am-link-btn" href="'+escAttr(p.od.url_pdf)+'" target="_blank" rel="noopener">&darr; Orden del D&iacute;a</a>';
  document.getElementById('ficha-body').innerHTML=
    '<div class="ficha-extracto">'+esc(p.extracto)+'</div>'
    +'<div class="ficha-kv">'+kv.map(function(r){return '<div class="ficha-kv-row"><span class="ficha-kv-label">'+r[0]+'</span><span class="ficha-kv-val">'+r[1]+'</span></div>';}).join('')+'</div>'
    +cardFooterHtml(p)
    +(links?'<div class="ficha-links">'+links+'</div>':'');
  document.getElementById('ficha-overlay').classList.add('open');
}
function cerrarFicha(e){
  if(e&&e.target!==document.getElementById('ficha-overlay'))return;
  document.getElementById('ficha-overlay').classList.remove('open');
}
function parseFechaDMY(fecha){
  var parts=(fecha||'').split('/');
  if(parts.length!==3)return null;
  return new Date(+parts[2],+parts[1]-1,+parts[0]);
}
/* ── Proyectos en trámite (por comisión, tarjetas estilo Ayuda Memoria) ── */
var COM_PROY_CATS=[
  {key:'PL',label:'Proyecto de Ley',tipos:['PL']},
  {key:'PC',label:'Proyecto de Comunicación',tipos:['PC']},
  {key:'PR',label:'Proyecto de Resolución',tipos:['PR']},
  {key:'Otros',label:'Otros',tipos:['PD','CA','CV']}
];
var comProyCategoria=null,comProyTratadosFiltro='todos',comProyListaActual=[];
function proyectosDeComision(c){
  var nom=normCom(c.nombre);
  return DATA.filter(function(p){
    var coms=p.comisiones||[];
    return coms.length&&normCom(coms[0])===nom;
  });
}
function reunionesCalificadas(p,comNombre){
  var nom=normCom(nombreCom(comNombre));
  return (p.reuniones||[]).filter(function(r){return r.tipo!=='asesores'&&normCom(nombreCom(r.comision))===nom});
}
/* A diferencia de "en trámite" (que sólo mira el 1er giro/cabecera), esto
   busca en TODO DATA: un proyecto puede tratarse en la reunión de una
   comisión aunque esa comisión sea un giro adicional, no la cabecera. */
function proyectosTratadosEnComision(comNombre){
  return DATA.filter(function(p){return reunionesCalificadas(p,comNombre).length});
}
function estadoTratado(p,comNombre){
  var rs=reunionesCalificadas(p,comNombre);
  if(!rs.length)return null;
  var hoy=new Date().toISOString().slice(0,10);
  var pasado=false,futuro=false;
  rs.forEach(function(r){
    if(!r.iso)return;
    var f=r.iso.slice(0,10);
    if(f<hoy)pasado=true;else futuro=true;
  });
  return {tratado:pasado,pendiente:!pasado&&futuro};
}
function initProyectosComision(c){
  comProyCategoria=null;
  comProyTratadosFiltro='todos';
  var proyectos=proyectosDeComision(c);
  var esComisionAcuerdos=normCom(c.nombre)==='DE ACUERDOS';
  var hayAcuerdos=proyectos.some(function(p){return p.tipo==='AC'});
  var cats=esComisionAcuerdos
    ? [{key:'AC',label:'Acuerdos',tipos:['AC']}]
    : COM_PROY_CATS.concat(hayAcuerdos?[{key:'AC',label:'Acuerdos',tipos:['AC']}]:[]);
  var tratadosCount=proyectosTratadosEnComision(c.nombre).length;
  var html=cats.map(function(cat){
    var n=proyectos.filter(function(p){return cat.tipos.indexOf(p.tipo)>=0}).length;
    return '<button class="com-proy-cat-btn" data-catkey="'+cat.key+'" onclick="selectComProyCategoria(\''+cat.key+'\')">'+esc(cat.label)+' <span class="cnt">('+n+')</span></button>';
  }).join('')
  +'<button class="com-proy-cat-btn" data-catkey="Tratados" onclick="selectComProyCategoria(\'Tratados\')">Tratadas en reunión de senadores <span class="cnt">('+tratadosCount+')</span></button>';
  document.getElementById('com-proy-cats').innerHTML=html;
  document.getElementById('com-proy-tratados-chips').style.display='none';
  document.getElementById('com-proy-tratados-chips').innerHTML='';
  document.getElementById('com-proy-grid').innerHTML='';
}
function selectComProyCategoria(key){
  comProyCategoria=key;
  comProyTratadosFiltro='todos';
  document.querySelectorAll('#com-proy-cats .com-proy-cat-btn').forEach(function(b){
    b.classList.toggle('active',b.getAttribute('data-catkey')===key);
  });
  renderComProyGrid();
}
function renderComProyTratadosChips(){
  var el=document.getElementById('com-proy-tratados-chips');
  if(comProyCategoria!=='Tratados'){el.style.display='none';el.innerHTML='';return}
  var opts=[['todos','Todos'],['tratados','Ya tratados'],['pendientes','Pendientes de tratar']];
  el.style.display='flex';
  el.innerHTML=opts.map(function(o){
    return '<button class="chip'+(comProyTratadosFiltro===o[0]?' on':'')+'" onclick="setComProyTratadosFiltro(\''+o[0]+'\')">'+o[1]+'</button>';
  }).join('');
}
function setComProyTratadosFiltro(v){
  comProyTratadosFiltro=v;
  renderComProyGrid();
}
function renderComProyGrid(){
  var c=comisionAbierta;
  var grid=document.getElementById('com-proy-grid');
  if(!c||!comProyCategoria){grid.innerHTML='';return}
  var proyectos=proyectosDeComision(c);
  var cat=COM_PROY_CATS.concat([{key:'AC',tipos:['AC']}]).filter(function(x){return x.key===comProyCategoria})[0];
  var lista;
  if(comProyCategoria==='Tratados'){
    lista=proyectosTratadosEnComision(c.nombre);
    if(comProyTratadosFiltro!=='todos'){
      lista=lista.filter(function(p){
        var est=estadoTratado(p,c.nombre);
        return comProyTratadosFiltro==='tratados'?(est&&est.tratado):(est&&est.pendiente);
      });
    }
  }else{
    lista=proyectos.filter(function(p){return cat&&cat.tipos.indexOf(p.tipo)>=0});
  }
  renderComProyTratadosChips();
  lista.sort(function(a,b){
    var da=parseFechaDMY(a.fecha),db=parseFechaDMY(b.fecha);
    return (db?db.getTime():0)-(da?da.getTime():0);
  });
  comProyListaActual=lista;
  if(!lista.length){grid.innerHTML='<div class="com-empty">No hay proyectos para este filtro.</div>';return}
  grid.innerHTML=lista.map(function(p,i){return buildComProyCard(p,i,c.nombre)}).join('');
}
function buildComProyCard(p,idx,comNombre){
  var fg=TIPO_FG[p.tipo]||'#888',bg=TIPO_BG[p.tipo]||'#eee';
  var expNro=p.origen+'-'+p.nro+'/'+String(p.anio).slice(-2);
  var autor=p.autores&&p.autores[0]?p.autores[0]:'';
  var bloque=p.bloques&&p.bloques[0]?p.bloques[0]:'';
  var col=blqColor(bloque);
  var tratadoTag='';
  if(comProyCategoria==='Tratados'){
    var est=estadoTratado(p,comNombre);
    if(est)tratadoTag='<span class="com-tratado-tag '+(est.tratado?'ok':'pend')+'">'+(est.tratado?'Ya tratado':'Pendiente')+'</span>';
  }
  var badgesHtml=cardBadgesHtml(p);
  return '<div class="am-card" onclick="irAExpedienteComision('+idx+')">'
    +'<div class="am-card-top"><span class="am-badge" style="background:'+bg+';color:'+fg+'">'+esc(p.tipo)+'</span><span class="am-exp-num">'+esc(expNro)+'</span></div>'
    +(autor?'<div class="am-autor">'+esc(autor)+'</div>':'')
    +'<p class="am-desc">'+esc(p.extracto)+'</p>'
    +'<div class="am-card-bottom">'
    +(bloque?'<span class="btag" style="background:'+col.bg+';color:'+col.badge+'">'+esc(bloque)+'</span>':'<span></span>')
    +tratadoTag
    +'</div>'
    +(badgesHtml?'<div class="am-card-footer">'+badgesHtml+'</div>':'')
    +'</div>';
}
function irAExpedienteComision(idx){
  var p=comProyListaActual[idx];
  if(!p)return;
  irAExpediente(p.origen+'-'+p.nro+'/'+String(p.anio).slice(-2));
}
var COM_NOMBRE_CORTO={
  'De Economías Regionales, Economía Social, Micro, Pequeña y Mediana Empresa':'Ec. Regionales',
  'De Sistemas, Medios de Comunicación y Libertad de Expresión':'Sistemas y Medios',
  'De Coparticipación Federal de Impuestos':'Coparticipación',
  'De Infraestructura, Vivienda y Transporte':'Infraestructura',
  'De Asuntos Administrativos y Municipales':'Asuntos Adm.',
  'De Asuntos Constitucionales':'Constitucionales',
  'De Seguridad Interior y Narcotráfico':'Seg. Interior',
  'De Relaciones Exteriores y Culto':'RR.EE. y Culto',
  'De Población y Desarrollo Humano':'Pob. y Des. Humano',
  'De Trabajo y Previsión Social':'Trabajo',
  'De Minería, Energía y Combustibles':'Minería',
  'De Agricultura, Ganadería y Pesca':'Agricultura',
  'De Ambiente y Desarrollo Sustentable':'Ambiente',
  'De Economía Nacional e Inversión':'Ec. Nacional',
  'De Derechos y Garantías':'Der. y Garantías',
  'De Defensa Nacional':'Defensa',
  'De Educación y Cultura':'Educación',
  'De Industria y Comercio':'Industria',
  'De Legislación General':'Legislación',
  'De Ciencia y Tecnología':'Ciencia',
  'De Justicia y Asuntos Penales':'Justicia Penal'
};
function nombreComCorto(nombre){return COM_NOMBRE_CORTO[nombre]||nombreCom(nombre)}

/* ── Proyección de votación (adaptado de comisiones-senado) ───────────── */
var PROY_VOTOS={};
var _PROY_BLOQUE_IDX={};
function renderProyeccion(){
  var c=comisionAbierta;
  var tbody=document.getElementById('proyTableBody');
  var panel=document.getElementById('proyBloquePanel');
  Object.keys(PROY_VOTOS).forEach(function(k){delete PROY_VOTOS[k]});
  Object.keys(_PROY_BLOQUE_IDX).forEach(function(k){delete _PROY_BLOQUE_IDX[k]});
  var integrantes=(c&&c.integrantes)||[];
  if(!integrantes.length){
    tbody.innerHTML='<tr><td colspan="5" class="proy-empty">Sin integrantes cargados.</td></tr>';
    if(panel)panel.style.display='none';
    updateDictamenBanner();
    return;
  }
  integrantes.forEach(function(m,i){
    if(!_PROY_BLOQUE_IDX[m.bloque])_PROY_BLOQUE_IDX[m.bloque]=[];
    _PROY_BLOQUE_IDX[m.bloque].push(i);
  });
  if(panel){
    var bloques=[];
    integrantes.forEach(function(m){if(bloques.indexOf(m.bloque)<0)bloques.push(m.bloque)});
    panel.innerHTML='<div class="proy-bloque-panel-title">Posicionamiento por bloque</div>'
      +bloques.map(function(b,bi){
        var bc=blqColor(b);
        var cnt=_PROY_BLOQUE_IDX[b].length;
        return '<div class="proy-bloque-row">'
          +'<div class="proy-bloque-name"><span class="bloque-dot" style="background:'+bc.dot+'"></span>'+esc(b)+'<span style="font-size:10px;color:#9CA3AF;margin-left:4px">('+cnt+')</span></div>'
          +'<div class="proy-vote-btns">'
          +'<button class="vote-btn mayoria" onclick="setVotoBloque('+bi+',\'mayoria\')">Mayor&iacute;a</button>'
          +'<button class="vote-btn mayoria_dis" onclick="setVotoBloque('+bi+',\'mayoria_dis\')">May. c/ disidencia</button>'
          +'<button class="vote-btn minoria" onclick="setVotoBloque('+bi+',\'minoria\')">Minor&iacute;a</button>'
          +'<button class="vote-btn sin" onclick="setVotoBloque('+bi+',\'sin\')">Sin definir</button>'
          +'</div></div>';
      }).join('');
    panel.style.display='block';
    panel._bloques=bloques;
  }
  tbody.innerHTML=integrantes.map(function(m,i){
    PROY_VOTOS[i]='sin';
    var bc=blqColor(m.bloque);
    var cLabel=(m.rol&&m.rol!=='Vocal')?m.rol:'';
    return '<tr id="proy-row-'+i+'">'
      +'<td><span class="bloque-dot" style="background:'+bc.dot+'"></span></td>'
      +'<td style="font-weight:500">'+esc(m.nombre)+'</td>'
      +'<td><span style="font-size:11px;padding:2px 7px;border-radius:10px;background:'+bc.bg+';color:'+bc.badge+'">'+esc(m.bloque)+'</span></td>'
      +'<td style="font-size:11px;color:#6B7280">'+esc(cLabel)+'</td>'
      +'<td><div class="proy-vote-btns">'
      +'<button class="vote-btn mayoria" onclick="setVoto('+i+',\'mayoria\')">Mayor&iacute;a</button>'
      +'<button class="vote-btn mayoria_dis" onclick="setVoto('+i+',\'mayoria_dis\')">May. c/ disidencia</button>'
      +'<button class="vote-btn minoria" onclick="setVoto('+i+',\'minoria\')">Minor&iacute;a</button>'
      +'<button class="vote-btn sin active" onclick="setVoto('+i+',\'sin\')">Sin definir</button>'
      +'</div></td></tr>';
  }).join('');
  updateDictamenBanner();
}
function setVotoBloque(bloqueIdx,voto){
  var panel=document.getElementById('proyBloquePanel');
  var bloque=panel&&panel._bloques?panel._bloques[bloqueIdx]:null;
  if(!bloque)return;
  (_PROY_BLOQUE_IDX[bloque]||[]).forEach(function(i){setVoto(i,voto)});
}
function setVoto(idx,voto){
  PROY_VOTOS[idx]=voto;
  var row=document.getElementById('proy-row-'+idx);
  if(!row)return;
  row.querySelectorAll('.vote-btn').forEach(function(b){
    b.classList.remove('active');
    if(b.classList.contains(voto))b.classList.add('active');
  });
  updateDictamenBanner();
}
function resetProyVotos(){
  Object.keys(PROY_VOTOS).forEach(function(k){
    PROY_VOTOS[k]='sin';
    var row=document.getElementById('proy-row-'+k);
    if(row){
      row.querySelectorAll('.vote-btn').forEach(function(b){
        b.classList.remove('active');
        if(b.classList.contains('sin'))b.classList.add('active');
      });
    }
  });
  updateDictamenBanner();
}
function updateDictamenBanner(){
  var vals=Object.values(PROY_VOTOS);
  var total=vals.length;
  var mayoria=vals.filter(function(v){return v==='mayoria'}).length;
  var mayoriaDis=vals.filter(function(v){return v==='mayoria_dis'}).length;
  var minoria=vals.filter(function(v){return v==='minoria'}).length;
  var sin=vals.filter(function(v){return v==='sin'}).length;
  var mayoriaAbsoluta=total>0?Math.floor(total/2)+1:1;
  var hayDictamen=(mayoria+mayoriaDis)>=mayoriaAbsoluta&&total>0;
  var banner=document.getElementById('dictamenBanner');
  if(!banner)return;
  banner.className='dictamen-banner '+(hayDictamen?'hay-dictamen':'no-dictamen');
  document.getElementById('dictamenStatus').textContent=hayDictamen?'HAY DICTAMEN':'NO HAY DICTAMEN';
  document.getElementById('dictamenCounter').innerHTML=
    '<span style="color:#059669">'+mayoria+' mayoría</span> · <span style="color:#D97706">'+mayoriaDis+' may. c/ disidencia</span> · <span style="color:#DC2626">'+minoria+' minoría</span> · '+sin+' sin definir · '+total+' total';
  document.getElementById('proyMayoriaLabel').textContent=total>0?'Mayoría absoluta: '+mayoriaAbsoluta+' votos':'';
}
function exportProyPdf(){
  var jsPDFLib=window.jspdf;
  if(!jsPDFLib){alert('Error: jsPDF no cargó correctamente.');return;}
  var jsPDF=jsPDFLib.jsPDF;
  var c=comisionAbierta;
  if(!c){alert('Abrí una comisión primero.');return;}
  var tema=document.getElementById('proyTema').value||'Sin especificar';
  var rows=document.querySelectorAll('#proyTableBody tr[id^="proy-row-"]');
  if(!rows.length){alert('No hay integrantes para exportar.');return;}
  var doc=new jsPDF({orientation:'portrait',unit:'mm',format:'a4'});
  loadPoppins(doc);
  var W=210,H=297,ML=15,MR=15;
  var BLUE=[27,94,162];var BLUE_LT=[214,228,240];var WHITE=[255,255,255];
  var d=new Date();
  var TODAY=d.getDate()+' de '+MESES_LARGO[d.getMonth()]+' de '+d.getFullYear();
  doc.setFillColor(BLUE[0],BLUE[1],BLUE[2]);doc.rect(0,0,W,18,'F');
  doc.setTextColor(WHITE[0],WHITE[1],WHITE[2]);
  doc.setFont('Poppins','normal');doc.setFontSize(7);
  doc.text('SENADO DE LA NACIÓN',ML,6.5);
  doc.setFont('Poppins','bold');doc.setFontSize(9.5);
  doc.text('PROSECRETARÍA PARLAMENTARIA',ML,13);
  doc.setFont('Poppins','normal');doc.setFontSize(7);
  doc.text('PROYECCIÓN DE VOTACIÓN',W-MR,6.5,{align:'right'});
  doc.text(TODAY,W-MR,13,{align:'right'});
  doc.setFillColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);doc.rect(0,18,W,0.8,'F');
  var y=26;
  doc.setFont('Poppins','bold');doc.setFontSize(12);doc.setTextColor(BLUE[0],BLUE[1],BLUE[2]);
  var titleLines=doc.splitTextToSize(nombreCom(c.nombre),180);
  titleLines.forEach(function(l){doc.text(l,ML,y);y+=6;});
  y+=2;
  doc.setFont('Poppins','normal');doc.setFontSize(9);doc.setTextColor(74,74,74);
  doc.text('Tema: '+tema,ML,y);y+=5;
  var vals=Object.values(PROY_VOTOS);
  var total=vals.length;
  var nMayoria=vals.filter(function(v){return v==='mayoria'}).length;
  var nMayoriaDis=vals.filter(function(v){return v==='mayoria_dis'}).length;
  var nMinoria=vals.filter(function(v){return v==='minoria'}).length;
  var nSin=vals.filter(function(v){return v==='sin'}).length;
  var mayoriaAbsoluta=Math.floor(total/2)+1;
  var hayDictamen=(nMayoria+nMayoriaDis)>=mayoriaAbsoluta&&total>0;
  y+=3;
  var dictColor=hayDictamen?[6,95,70]:[153,27,27];
  var dictBg=hayDictamen?[209,250,229]:[254,226,226];
  doc.setFillColor(dictBg[0],dictBg[1],dictBg[2]);doc.rect(ML,y-5,W-ML-MR,10,'F');
  doc.setFont('Poppins','bold');doc.setFontSize(13);doc.setTextColor(dictColor[0],dictColor[1],dictColor[2]);
  doc.text(hayDictamen?'HAY DICTAMEN':'NO HAY DICTAMEN',W/2,y+1,{align:'center'});
  y+=9;
  doc.setFont('Poppins','normal');doc.setFontSize(9);doc.setTextColor(74,74,74);
  doc.text(nMayoria+' mayoría · '+nMayoriaDis+' may. c/ disidencia · '+nMinoria+' minoría · '+nSin+' sin definir · '+total+' total',W/2,y,{align:'center'});
  y+=8;
  doc.setFillColor(BLUE[0],BLUE[1],BLUE[2]);doc.rect(ML,y,W-ML-MR,6,'F');
  doc.setTextColor(WHITE[0],WHITE[1],WHITE[2]);doc.setFont('Poppins','bold');doc.setFontSize(7.5);
  doc.text('NOMBRE',ML+2,y+4);doc.text('BLOQUE',ML+75,y+4);doc.text('CARGO',ML+130,y+4);doc.text('POSICIÓN',W-MR-2,y+4,{align:'right'});
  y+=8;
  var idx=0;
  while(true){
    var row=document.getElementById('proy-row-'+idx);
    if(!row)break;
    if(y>H-20){
      doc.setDrawColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);doc.setLineWidth(0.3);doc.line(ML,H-9,W-MR,H-9);
      doc.setFont('Poppins','normal');doc.setFontSize(7);doc.setTextColor(150,150,150);
      doc.text('Prosecretaría Parlamentaria',ML,H-5);doc.text(TODAY,W-MR,H-5,{align:'right'});
      doc.addPage();
      y=22;
      doc.setFillColor(BLUE[0],BLUE[1],BLUE[2]);doc.rect(ML,y,W-ML-MR,6,'F');
      doc.setTextColor(WHITE[0],WHITE[1],WHITE[2]);doc.setFont('Poppins','bold');doc.setFontSize(7.5);
      doc.text('NOMBRE',ML+2,y+4);doc.text('BLOQUE',ML+75,y+4);doc.text('CARGO',ML+130,y+4);doc.text('POSICIÓN',W-MR-2,y+4,{align:'right'});
      y+=8;
    }
    if(idx%2===0){doc.setFillColor(248,250,255);doc.rect(ML,y-3,W-ML-MR,6,'F');}
    var voto=PROY_VOTOS[idx]||'sin';
    var votoLabel=voto==='mayoria'?'Mayoría':voto==='mayoria_dis'?'May. c/ disidencia':voto==='minoria'?'Minoría':'Sin definir';
    var votoColor=voto==='mayoria'?[5,150,105]:voto==='mayoria_dis'?[217,119,6]:voto==='minoria'?[220,38,38]:[156,163,175];
    var cells=row.querySelectorAll('td');
    var nombre=cells[1]?cells[1].textContent.trim():'';
    var bloque=cells[2]?cells[2].textContent.trim():'';
    var cargo=cells[3]?cells[3].textContent.trim():'';
    doc.setFont('Poppins','normal');doc.setFontSize(8);doc.setTextColor(74,74,74);
    doc.text(nombre.substring(0,40),ML+2,y+1);
    doc.text(bloque.substring(0,28),ML+75,y+1);
    doc.text(cargo.substring(0,20),ML+130,y+1);
    doc.setTextColor(votoColor[0],votoColor[1],votoColor[2]);doc.setFont('Poppins','bold');
    doc.text(votoLabel,W-MR-2,y+1,{align:'right'});
    y+=6;idx++;
  }
  doc.setDrawColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);doc.setLineWidth(0.3);doc.line(ML,H-9,W-MR,H-9);
  doc.setFont('Poppins','normal');doc.setFontSize(7);doc.setTextColor(150,150,150);
  doc.text('Prosecretaría Parlamentaria',ML,H-5);doc.text(TODAY,W-MR,H-5,{align:'right'});
  doc.save('proyeccion-'+nombreCom(c.nombre).replace(/[^a-zA-Z0-9]/g,'-').substring(0,30)+'.pdf');
}

function renderRepresentacion(){
  var totalSenadores=0;
  Object.keys(BLOQUE_TOTALES).forEach(function(b){totalSenadores+=BLOQUE_TOTALES[b]});
  var bloques=Object.keys(BLOQUE_TOTALES).sort(function(a,b){return BLOQUE_TOTALES[b]-BLOQUE_TOTALES[a]});

  var globalHtml='<div class="repr-titulo">Resumen global</div>'
    +'<p class="repr-hint">"Com. de 17" y "Com. de 19" son las bancas proporcionales seg&uacute;n el peso de cada bloque en la c&aacute;mara (senadores &divide; '+totalSenadores+' &times; cupo).</p>'
    +'<div class="repr-wrap"><table class="repr-table"><thead><tr>'
    +'<th>Bloque</th><th class="num">Senadores</th><th class="num">% c&aacute;mara</th>'
    +'<th class="num">Com. de 17</th><th class="num">Com. de 19</th>'
    +'</tr></thead><tbody>';
  bloques.forEach(function(b){
    var total=BLOQUE_TOTALES[b];
    var pct=(total/totalSenadores*100).toFixed(2);
    var exp17=(total/totalSenadores*17).toFixed(2);
    var exp19=(total/totalSenadores*19).toFixed(2);
    var col=getBloqueColor(b);
    globalHtml+='<tr><td><div class="repr-bloque-cell"><span class="repr-dot" style="background:'+col+'"></span>'+esc(b)+'</div></td>'
      +'<td class="num">'+total+'</td><td class="num">'+pct+'%</td>'
      +'<td class="num">'+exp17+'</td><td class="num">'+exp19+'</td></tr>';
  });
  globalHtml+='</tbody></table></div>';
  document.getElementById('repr-global').innerHTML=globalHtml;

  var crossHtml='<div class="repr-titulo">Integrantes por bloque y comisi&oacute;n</div>'
    +'<p class="repr-hint">Desplaz&aacute; horizontalmente para ver todas las comisiones.</p>'
    +'<div class="repr-wrap"><table class="cross-table"><thead><tr><th class="blq-col">Bloque</th>';
  COMISIONES.forEach(function(c){crossHtml+='<th class="com-col"><span>'+esc(nombreComCorto(c.nombre))+'</span></th>'});
  crossHtml+='</tr></thead><tbody>';
  bloques.forEach(function(b){
    crossHtml+='<tr><td class="blq-name">'+esc(b)+'</td>';
    COMISIONES.forEach(function(c){
      var n=c.integrantes.filter(function(m){return m.bloque===b}).length;
      crossHtml+='<td class="val" style="color:'+(n>0?'#4A4A4A':'#cfd8e3')+';font-weight:'+(n>0?'600':'400')+'">'+(n>0?n:'&mdash;')+'</td>';
    });
    crossHtml+='</tr>';
  });
  crossHtml+='<tr class="cross-vacantes"><td class="blq-name">Vacantes</td>';
  COMISIONES.forEach(function(c){
    var v=c.cupo-c.integrantes.length;
    crossHtml+='<td class="val" style="color:'+(v>0?'#B91C1C':'#cfd8e3')+';font-weight:'+(v>0?'700':'400')+'">'+(v>0?v:'&mdash;')+'</td>';
  });
  crossHtml+='</tr>';
  crossHtml+='</tbody></table></div>';
  document.getElementById('repr-cross').innerHTML=crossHtml;
}
/* ── Estadísticas > Por senador/a: invierte COMISIONES (comisión→integrantes)
   a senador→comisiones en el cliente, sin tocar data/comisiones.json ──── */
function renderComisionesPorSenador(){
  var grid=document.getElementById('senador-grid');
  if(!grid)return;
  var q=(document.getElementById('senador-search').value||'').toLowerCase().trim();
  var porSenador={};
  COMISIONES.forEach(function(c){
    c.integrantes.forEach(function(m){
      if(!porSenador[m.nombre])porSenador[m.nombre]={bloque:m.bloque,comisiones:[]};
      porSenador[m.nombre].comisiones.push({nombre:c.nombre,rol:m.rol,dpp:m.dpp,hist:m.hist});
    });
  });
  var nombres=Object.keys(porSenador).sort(function(a,b){return a.localeCompare(b,'es')});
  if(q)nombres=nombres.filter(function(n){return n.toLowerCase().indexOf(q)>=0});
  if(!nombres.length){grid.innerHTML='<div class="com-empty">Sin resultados para este filtro.</div>';return}
  var html='';
  nombres.forEach(function(nombre){
    var d=porSenador[nombre],col=blqColor(d.bloque);
    var chips=d.comisiones.map(function(cm,i){
      var rolTxt=(cm.rol&&cm.rol!=='Vocal')?' &middot; '+esc(cm.rol):'';
      return '<button class="chip" onclick="mostrarDppHistDirecto(\''+jsStr(nombre)+'\','+i+')">'+esc(nombreComCorto(cm.nombre))+rolTxt+'</button>';
    }).join('');
    html+='<div class="senator-card"><div class="senator-name">'+esc(nombre)+'</div>'
      +'<span class="senator-bloque-tag" style="background:'+col.bg+';color:'+col.badge+'">'+esc(d.bloque)+'</span>'
      +'<div class="senator-chips">'+chips+'</div>'
      +'<div class="senator-count">'+d.comisiones.length+' comisi&oacute;n'+(d.comisiones.length!==1?'es':'')+'</div></div>';
  });
  grid.innerHTML=html;
}
function mostrarDppHistDirecto(nombre,i){
  var porSenador={};
  COMISIONES.forEach(function(c){
    c.integrantes.forEach(function(m){
      if(!porSenador[m.nombre])porSenador[m.nombre]=[];
      porSenador[m.nombre].push({nombre:c.nombre,dpp:m.dpp,hist:m.hist});
    });
  });
  var cm=(porSenador[nombre]||[])[i];
  if(!cm)return;
  abrirDppModal(nombre+' — '+nombreCom(cm.nombre),cm.hist);
}
/* ── Exportar integrantes de la comisión abierta a PDF (diseño del
      repo comisiones-senado, adaptado a una sola comisión) ──────── */
function loadPoppins(doc){
  doc.addFileToVFS('Poppins-Regular.ttf',FONT_POPPINS_REGULAR);
  doc.addFont('Poppins-Regular.ttf','Poppins','normal');
  doc.addFileToVFS('Poppins-Bold.ttf',FONT_POPPINS_BOLD);
  doc.addFont('Poppins-Bold.ttf','Poppins','bold');
}
function exportarComisionPdf(){
  var c=comisionAbierta;
  if(!c)return;
  var jsPDFLib=window.jspdf;
  if(!jsPDFLib){alert('Error: jsPDF no cargó correctamente.');return}
  var jsPDF=jsPDFLib.jsPDF;
  var doc=new jsPDF({orientation:'portrait',unit:'mm',format:'a4'});
  loadPoppins(doc);
  var W=210,H=297,ML=15,MR=15,pageW=180;
  var BLUE=[27,94,162],BLUE_LT=[214,228,240],GRAY=[74,74,74],WHITE=[255,255,255];
  var d=new Date();
  var months=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
  var TODAY=d.getDate()+' de '+months[d.getMonth()]+' de '+d.getFullYear();
  var pageNum=1,y=22,BOTTOM=H-14;

  function drawHeader(){
    doc.setFillColor(BLUE[0],BLUE[1],BLUE[2]);
    doc.rect(0,0,W,18,'F');
    doc.setTextColor(WHITE[0],WHITE[1],WHITE[2]);
    doc.setFont('Poppins','normal');doc.setFontSize(7);
    doc.text('SENADO DE LA NACIÓN ARGENTINA',ML,6.5);
    doc.setFont('Poppins','bold');doc.setFontSize(9.5);
    doc.text('PROSECRETARÍA PARLAMENTARIA',ML,13);
    doc.setFont('Poppins','normal');doc.setFontSize(7);
    doc.text('INTEGRACIÓN DE COMISIONES · PERÍODO 2026',W-MR,6.5,{align:'right'});
    doc.text(TODAY,W-MR,13,{align:'right'});
    doc.setFillColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);
    doc.rect(0,18,W,0.8,'F');
  }
  function drawFooter(n,total){
    doc.setDrawColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);doc.setLineWidth(0.3);
    doc.line(ML,H-9,W-MR,H-9);
    doc.setFont('Poppins','normal');doc.setFontSize(7);doc.setTextColor(150,150,150);
    doc.text('Prosecretaría Parlamentaria · Senado de la Nación Argentina',ML,H-5);
    doc.text('Página '+n+' de '+total,W/2,H-5,{align:'center'});
    doc.text('Documento generado automáticamente',W-MR,H-5,{align:'right'});
  }
  function checkPage(needed){
    if(y+needed>BOTTOM){doc.addPage();pageNum++;drawHeader();y=22;}
  }

  drawHeader();
  var ROW_H=7;
  checkPage(22);

  doc.setFillColor(BLUE[0],BLUE[1],BLUE[2]);
  doc.rect(ML,y,pageW,13,'F');
  doc.setFont('Poppins','bold');doc.setFontSize(11);
  doc.setTextColor(WHITE[0],WHITE[1],WHITE[2]);
  var nameLines=doc.splitTextToSize(c.nombre,pageW-30);
  doc.text(nameLines[0],ML+3,y+8.5);
  doc.setFont('Poppins','normal');doc.setFontSize(8);
  doc.setTextColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);
  var vacantes=Math.max(0,(c.cupo||0)-c.integrantes.length);
  var totalTxt=vacantes>0
    ?(c.integrantes.length+' de '+c.cupo+' integrantes · '+vacantes+' vacante'+(vacantes!==1?'s':''))
    :(c.integrantes.length+' integrantes');
  doc.text(totalTxt,W-MR-3,y+8.5,{align:'right'});
  y+=14;

  doc.setFillColor(BLUE_LT[0],BLUE_LT[1],BLUE_LT[2]);
  doc.rect(ML,y,pageW,6.5,'F');
  doc.setFont('Poppins','bold');doc.setFontSize(7.5);
  doc.setTextColor(BLUE[0],BLUE[1],BLUE[2]);
  doc.text('SENADOR/A',ML+8,y+4.5);
  doc.text('BLOQUE',ML+80,y+4.5);
  doc.text('CARGO',ML+133,y+4.5);
  doc.text('DPP',W-MR-3,y+4.5,{align:'right'});
  y+=6.5;

  conVacantes(c).forEach(function(m,i){
    checkPage(ROW_H);
    if(i%2===0){doc.setFillColor(248,250,252);doc.rect(ML,y,pageW,ROW_H,'F');}
    if(m.vacante){
      doc.setDrawColor(176,186,197);doc.setLineWidth(0.3);
      doc.circle(ML+4.5,y+ROW_H/2,1.4,'S');
      doc.setFont('Poppins','normal');doc.setFontSize(8.5);
      doc.setTextColor(154,161,166);
      doc.text('Vacante',ML+8,y+ROW_H/2+1.3);
      doc.setDrawColor(241,245,249);doc.setLineWidth(0.2);
      doc.line(ML,y+ROW_H,W-MR,y+ROW_H);
      y+=ROW_H;
      return;
    }
    var bc=blqColor(m.bloque);
    var hex=bc.dot.replace('#','');
    doc.setFillColor(parseInt(hex.substring(0,2),16),parseInt(hex.substring(2,4),16),parseInt(hex.substring(4,6),16));
    doc.circle(ML+4.5,y+ROW_H/2,1.4,'F');
    doc.setFont('Poppins','normal');doc.setFontSize(8.5);
    doc.setTextColor(GRAY[0],GRAY[1],GRAY[2]);
    doc.text(m.nombre,ML+8,y+ROW_H/2+1.3);
    doc.setFontSize(7.5);doc.setTextColor(100,100,100);
    var bname=m.bloque||'';
    doc.text(bname.length>26?bname.substring(0,24)+'…':bname,ML+80,y+ROW_H/2+1.3);
    doc.setFont('Poppins','bold');doc.setFontSize(7.5);
    if(m.rol==='Presidente'){doc.setTextColor(30,64,175);doc.text('Presidente/a',ML+133,y+ROW_H/2+1.3);}
    else if(m.rol==='Vicepresidente'){doc.setTextColor(124,58,237);doc.text('Vicepresidente/a',ML+133,y+ROW_H/2+1.3);}
    else if(m.rol==='Secretario'){doc.setTextColor(6,95,70);doc.text('Secretario/a',ML+133,y+ROW_H/2+1.3);}
    else{doc.setTextColor(150,150,150);doc.text('Vocal',ML+133,y+ROW_H/2+1.3);}
    doc.setFont('Poppins','normal');doc.setTextColor(GRAY[0],GRAY[1],GRAY[2]);
    if(m.dpp){
      doc.setFillColor(255,243,205);
      doc.roundedRect(W-MR-19,y+1.5,17,4,1,1,'F');
      doc.setFont('Poppins','bold');doc.setFontSize(6.5);
      doc.setTextColor(122,82,0);
      doc.text('DPP-'+m.dpp,W-MR-10.5,y+ROW_H/2+0.8,{align:'center'});
      doc.setFont('Poppins','normal');doc.setTextColor(GRAY[0],GRAY[1],GRAY[2]);
    }
    doc.setDrawColor(241,245,249);doc.setLineWidth(0.2);
    doc.line(ML,y+ROW_H,W-MR,y+ROW_H);
    y+=ROW_H;
  });

  var totalPages=pageNum;
  for(var p=1;p<=totalPages;p++){doc.setPage(p);drawFooter(p,totalPages);}
  var fileName=nombreCom(c.nombre).trim().replace(/[\s,]/g,'_').replace(/_+/g,'_').substring(0,40)+'.pdf';
  doc.save(fileName);
}
function renderProximaReunion(c){
  var el=document.getElementById('com-proxima-reunion');
  var r=c.proximaReunion;
  if(!r){el.innerHTML='';return}
  el.innerHTML='<div class="com-proximareunion">'
    +'<span>&#128197; <strong>Pr&oacute;xima reuni&oacute;n:</strong> '+esc(r.fecha)+' &middot; '+esc(r.hora)+' hs</span>'
    +'<span>&#128205; '+esc(r.salon)+'</span>'
    +'<span>&#128196; '+r.nExpedientes+' expediente'+(r.nExpedientes!==1?'s':'')+' en el temario</span>'
    +'</div>';
}

/* ── Agenda de reuniones ──────────────────────────────────────────── */
function reunionTime(r){
  var t=r.fecha_iso?new Date(r.fecha_iso).getTime():NaN;
  return isNaN(t)?-Infinity:t;
}
function chevron(){return '<span class="agenda-chevron">&#9656;</span>';}
function toggleColapso(headEl){
  var wrap=headEl.parentNode;
  if(wrap)wrap.classList.toggle('collapsed');
}
function plenariaBadge(r){
  return (r.comisiones&&r.comisiones.length>1)?'<span class="plenaria-badge">Plenaria</span>':'';
}
function suspendidaBadge(r){
  return r.suspendida?'<span class="suspendida-badge" title="Figuraba en un bolet&iacute;n anterior y desapareci&oacute; de la agenda">Suspendida</span>':'';
}
function editadaBadge(r){
  if(r.creada)return '<span class="editada-badge" title="Cargada a mano desde el Editor de Agenda, sin bolet&iacute;n de origen">&#10133; Creada</span>';
  return r.editada?'<span class="editada-badge" title="Corregida a mano despu&eacute;s del bolet&iacute;n, desde el Editor de Agenda">&#9998; Editada</span>':'';
}
function horaConCorreccion(r){
  if(r.hora_boletin)return '<span class="hora-vieja">'+esc(r.hora_boletin)+'</span> &rarr; <span class="hora-nueva">'+esc(r.hora)+'</span>';
  return esc(r.hora);
}
function agendaCardsHtml(arr,isPast){
  var h='';
  arr.forEach(function(r){h+=buildReunionCard(r,AGENDA.indexOf(r),isPast);});
  return h;
}
function agendaGrupoHtml(titulo,arr,isPast){
  if(!arr.length)return '';
  var cards=agendaCardsHtml(arr,isPast);
  var count=' <span class="agenda-grupo-count">('+arr.length+')</span>';
  /* Las pasadas van colapsadas por defecto (lista larga de referencia) */
  if(isPast){
    return '<div class="agenda-colapsable collapsed">'
      +'<div class="agenda-grupo-title colapsable-head" onclick="toggleColapso(this)">'+chevron()+esc(titulo)+count+'</div>'
      +'<div class="agenda-colapsable-body">'+cards+'</div>'
      +'</div>';
  }
  return '<div class="agenda-grupo-title">'+esc(titulo)+count+'</div>'+cards;
}
function buildReunionCard(r,idx,isPast){
  var tl=REUNION_TIPO_LABEL[r.tipo]||r.tipo;
  var col=REUNION_TIPO_COLOR[r.tipo]||{fg:'#888',bg:'#eee'};
  var coms=(r.comisiones||[]).map(esc).join(' &middot; ');
  return '<div class="agenda-card'+(isPast?' agenda-pasada':'')+(r.suspendida?' agenda-suspendida':'')+'" onclick="abrirReunion('+idx+')">'
    +'<div class="agenda-card-top">'
    +'<span class="agenda-fecha">'+esc(r.dia?r.dia+' ':'')+esc(r.fecha_completa||r.fecha)+' &middot; '+horaConCorreccion(r)+' hs</span>'
    +'<span class="agenda-badges">'+suspendidaBadge(r)+editadaBadge(r)+plenariaBadge(r)+'<span class="exp-badge" style="background:'+col.bg+';color:'+col.fg+'">'+esc(tl)+'</span></span>'
    +'</div>'
    +'<div class="agenda-card-com">'+coms+'</div>'
    +'<div class="agenda-card-salon">'+esc(r.salon_completo||r.salon)+(isPast?' <span class="agenda-pasada-tag">Realizada</span>':'')+'</div>'
    +'</div>';
}
/* Separa próximas/pasadas dentro de un conjunto de reuniones ya filtrado */
function agendaSeccionHtml(tituloSeccion, hint, arr, esAsesores){
  if(!arr.length)return '';
  var now=Date.now(),proximas=[],pasadas=[];
  arr.forEach(function(r){
    var t=reunionTime(r);
    if(t!==-Infinity&&t>=now)proximas.push(r);else pasadas.push(r);
  });
  proximas.sort(function(a,b){return reunionTime(a)-reunionTime(b)});
  pasadas.sort(function(a,b){return reunionTime(b)-reunionTime(a)});
  var cuerpo=agendaGrupoHtml('Pr&oacute;ximas',proximas,false)+agendaGrupoHtml('Reuniones pasadas',pasadas,true);
  if(!cuerpo)return '';
  var hintHtml=hint?' <span class="agenda-seccion-hint">'+esc(hint)+'</span>':'';
  var count=' <span class="agenda-grupo-count">('+arr.length+')</span>';
  /* La sección de asesores va colapsada por defecto (instancia secundaria) */
  if(esAsesores){
    return '<div class="agenda-seccion agenda-seccion-asesores agenda-colapsable collapsed">'
      +'<div class="agenda-seccion-title colapsable-head" onclick="toggleColapso(this)">'+chevron()+esc(tituloSeccion)+hintHtml+count+'</div>'
      +'<div class="agenda-colapsable-body">'+cuerpo+'</div>'
      +'</div>';
  }
  return '<div class="agenda-seccion">'
    +'<div class="agenda-seccion-title">'+esc(tituloSeccion)+hintHtml+'</div>'
    +cuerpo+'</div>';
}
/* ── Agenda: calendario mensual (senadores + bicamerales) ────────────── */
var MESES_LARGO=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
var DIAS_SEMANA_LARGO=['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
var agendaComision='',agendaSearch='';
var AGENDA_CAL_MES=null,AGENDA_CAL_MIN=null,AGENDA_CAL_MAX=null;

function agendaPrincipales(){return AGENDA.filter(function(r){return r.tipo!=='asesores'})}
function agendaTextoBusqueda(r){
  var partes=(r.comisiones||[]).slice();
  (r.temario||[]).forEach(function(it){
    if(it.numero)partes.push(it.numero);
    if(it.extracto)partes.push(it.extracto);
  });
  return partes.join(' ');
}
/* Coincidencia de palabra(s) exacta(s): cada término tipeado debe aparecer
   como palabra completa (no substring de otra palabra), sin importar
   mayúsculas. Unicode-aware para que tildes/ñ no rompan el límite de palabra.
   Para que filtre a medida que se escribe (y no recién al completar la
   palabra), la última palabra —mientras no haya un espacio después— se
   busca por prefijo; las anteriores, ya "cerradas" por el espacio, exigen
   coincidencia exacta. */
function matchPalabraExacta(query,texto){
  query=query||'';
  var terminaEnEspacio=/\s$/.test(query);
  var tokens=query.trim().split(/\s+/).filter(Boolean);
  if(!tokens.length)return true;
  texto=texto||'';
  return tokens.every(function(tok,i){
    var esUltimaIncompleta=(i===tokens.length-1)&&!terminaEnEspacio;
    var escTok=tok.replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
    try{
      var patron='(?<![\\p{L}\\p{N}])'+escTok+(esUltimaIncompleta?'':'(?![\\p{L}\\p{N}])');
      return new RegExp(patron,'iu').test(texto);
    }catch(e){
      return texto.toLowerCase().indexOf(tok.toLowerCase())>=0;
    }
  });
}
function agendaPasaFiltro(r){
  if(agendaComision&&(r.comisiones||[]).indexOf(agendaComision)<0)return false;
  if(agendaSearch&&!matchPalabraExacta(agendaSearch,agendaTextoBusqueda(r)))return false;
  return true;
}
function agendaPrincipalesFiltradas(){return agendaPrincipales().filter(agendaPasaFiltro)}

function agendaInit(){
  var principales=agendaPrincipales();
  var comSet={};
  principales.forEach(function(r){(r.comisiones||[]).forEach(function(c){if(c)comSet[c]=1})});
  fillSelect('agenda-comision-select',Object.keys(comSet).sort());
  document.getElementById('agenda-comision-select').addEventListener('change',function(e){agendaComision=e.target.value;agendaOnFiltro()});
  document.getElementById('agenda-search').addEventListener('input',function(e){agendaSearch=e.target.value;agendaOnFiltro()});

  var fechas=principales.map(function(r){return r.fecha_iso?new Date(r.fecha_iso):null}).filter(Boolean);
  var hoy=new Date();
  if(fechas.length){
    var min=fechas.reduce(function(a,b){return b<a?b:a});
    var max=fechas.reduce(function(a,b){return b>a?b:a});
    AGENDA_CAL_MIN=new Date(min.getFullYear(),min.getMonth(),1);
    AGENDA_CAL_MAX=new Date(max.getFullYear(),max.getMonth(),1);
  }else{
    AGENDA_CAL_MIN=AGENDA_CAL_MAX=new Date(hoy.getFullYear(),hoy.getMonth(),1);
  }
  var inicial=new Date(hoy.getFullYear(),hoy.getMonth(),1);
  if(inicial<AGENDA_CAL_MIN)inicial=new Date(AGENDA_CAL_MIN);
  if(inicial>AGENDA_CAL_MAX)inicial=new Date(AGENDA_CAL_MAX);
  AGENDA_CAL_MES=inicial;

  renderAgendaCalendario();
  renderAgendaAsesores();
  renderAgendaHoy();
}
function toggleAgendaVista(vista){
  document.getElementById('agenda-hoy-wrap').hidden=(vista==='calendario');
  document.getElementById('agenda-calendario-wrap').hidden=(vista!=='calendario');
}
function renderAgendaHoy(){
  var hoy=new Date();
  var hoyKey=hoy.getFullYear()+'-'+hoy.getMonth()+'-'+hoy.getDate();
  var reuniones=AGENDA.filter(function(r){
    if(!r.fecha_iso||r.suspendida)return false;
    var d=new Date(r.fecha_iso);
    return (d.getFullYear()+'-'+d.getMonth()+'-'+d.getDate())===hoyKey;
  });
  reuniones.sort(function(a,b){return reunionTime(a)-reunionTime(b)});
  var diaSemana=DIAS_SEMANA_LARGO[hoy.getDay()];
  document.getElementById('agenda-hoy-titulo').textContent='Hoy, '+diaSemana+' '+hoy.getDate()+' de '+MESES_LARGO[hoy.getMonth()];
  var body=document.getElementById('agenda-hoy-body');
  body.innerHTML=reuniones.length
    ?reuniones.map(function(r){return buildReunionCard(r,AGENDA.indexOf(r),reunionTime(r)<Date.now());}).join('')
    :'<div class="com-empty">No hay reuniones programadas para hoy.</div>';
}
function agendaOnFiltro(){
  renderAgendaCalendario();
  renderAgendaAsesores();
}
function agendaCambiarMes(delta){
  var m=new Date(AGENDA_CAL_MES.getFullYear(),AGENDA_CAL_MES.getMonth()+delta,1);
  if(m<AGENDA_CAL_MIN)m=new Date(AGENDA_CAL_MIN);
  if(m>AGENDA_CAL_MAX)m=new Date(AGENDA_CAL_MAX);
  AGENDA_CAL_MES=m;
  renderAgendaCalendario();
}
function renderAgendaCalendario(){
  var mes=AGENDA_CAL_MES;
  var nombreMes=MESES_LARGO[mes.getMonth()];
  document.getElementById('cal-mes-label').textContent=nombreMes.charAt(0).toUpperCase()+nombreMes.slice(1)+' de '+mes.getFullYear();

  var prevMes=new Date(mes.getFullYear(),mes.getMonth()-1,1);
  var nextMes=new Date(mes.getFullYear(),mes.getMonth()+1,1);
  document.getElementById('cal-prev').disabled=prevMes<AGENDA_CAL_MIN;
  document.getElementById('cal-next').disabled=nextMes>AGENDA_CAL_MAX;

  var filtradas=agendaPrincipalesFiltradas();
  var porDia={};
  filtradas.forEach(function(r){
    if(!r.fecha_iso)return;
    var d=new Date(r.fecha_iso);
    if(d.getFullYear()!==mes.getFullYear()||d.getMonth()!==mes.getMonth())return;
    (porDia[d.getDate()]=porDia[d.getDate()]||[]).push(r);
  });
  Object.keys(porDia).forEach(function(k){porDia[k].sort(function(a,b){return reunionTime(a)-reunionTime(b)})});

  var primerDiaSemana=(mes.getDay()+6)%7; /* 0=lunes ... 6=domingo */
  var diasEnMes=new Date(mes.getFullYear(),mes.getMonth()+1,0).getDate();
  var diasMesAnterior=new Date(mes.getFullYear(),mes.getMonth(),0).getDate();
  var hoy=new Date();
  var hoyKey=hoy.getFullYear()+'-'+hoy.getMonth()+'-'+hoy.getDate();

  var celdas=[];
  for(var i=0;i<primerDiaSemana;i++)celdas.push({num:diasMesAnterior-primerDiaSemana+1+i,outside:true});
  for(var d2=1;d2<=diasEnMes;d2++)celdas.push({num:d2,outside:false,items:porDia[d2]||[]});
  var trailNum=1;
  while(celdas.length%7!==0)celdas.push({num:trailNum++,outside:true});

  var html='';
  celdas.forEach(function(c,idx){
    var dow=idx%7,weekend=(dow===5||dow===6);
    var cls='cal-day'+(weekend?' weekend':'')+(c.outside?' outside':'');
    if(!c.outside&&(mes.getFullYear()+'-'+mes.getMonth()+'-'+c.num)===hoyKey)cls+=' today';
    var itemsHtml='';
    if(!c.outside&&c.items&&c.items.length){
      cls+=' has-items';
      var max=3;
      c.items.slice(0,max).forEach(function(r){
        var col=REUNION_TIPO_COLOR[r.tipo]||{fg:'#888',bg:'#eee'};
        var txt=r.hora+' '+(r.comisiones||[]).join(', ');
        itemsHtml+='<span class="cal-pill" style="background:'+col.bg+';color:'+col.fg+'" title="'+escAttr(txt)+'">'+esc(txt)+'</span>';
      });
      if(c.items.length>max)itemsHtml+='<span class="cal-more">+'+(c.items.length-max)+' más</span>';
    }
    var onclick=(!c.outside&&c.items&&c.items.length)?' onclick="agendaAbrirDia('+mes.getFullYear()+','+mes.getMonth()+','+c.num+')"':'';
    html+='<div class="'+cls+'"'+onclick+'><span class="cal-day-num">'+c.num+'</span><div class="cal-day-items">'+itemsHtml+'</div></div>';
  });
  document.getElementById('cal-grid').innerHTML=html;

  var msgEl=document.getElementById('cal-empty-msg');
  var hayFiltro=agendaComision||agendaSearch;
  msgEl.style.display=(hayFiltro&&!filtradas.length)?'block':'none';
}
function agendaAbrirDia(anio,mes,dia){
  var reuniones=agendaPrincipalesFiltradas().filter(function(r){
    if(!r.fecha_iso)return false;
    var d=new Date(r.fecha_iso);
    return d.getFullYear()===anio&&d.getMonth()===mes&&d.getDate()===dia;
  });
  reuniones.sort(function(a,b){return reunionTime(a)-reunionTime(b)});
  var diaSemana=DIAS_SEMANA_LARGO[new Date(anio,mes,dia).getDay()];
  document.getElementById('agenda-dia-titulo').textContent=diaSemana.charAt(0).toUpperCase()+diaSemana.slice(1)+' '+dia+' de '+MESES_LARGO[mes]+' de '+anio;
  document.getElementById('agenda-dia-body').innerHTML=reuniones.map(function(r){
    return buildReunionCard(r,AGENDA.indexOf(r),reunionTime(r)<Date.now());
  }).join('')||'<div class="com-empty">Sin reuniones.</div>';
  document.getElementById('agenda-dia-overlay').classList.add('open');
}
function agendaCerrarDia(e){
  if(e&&e.target!==document.getElementById('agenda-dia-overlay'))return;
  document.getElementById('agenda-dia-overlay').classList.remove('open');
}
function renderAgendaAsesores(){
  var asesores=AGENDA.filter(function(r){return r.tipo==='asesores'}).filter(agendaPasaFiltro);
  document.getElementById('agenda-asesores').innerHTML=agendaSeccionHtml('Reuniones de asesores','instancia previa, no vinculante',asesores,true);
}
/* ── Ayuda Memoria (Órdenes del Día) ──────────────────────────────── */
var PROYECTOS_POR_CLAVE=null;
function claveExp(origen,nro,anio){return origen+'~|~'+nro+'~|~'+anio}
function proyectoDeExp(exp){
  if(!PROYECTOS_POR_CLAVE){
    PROYECTOS_POR_CLAVE={};
    DATA.forEach(function(p){PROYECTOS_POR_CLAVE[claveExp(p.origen,p.nro,p.anio)]=p});
  }
  return PROYECTOS_POR_CLAVE[claveExp(exp.origen,exp.nro,exp.anio)]||null;
}
var AM_CATS=['Todos','Acuerdo','Acuerdo para dar cuenta','Proyecto de Ley','Proyecto de Declaración','Proyecto de Comunicación','Proyecto de Resolución'];
var AM_CAT_LABELS={'Todos':'Todos','Acuerdo':'Acuerdos','Acuerdo para dar cuenta':'Acuerdos para dar cuenta','Proyecto de Ley':'Proyectos de Ley','Proyecto de Declaración':'Declaraciones','Proyecto de Comunicación':'Comunicaciones','Proyecto de Resolución':'Resoluciones'};
var AM_CAT_CODE={'Acuerdo':'AC','Acuerdo para dar cuenta':'DC','Proyecto de Ley':'PL','Proyecto de Declaración':'PD','Proyecto de Comunicación':'PC','Proyecto de Resolución':'PR'};
/* Paleta propia de Ayuda Memoria (no la de Proyectos: ahí PL/PD son dos tonos
   de azul casi iguales, acá conviene que se distingan de un vistazo). */
var AM_TIPO_FG={PL:'#1B5EA2',PD:'#7C3AED',PC:'#0d7a4a',PR:'#C2650C',AC:'#7a5c1a',DC:'#8a5a00'};
var AM_TIPO_BG={PL:'#D6E4F0',PD:'#EDE4FB',PC:'#DCF0E8',PR:'#FBEADD',AC:'#F9F0DA',DC:'#FFE8B3'};
var amCat='Todos',amComision='',amAutor='',amBloque='',amSearch='',amCurrent=null,amStep=0,amFiltered=[];
/* Selector de autores: senadores individuales (no el texto compuesto de la
   ficha). Con un bloque elegido sólo se listan los senadores de ese bloque. */
function amFillAutores(){
  var set={};
  (AYUDA_MEMORIA||[]).forEach(function(d){
    (d.autoresDet||[]).forEach(function(a){if(!amBloque||a.b===amBloque)set[a.n]=1});
  });
  var sel=document.getElementById('am-autor-select');
  sel.innerHTML='<option value="">Todos los autores</option>';
  fillSelect('am-autor-select',Object.keys(set).sort());
  if(amAutor&&!set[amAutor])amAutor='';
  sel.value=amAutor;
}
function amInit(){
  var comSet={},bloqueSet={};
  (AYUDA_MEMORIA||[]).forEach(function(d){
    (d.comisiones||[]).forEach(function(c){if(c)comSet[c]=1});
    (d.bloquesAutor||[]).forEach(function(b){bloqueSet[b]=1});
  });
  fillSelectLabeled('am-comision-select',Object.keys(comSet).sort(),comLabel);
  document.getElementById('am-comision-select').addEventListener('change',function(e){amComision=e.target.value;renderAm()});
  amFillAutores();
  document.getElementById('am-autor-select').addEventListener('change',function(e){amAutor=e.target.value;renderAm()});
  fillSelect('am-bloque-select',Object.keys(bloqueSet).sort());
  document.getElementById('am-bloque-select').addEventListener('change',function(e){amBloque=e.target.value;amFillAutores();renderAm()});

  var chipsEl=document.getElementById('am-chips');
  AM_CATS.forEach(function(c){
    var chip=document.createElement('div');
    chip.className='chip'+(c===amCat?' on':'');
    chip.textContent=AM_CAT_LABELS[c]||c;
    chip.addEventListener('click',function(){
      amCat=c;
      document.querySelectorAll('#am-chips .chip').forEach(function(x){x.classList.remove('on')});
      chip.classList.add('on');
      renderAm();
    });
    chipsEl.appendChild(chip);
  });

  document.getElementById('am-search').addEventListener('input',function(e){amSearch=e.target.value.toLowerCase();renderAm()});
  document.getElementById('am-close').addEventListener('click',amCloseStory);
  document.getElementById('am-prev-zone').addEventListener('click',amPrevStep);
  document.getElementById('am-next-zone').addEventListener('click',amNextStep);
  document.getElementById('am-btn-prev').addEventListener('click',amPrevStep);
  document.getElementById('am-btn-next').addEventListener('click',amNextStep);
  document.getElementById('am-scrim').addEventListener('click',function(e){if(e.target.id==='am-scrim')amCloseStory()});
  document.addEventListener('keydown',function(e){
    if(!document.getElementById('am-scrim').classList.contains('open'))return;
    if(e.key==='Escape')amCloseStory();
    if(e.key==='ArrowRight')amNextStep();
    if(e.key==='ArrowLeft')amPrevStep();
  });
  renderAm();
}
function amCardBadge(d){
  var code=AM_CAT_CODE[d.categoria]||'';
  var fg=AM_TIPO_FG[code]||'#666',bg=AM_TIPO_BG[code]||'#eee';
  return '<span class="am-badge" style="background:'+bg+';color:'+fg+'">'+esc(d.categoria)+'</span>';
}
function buildAmCard(d,idx){
  var comision=comLabel(d.comisionCabecera||(d.comisiones&&d.comisiones[0])||'');
  return '<div class="am-card" onclick="amOpenStory('+idx+')">'
    +'<div class="am-card-top">'+amCardBadge(d)+'<span class="am-exp-num am-od-num">'+(d.pendienteCuenta?esc(d.expedientes[0].codigo):'OD '+esc(d.numero)+'/'+esc(String(d.periodo).slice(-2)))+'</span>'+(d.minoria?'<span class="am-minoria-tag">Con minor&iacute;a</span>':'')+'</div>'
    +(d.autor?'<div class="am-autor">'+esc(d.autor)+'</div>':'')
    +'<p class="am-desc">'+esc(d.descripcion)+'</p>'
    +'<div class="am-card-bottom"><span class="am-comision">'+esc(comision)+'</span><span class="am-read-hint">Ver ficha &rarr;</span></div>'
    +'</div>';
}
function renderAm(){
  var data=AYUDA_MEMORIA||[];
  amFiltered=data.filter(function(d){
    if(amCat!=='Todos'&&d.categoria!==amCat)return false;
    if(amComision&&(d.comisiones||[]).indexOf(amComision)<0)return false;
    if(amAutor&&!(d.autoresDet||[]).some(function(a){return a.n===amAutor}))return false;
    if(amBloque&&(d.bloquesAutor||[]).indexOf(amBloque)<0)return false;
    if(amSearch){
      var hay=(d.descripcion+' '+(d.autor||'')+' '+(d.expedientes||[]).map(function(e){return e.codigo}).join(' ')).toLowerCase();
      if(hay.indexOf(amSearch)<0)return false;
    }
    return true;
  });
  var countEl=document.getElementById('am-count');
  if(countEl)countEl.textContent=amFiltered.length+' de '+data.length+' expedientes';
  var grid=document.getElementById('am-grid');
  if(!grid)return;
  if(!amFiltered.length){grid.innerHTML='<div class="no-results">No hay expedientes que coincidan con el filtro.</div>';return}
  var html='';
  amFiltered.forEach(function(d){html+=buildAmCard(d,data.indexOf(d))});
  grid.innerHTML=html;
}
/* ── Exportar Ayuda Memoria (según filtros aplicados) a .xls ──────────
   Se arma a mano un XML Spreadsheet 2003 (lo que abre Excel nativamente
   con extensión .xls) en vez de sumar una librería sólo para esto -- el
   formato admite hipervínculos por celda (ss:HRef) sin depender de nada
   externo. Una fila por expediente (no por OD): si una OD junta varios
   expedientes, cada uno necesita su propio link, así que conviene
   repetirla en vez de perder el hipervínculo de alguno.*/
function _xmlEsc(s){
  return String(s==null?'':s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function _construirXmlAyudaMemoria(){
  var filas=[];
  amFiltered.forEach(function(d){
    var autorContenido=(d.autor?d.autor+': ':'')+(d.descripcion||'');
    var firmantes=(d.firmantesMayoria||[]).join('; ');
    (d.disidencias||[]).forEach(function(ds){
      if(!ds.firmantes||!ds.firmantes.length)return;
      var lab=ds.tipo==='parcial'?'En disidencia parcial':ds.tipo==='total'?'En disidencia total':'En disidencia';
      firmantes+=(firmantes?'\n':'')+lab+': '+ds.firmantes.join('; ');
    });
    var comision=comLabel(d.comisionCabecera||(d.comisiones&&d.comisiones[0])||'');
    var odNum=d.pendienteCuenta?'Para dar cuenta':d.numero+'/'+String(d.periodo).slice(-2)+(d.tipoOD==='ANEXO'?' (Anexo)':'');
    var exps=(d.expedientes&&d.expedientes.length)?d.expedientes:[{codigo:'',url:null}];
    exps.forEach(function(e){
      filas.push({
        od:odNum, odUrl:d.odLink||null,
        exp:e.codigo||'', expUrl:e.url||null,
        autorContenido:autorContenido, firmantes:firmantes, comision:comision
      });
    });
  });

  var cols=['OD N°','EXPTE N°','AUTORES Y CONTENIDO','FIRMANTES DEL DICTAMEN','COMISIÓN CABECERA'];
  var xml='<?xml version="1.0" encoding="UTF-8"?>\n'
    +'<?mso-application progid="Excel.Sheet"?>\n'
    +'<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet" '
    +'xmlns:o="urn:schemas-microsoft-com:office:office" '
    +'xmlns:x="urn:schemas-microsoft-com:office:excel" '
    +'xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet" '
    +'xmlns:html="http://www.w3.org/TR/REC-html40">\n'
    +'<Styles>'
    +'<Style ss:ID="Header"><Font ss:Bold="1" ss:Color="#FFFFFF"/><Interior ss:Color="#1B5EA2" ss:Pattern="Solid"/></Style>'
    +'<Style ss:ID="Link"><Font ss:Color="#1B5EA2" ss:Underline="Single"/></Style>'
    +'<Style ss:ID="Wrap"><Alignment ss:Vertical="Top" ss:WrapText="1"/></Style>'
    +'</Styles>\n'
    +'<Worksheet ss:Name="Ayuda Memoria">\n<Table>\n'
    +'<Column ss:Width="70"/><Column ss:Width="90"/><Column ss:Width="340"/><Column ss:Width="220"/><Column ss:Width="160"/>\n';

  xml+='<Row>'+cols.map(function(c){return '<Cell ss:StyleID="Header"><Data ss:Type="String">'+_xmlEsc(c)+'</Data></Cell>';}).join('')+'</Row>\n';

  filas.forEach(function(f){
    xml+='<Row>';
    xml+= f.odUrl
      ? '<Cell ss:HRef="'+_xmlEsc(f.odUrl)+'" ss:StyleID="Link"><Data ss:Type="String">'+_xmlEsc(f.od)+'</Data></Cell>'
      : '<Cell><Data ss:Type="String">'+_xmlEsc(f.od)+'</Data></Cell>';
    xml+= f.expUrl
      ? '<Cell ss:HRef="'+_xmlEsc(f.expUrl)+'" ss:StyleID="Link"><Data ss:Type="String">'+_xmlEsc(f.exp)+'</Data></Cell>'
      : '<Cell><Data ss:Type="String">'+_xmlEsc(f.exp)+'</Data></Cell>';
    xml+='<Cell ss:StyleID="Wrap"><Data ss:Type="String">'+_xmlEsc(f.autorContenido)+'</Data></Cell>';
    xml+='<Cell ss:StyleID="Wrap"><Data ss:Type="String">'+_xmlEsc(f.firmantes).replace(/\n/g,'&#10;')+'</Data></Cell>';
    xml+='<Cell><Data ss:Type="String">'+_xmlEsc(f.comision)+'</Data></Cell>';
    xml+='</Row>\n';
  });

  xml+='</Table></Worksheet></Workbook>';
  return xml;
}
function exportarAyudaMemoria(){
  if(!amFiltered.length){alert('No hay expedientes para exportar con el filtro actual.');return}
  var xml=_construirXmlAyudaMemoria();
  var blob=new Blob([xml],{type:'application/vnd.ms-excel'});
  var url=URL.createObjectURL(blob);
  var a=document.createElement('a');
  a.href=url;
  a.download='ayuda_memoria_'+new Date().toISOString().slice(0,10)+'.xls';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(function(){URL.revokeObjectURL(url);},1000);
}
function amBuildPendiente(d){
  var exp=d.expedientes[0];
  var links=[];
  if(exp.url)links.push('<a class="am-link-btn" href="'+escAttr(exp.url)+'" target="_blank" rel="noopener">&#128196; Ver expediente</a>');
  if(d.pliegoSlug)links.push('<a class="am-link-btn" href="#pliegos/'+escAttr(d.pliegoSlug)+'" onclick="amCloseStory()">&#9878; Ver en Pliegos judiciales</a>');
  return [
    {label:'Qué es',title:d.candidato||'Mensaje del Poder Ejecutivo',badges:[d.categoria,d.origen],body:d.descripcion},
    {label:'Trámite',title:'Pendiente de dar cuenta',kv:[
      ['Expediente', esc(exp.codigo)],
      ['Comisi&oacute;n', esc(comLabel(d.comisionCabecera))],
      ['Ingreso', esc(d.fechaIngreso||'—')],
      ['DAE', d.dae?'N&ordm; '+esc(d.dae)+' / '+esc(d.periodo):'—'],
      ['Estado', 'Ingresó al Senado; todavía no se dio cuenta en el recinto']
    ],linksHtml:links.length?'<div class="am-link-row">'+links.join('')+'</div>':''}
  ];
}
function amBuildSteps(d){
  if(d.pendienteCuenta)return amBuildPendiente(d);
  var steps=[];
  steps.push({
    label:'Qué es',
    title:d.autor?d.autor:(d.origen==='Poder Ejecutivo'?'Mensaje del Poder Ejecutivo':'Proyecto en revisión'),
    badges:[d.categoria,d.origen],
    body:d.descripcion
  });
  var links=[];
  if(d.odLink)links.push('<a class="am-link-btn" href="'+escAttr(d.odLink)+'" target="_blank" rel="noopener">&darr; Descargar Orden del D&iacute;a</a>');
  if(d.minoria&&d.minoria.odLink)links.push('<a class="am-link-btn" href="'+escAttr(d.minoria.odLink)+'" target="_blank" rel="noopener">&darr; Descargar Anexo (minor&iacute;a)</a>');
  var primerExp=(d.expedientes||[])[0];
  if(primerExp&&primerExp.url)links.push('<a class="am-link-btn" href="'+escAttr(primerExp.url)+'" target="_blank" rel="noopener">&#128196; Ver expediente</a>');
  steps.push({
    label:'Trámite',
    title:'Datos del expediente',
    kv:[
      ['Expediente(s)', esc((d.expedientes||[]).map(function(e){return e.codigo}).join(' · '))],
      ['Comisi&oacute;n(es)', esc(((d.comisiones&&d.comisiones.length)?d.comisiones:[d.comisionCabecera]).filter(Boolean).map(comLabel).join(' · ')||'—')],
      ['Fecha de dictamen', esc(d.fechaDictamen||'—')],
      ['Orden del D&iacute;a', 'N&ordm; '+esc(d.numero)+' / '+esc(d.periodo)+(d.minoria?' (con dictamen en minor&iacute;a)':'')]
    ],
    linksHtml:links.length?'<div class="am-link-row">'+links.join('')+'</div>':''
  });
  if((d.firmantesPorBloque&&d.firmantesPorBloque.length)||(d.disidenciasPorBloque&&d.disidenciasPorBloque.length)){
    steps.push({label:'Firmantes',title:'Firmantes del dictamen de mayoría',firmantesPorBloque:d.firmantesPorBloque||[],disidencias:d.disidenciasPorBloque||[]});
  }
  if(d.minoria&&((d.minoria.firmantesPorBloque&&d.minoria.firmantesPorBloque.length)||(d.minoria.disidenciasPorBloque&&d.minoria.disidenciasPorBloque.length))){
    steps.push({label:'Minoría',title:'Firmantes del dictamen en minoría',firmantesPorBloque:d.minoria.firmantesPorBloque||[],disidencias:d.minoria.disidenciasPorBloque||[]});
  }
  return steps;
}
function amOpenStory(idx){
  amCurrent=idx;amStep=0;
  var d=(AYUDA_MEMORIA||[])[idx];
  if(!d)return;
  document.getElementById('am-story-id').textContent=d.pendienteCuenta?d.expedientes[0].codigo:'OD '+d.numero+'/'+String(d.periodo).slice(-2);
  var steps=amBuildSteps(d);
  document.getElementById('am-progress').innerHTML=steps.map(function(){return '<div class="bar"><div class="fill"></div></div>'}).join('');
  document.getElementById('am-dots').innerHTML=steps.map(function(s,i){return '<div class="am-dot" data-i="'+i+'"></div>'}).join('');
  amRenderStep();
  document.getElementById('am-scrim').classList.add('open');
}
function amCloseStory(){document.getElementById('am-scrim').classList.remove('open');amCurrent=null}
function amRenderStep(){
  var d=(AYUDA_MEMORIA||[])[amCurrent];
  if(!d)return;
  var steps=amBuildSteps(d);
  var s=steps[amStep];
  var html='<div class="am-step-label">'+esc(s.label)+' &middot; '+(amStep+1)+'/'+steps.length+'</div>'
    +'<h2>'+esc(s.title)+'</h2>';
  if(s.badges)html+='<div class="am-badges-row">'+s.badges.filter(Boolean).map(function(b){return '<span>'+esc(b)+'</span>'}).join('')+'</div>';
  if(s.body)html+='<p>'+esc(s.body)+'</p>';
  if(s.kv)html+='<dl class="am-kv">'+s.kv.map(function(kv){return '<dt>'+kv[0]+'</dt><dd>'+kv[1]+'</dd>'}).join('')+'</dl>';
  if(s.linksHtml)html+=s.linksHtml;
  var gruposHtml=function(grupos){
    return grupos.map(function(g){
      var col=blqColor(g.bloque);
      return '<div class="am-firmantes-bloque"><span class="bl-name" style="background:'+col.bg+';color:'+col.badge+'">'+esc(g.bloque)+'</span>'
        +'<div class="bl-list">'+esc(g.integrantes.join(' · '))+'</div></div>';
    }).join('');
  };
  if(s.firmantesPorBloque)html+=gruposHtml(s.firmantesPorBloque);
  (s.disidencias||[]).forEach(function(ds){
    html+='<div class="am-disidencia"><div class="am-disid-title">'+esc(ds.label)+'</div>'+gruposHtml(ds.firmantesPorBloque)+'</div>';
  });
  document.getElementById('am-story-body').innerHTML=html;
  document.querySelectorAll('#am-progress .bar').forEach(function(bar,i){
    var fill=bar.querySelector('.fill');
    fill.style.width=i<=amStep?'100%':'0%';
  });
  document.querySelectorAll('#am-dots .am-dot').forEach(function(dot,i){dot.classList.toggle('active',i===amStep)});
  document.getElementById('am-btn-prev').disabled=amStep===0;
  document.getElementById('am-btn-next').textContent=amStep===steps.length-1?'Cerrar ✕':'Siguiente →';
}
function amNextStep(){
  var d=(AYUDA_MEMORIA||[])[amCurrent];
  if(!d)return;
  var steps=amBuildSteps(d);
  if(amStep<steps.length-1){amStep++;amRenderStep()}else{amCloseStory()}
}
function amPrevStep(){if(amStep>0){amStep--;amRenderStep()}}
function parseExpNumero(numero){
  var m=/^([A-ZÑ.]+)-(\d+)\/(\d+)$/.exec(String(numero||'').trim().toUpperCase());
  if(!m)return null;
  return {origen:m[1].replace(/\./g,''),nro:parseInt(m[2],10),anio:2000+parseInt(m[3],10)};
}
function irAExpediente(numero){
  var exp=parseExpNumero(numero);
  if(!exp)return;
  resetBuscadorOnly();
  activeAnio='';activeTipos={};activeOrigen='';activeAcuerdoEstado='';
  document.getElementById('search').value=exp.origen+'-'+exp.nro+'/'+String(exp.anio).slice(-2);
  switchMain('proyectos');
  switchSub('buscador');
  applyAll();
  window.scrollTo({top:0,behavior:'smooth'});
}
var agendaReunionActual=null;
function claveReunionUrl(r){
  return (r.fecha||'')+'|'+(r.hora_boletin||r.hora||'')+'|'+(r.comisiones||[]).join(',');
}
/* Hash corto y estable (no criptográfico, sólo para acortar el link
   compartible) -- con ~220 reuniones el riesgo de colisión es despreciable. */
function hashCorto(str){
  var h=5381;
  for(var i=0;i<str.length;i++)h=((h*33)^str.charCodeAt(i))>>>0;
  return h.toString(36);
}
var AGENDA_POR_HASH=null;
function reunionPorHashUrl(hash){
  if(!AGENDA_POR_HASH){
    AGENDA_POR_HASH={};
    AGENDA.forEach(function(r,i){AGENDA_POR_HASH[hashCorto(claveReunionUrl(r))]=i;});
  }
  return AGENDA_POR_HASH.hasOwnProperty(hash)?AGENDA_POR_HASH[hash]:-1;
}
function abrirReunion(idx,sinHash){
  var r=AGENDA[idx];
  if(!r)return;
  agendaReunionActual=r;
  agendaCerrarDia({target:document.getElementById('agenda-dia-overlay')});
  document.getElementById('agenda-nivel1').classList.remove('active');
  document.getElementById('agenda-nivel2').classList.add('active');
  if(!sinHash){
    var hash='#agenda/r/'+hashCorto(claveReunionUrl(r));
    if(location.hash!==hash)history.pushState({},'',hash);
  }
  var tl=REUNION_TIPO_LABEL[r.tipo]||r.tipo;
  var col=REUNION_TIPO_COLOR[r.tipo]||{fg:'#888',bg:'#eee'};
  document.getElementById('agenda-detalle-titulo').textContent=(r.comisiones||[]).join(' · ');
  document.getElementById('agenda-detalle-meta').innerHTML='<div class="agenda-detalle-row">'
    +'<span class="exp-badge" style="background:'+col.bg+';color:'+col.fg+'">'+esc(tl)+'</span>'
    +suspendidaBadge(r)+editadaBadge(r)+plenariaBadge(r)
    +'<span class="agenda-fecha">'+esc(r.dia?r.dia+' ':'')+esc(r.fecha_completa||r.fecha)+' &middot; '+horaConCorreccion(r)+' hs</span>'
    +'</div><div class="agenda-detalle-salon">&#128205; '+esc(r.salon_completo||r.salon)+'</div>'
    +(r.nota?'<div class="agenda-nota">&#9998; '+esc(r.nota)+'</div>':'');
  var th='';
  (r.temario||[]).forEach(function(it){
    var clickable=!!parseExpNumero(it.numero);
    th+='<div class="temario-item'+(clickable?' clk':'')+'"'+(clickable?' onclick="irAExpediente(\''+jsStr(it.numero)+'\')"':'')+'>'
      +(it.numero?'<span class="temario-num">'+esc(it.numero)+'</span>':'')
      +'<span class="temario-extracto">'+esc(it.extracto)+'</span>'
      +'</div>';
  });
  if(r.expositores)th+='<div class="ficha-expositores"><strong>Expositores / invitados:</strong> '+esc(r.expositores).replace(/\n/g,'<br>')+'</div>';
  document.getElementById('agenda-temario-list').innerHTML=th||'<div class="com-empty">Sin temario cargado.</div>';
  window.scrollTo({top:0,behavior:'smooth'});
}
function copiarLinkReunion(btn){
  var url=location.origin+location.pathname+'#f/'+hashCorto(claveReunionUrl(agendaReunionActual));
  var listo=function(){btn.innerHTML='&#10003; Copiado';setTimeout(function(){btn.innerHTML='&#128279; Copiar enlace';},1800);};
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(url).then(listo).catch(function(){prompt('Copiá el enlace:',url)});
  }else{
    prompt('Copiá el enlace:',url);
  }
}
function volverAgenda(){
  document.getElementById('agenda-nivel2').classList.remove('active');
  document.getElementById('agenda-nivel1').classList.add('active');
  if(location.hash.indexOf('#agenda/r/')===0)history.pushState({},'','#agenda');
}
function abrirReunionDesdeHash(){
  var h=location.hash;
  var esFicha=h.indexOf('#f/')===0;
  var esDetalle=h.indexOf('#agenda/r/')===0;
  if(!esFicha&&!esDetalle)return false;
  var hashCorto2=esFicha?h.slice('#f/'.length):h.slice('#agenda/r/'.length);
  var idx=reunionPorHashUrl(hashCorto2);
  if(idx<0)return false;
  activateMain('agenda');
  abrirReunion(idx,true);
  if(esFicha)abrirFichaReunion(true);
  return true;
}

/* ── Ficha de reunión (temario + checklist de integrantes por comisión) ── */
/* Único apellido duplicado entre los 72 senadores vigentes: López (Cándida
   Cristina / María Florencia) -- se desambigua a mano en vez de armar un
   algoritmo genérico para un caso que hoy es único. */
function apellidoFicha(nombreCompleto){
  var partes=String(nombreCompleto||'').split(',');
  var apellido=(partes[0]||'').trim();
  if(apellido.toUpperCase()==='LÓPEZ'||apellido.toUpperCase()==='LOPEZ'){
    var nombre=(partes[1]||'').toUpperCase();
    if(nombre.indexOf('FLORENCIA')>=0)return 'López, F.';
    if(nombre.indexOf('NDIDA')>=0)return 'López, C.'; // Cándida (evita el acento en el indexOf)
  }
  return apellido.toLowerCase().replace(/(^|\s)\S/g,function(c){return c.toUpperCase()});
}
/* Reconstruye la(s) comisión(es) oficiales de una reunión a partir de
   r.comisiones -- normalmente un nombre limpio por entrada (plenarias
   separadas por "|" ya vienen partidas en el scraper), pero a veces un
   nombre largo queda partido en 2 líneas (formato narrativo, sin "|").
   Cada entrada se prueba primero SOLA (para no confundir "2 comisiones
   distintas en una plenaria" con "1 nombre partido en 2 líneas"); sólo se
   acumula en el buffer cuando la entrada no matchea por sí misma. */
function _normComFicha(s){return normCom(comLabel(s));}
function comisionesDeReunion(r){
  var nombres=r.comisiones||[];
  var norm=_normComFicha;
  var resultado=[],buffer='';
  function resolverBuffer(){
    if(!buffer)return;
    var nb=norm(buffer);
    var parcial=COMISIONES.filter(function(c){
      var nc=norm(c.nombre);
      return (nc.indexOf(nb)>=0||nb.indexOf(nc)>=0)&&resultado.indexOf(c)<0;
    })[0];
    if(parcial)resultado.push(parcial);
    buffer='';
  }
  nombres.forEach(function(n){
    var directo=COMISIONES.filter(function(c){return norm(c.nombre)===norm(n)})[0];
    if(directo){
      resolverBuffer();
      if(resultado.indexOf(directo)<0)resultado.push(directo);
      return;
    }
    buffer=buffer?(buffer+' '+n):n;
    var combinado=COMISIONES.filter(function(c){return norm(c.nombre)===norm(buffer)})[0];
    if(combinado){resultado.push(combinado);buffer='';}
  });
  resolverBuffer();
  return resultado;
}
var FICHA_CARGO_LABEL={Presidente:'Presidente/a',Vicepresidente:'Vicepresidente/a',Secretario:'Secretario/a',Vocal:''};
/* Estado de "presente" por senador, sólo para la ficha actualmente abierta.
   Persiste en localStorage por reunión (fecha+hora+comisiones), para no
   perder las marcas si se cierra la pestaña a mitad de la reunión. Es por
   dispositivo -- no se sincroniza entre dos personas marcando a la vez. */
var fichaEstado={},fichaStorageKey=null;
function _fichaClave(comId,nombre){return comId+'||'+nombre;}
function _fichaCargarEstado(key){
  try{
    var raw=window.localStorage.getItem(key);
    return raw?JSON.parse(raw):{};
  }catch(e){return {};}
}
function _fichaGuardarEstado(){
  if(!fichaStorageKey)return;
  try{window.localStorage.setItem(fichaStorageKey,JSON.stringify(fichaEstado));}catch(e){}
}
function _fichaAplicarChecked(tr,checked){
  var key=tr.getAttribute('data-key');
  if(checked)fichaEstado[key]=true;else delete fichaEstado[key];
  tr.classList.toggle('ficha-checked',checked);
  var box=tr.querySelector('.ficha-checkbox');
  if(box)box.classList.toggle('checked',checked);
  fichaActualizarContador(tr.getAttribute('data-com'));
}
function toggleFichaPresente(tr){
  var key=tr.getAttribute('data-key');
  if(!key)return;
  var checked=!fichaEstado[key];
  _fichaAplicarChecked(tr,checked);
  // Si el/la senador/a integra más de una comisión de esta plenaria, marcarlo
  // presente en una lo marca presente en todas -- es la misma persona en la
  // misma reunión, no tiene sentido pedir que se tilde fila por fila.
  var nombre=tr.getAttribute('data-nombre');
  if(nombre){
    document.querySelectorAll('.ficha-table tr[data-nombre]').forEach(function(otro){
      if(otro!==tr&&otro.getAttribute('data-nombre')===nombre)_fichaAplicarChecked(otro,checked);
    });
  }
  _fichaGuardarEstado();
}
function fichaActualizarContador(comId){
  var wrap=document.querySelector('.ficha-comision[data-com="'+comId.replace(/"/g,'')+'"]');
  if(!wrap)return;
  var total=wrap.querySelectorAll('tbody tr:not(.ficha-row-vacante)').length;
  var presentes=wrap.querySelectorAll('tbody tr.ficha-checked').length;
  var mayoria=parseInt(wrap.getAttribute('data-mayoria'),10)||0;
  var el=wrap.querySelector('.ficha-presentes-count');
  if(el){
    el.textContent='Presentes: '+presentes+' de '+total+' (quórum '+mayoria+')';
    el.classList.toggle('ficha-quorum-ok',presentes>=mayoria);
  }
}
function fichaFiltrar(){
  var q=(document.getElementById('fichaBuscar').value||'').toLowerCase().trim();
  document.querySelectorAll('.ficha-table tbody tr').forEach(function(tr){
    if(!q){tr.style.display='';return}
    var texto=tr.textContent.toLowerCase();
    tr.style.display=texto.indexOf(q)>=0?'':'none';
  });
}
/* nombresRepetidos: Set (o null) de nombres que integran más de una de las
   comisiones de la plenaria -- esas filas se resaltan (rayado diagonal,
   no sólo color: tiene que leerse igual en una impresión en blanco y
   negro), porque en una reunión conjunta ese/a senador/a cuenta para el
   quórum/firma de cada comisión por separado. */
function fichaTablaComision(c,nombresRepetidos){
  var lista=conVacantes(c).slice();
  lista.sort(function(a,b){
    if(!!a.vacante!==!!b.vacante)return a.vacante?1:-1;
    var oa=ordenIntegrante(a),ob=ordenIntegrante(b);
    if(oa!==ob)return oa-ob;
    return (a.nombre||'').localeCompare(b.nombre||'');
  });
  var comId=comLabel(c.nombre);
  var mayoria=Math.floor((c.cupo||0)/2)+1;
  var hayRepetidos=false;
  var filas=lista.map(function(m){
    if(m.vacante){
      return '<tr class="ficha-row-vacante"><td class="ficha-check"><span class="ficha-checkbox"></span></td>'
        +'<td class="ficha-vacante">Vacante</td><td></td><td></td><td></td><td></td></tr>';
    }
    var col=blqColor(m.bloque);
    var dppHtml=m.dpp?'<span class="ficha-dpp">DPP-'+esc(m.dpp)+'</span>':'';
    var repetido=!!(nombresRepetidos&&nombresRepetidos[m.nombre]);
    if(repetido)hayRepetidos=true;
    var key=_fichaClave(comId,m.nombre);
    var checked=!!fichaEstado[key];
    return '<tr class="ficha-row-clickable'+(repetido?' ficha-row-repetido':'')+(checked?' ficha-checked':'')+'" data-key="'+escAttr(key)+'" data-com="'+escAttr(comId)+'" data-nombre="'+escAttr(m.nombre)+'" onclick="toggleFichaPresente(this)">'
      +'<td class="ficha-check"><span class="ficha-checkbox'+(checked?' checked':'')+'"></span></td>'
      +'<td class="ficha-apellido">'+avatarHtml(m.nombre,22)+esc(apellidoFicha(m.nombre))+(repetido?' <span class="ficha-repetido-marca" title="Integra más de una comisión de esta plenaria">*</span>':'')+'</td>'
      +'<td class="ficha-cargo">'+esc(FICHA_CARGO_LABEL[m.rol]!=null?FICHA_CARGO_LABEL[m.rol]:(m.rol||''))+'</td>'
      +'<td class="ficha-provincia">'+esc(m.provincia||'')+'</td>'
      +'<td><span class="btag" style="background:'+col.bg+';color:'+col.badge+'">'+esc(m.bloque||'')+'</span></td>'
      +'<td>'+dppHtml+'</td></tr>';
  }).join('');
  return '<div class="ficha-comision" data-com="'+escAttr(comId)+'" data-mayoria="'+mayoria+'">'
    +'<div class="ficha-comision-head"><h3>'+esc(comId)+'</h3>'
    +'<span class="ficha-comision-meta">'+c.integrantes.length+' de '+c.cupo+' integrantes'
    +' <span class="ficha-presentes-count no-print"></span></span></div>'
    +'<table class="ficha-table"><thead><tr><th></th><th>Senador/a</th><th>Cargo</th><th>Provincia</th><th>Bloque</th><th>DPP</th></tr></thead>'
    +'<tbody>'+filas+'</tbody></table>'
    +(hayRepetidos?'<div class="ficha-repetido-nota">* Integra también otra comisión de esta plenaria</div>':'')
    +'</div>';
}
function abrirFichaReunion(sinHash){
  var r=agendaReunionActual;
  if(!r)return;
  if(!sinHash){
    var hash='#f/'+hashCorto(claveReunionUrl(r));
    if(location.hash!==hash)history.pushState({},'',hash);
  }
  fichaStorageKey='ficha_'+(r.fecha||'')+'_'+(r.hora||'')+'_'+(r.comisiones||[]).join(',');
  fichaEstado=_fichaCargarEstado(fichaStorageKey);
  var comisiones=comisionesDeReunion(r);
  var titulo=comisiones.length?comisiones.map(function(c){return comLabel(c.nombre)}).join(' · '):(r.comisiones||[]).join(' · ');
  var temarioHtml=(r.temario||[]).map(function(it){
    return '<div class="ficha-tema">'+(it.numero?'<strong>'+esc(it.numero)+'</strong> ':'')+esc(it.extracto)+'</div>';
  }).join('')||'<div class="com-empty">Sin temario cargado.</div>';
  if(r.expositores){
    temarioHtml+='<div class="ficha-expositores"><strong>Expositores / invitados:</strong> '+esc(r.expositores)+'</div>';
  }
  // Senadores que integran más de una de las comisiones de la plenaria
  var conteoNombres={};
  comisiones.forEach(function(c){
    c.integrantes.forEach(function(m){conteoNombres[m.nombre]=(conteoNombres[m.nombre]||0)+1;});
  });
  var nombresRepetidos=null;
  if(comisiones.length>1){
    nombresRepetidos={};
    Object.keys(conteoNombres).forEach(function(n){if(conteoNombres[n]>1)nombresRepetidos[n]=true;});
  }
  var tablasHtml=comisiones.length
    ?comisiones.map(function(c){return fichaTablaComision(c,nombresRepetidos);}).join('')
    :'<div class="com-empty">No se pudo identificar la comisión oficial para armar el checklist de integrantes.</div>';
  var html='<div class="ficha-toolbar no-print">'
    +'<button class="btn-brass" onclick="window.print()">Imprimir / Guardar como PDF</button>'
    +'<button class="btn-neutral" onclick="cerrarFichaReunion()">Volver</button>'
    +'<button class="btn-neutral" onclick="copiarLinkReunion(this)" title="Copiar enlace directo a esta ficha">&#128279; Copiar enlace</button>'
    +(comisiones.length?'<input type="text" id="fichaBuscar" class="ficha-buscar" placeholder="Buscar por apellido…" oninput="fichaFiltrar()">':'')
    +'<span class="ficha-hint">Toc&aacute; una fila para marcar presente. Se guarda solo en este celular/navegador.</span>'
    +'</div>'
    +'<h1>Ficha de reuni&oacute;n de comisi&oacute;n</h1>'
    +(comisiones.length>1?'<div class="ficha-plenaria-banner">&#9873; Plenaria de comisiones</div>':'')
    +'<div class="ficha-meta">'
    +'<div><strong>Comisi&oacute;n'+(comisiones.length>1?'es':'')+':</strong> '+esc(titulo)+'</div>'
    +'<div><strong>Fecha:</strong> '+esc((r.dia?r.dia+' ':'')+(r.fecha_completa||r.fecha))+' &middot; '+horaConCorreccion(r)+' hs</div>'
    +'<div><strong>Sal&oacute;n:</strong> '+esc(r.salon_completo||r.salon)+'</div>'
    +'</div>'
    +(r.nota?'<div class="agenda-nota">&#9998; '+esc(r.nota)+'</div>':'')
    +'<div class="ficha-section-label">Temario</div>'
    +'<div class="ficha-temario">'+temarioHtml+'</div>'
    +'<div class="ficha-section-label">Integrantes</div>'
    +tablasHtml;
  document.getElementById('fichaReunionView').innerHTML=html;
  comisiones.forEach(function(c){fichaActualizarContador(comLabel(c.nombre));});
  document.body.classList.add('ficha-activa');
  document.getElementById('fichaReunionOverlay').hidden=false;
  window.scrollTo({top:0});
}
function cerrarFichaReunion(){
  document.body.classList.remove('ficha-activa');
  document.getElementById('fichaReunionOverlay').hidden=true;
  if(location.hash.indexOf('#f/')===0&&agendaReunionActual){
    history.pushState({},'','#agenda/r/'+hashCorto(claveReunionUrl(agendaReunionActual)));
  }
}

/* ── Sanciones HSN (Boletín de Novedades) ─────────────────────────── */
var SANC_SECCION_LABEL={ley:'Ley',decreto_res_com_dec:'Decreto/Res/Com/Dec',acuerdo:'Acuerdo',preferencia:'Preferencia'};
var sancCat='TODOS',sancPrefCat='TODOS';
var SANC_CATS=['TODOS','LEY','PR','PD','PC','AC','OTROS'];
var SANC_CAT_LABELS={TODOS:'Todos',LEY:'Ley',PR:'PR',PD:'PD',PC:'PC',AC:'Acuerdos',OTROS:'Otros'};
function fechaSesionDisplay(iso){
  var p=String(iso||'').split('-');
  return p.length===3?(p[2]+'/'+p[1]+'/'+p[0]):(iso||'');
}
function sancTipoDe(item){
  var exp=parseExpNumero(item.expediente);
  var p=exp?proyectoDeExp(exp):null;
  return p?p.tipo:null;
}
function sancAprobado(item){return item.resultado==='APROBADO'||item.resultado==='APROBADA';}
/* Categoría de Sanciones HSN: Ley/Acuerdos salen directo de la sección del
   Boletín; PR/PD/PC hay que resolverlos cruzando con el tipo real del
   proyecto (la sección "decreto_res_com_dec" del Boletín los mezcla a todos
   con los decretos, que caen en "Otros"). */
function sancCategoriaLanding(item){
  if(item.seccion==='preferencia')return null;
  if(!sancAprobado(item))return null;
  if(item.seccion==='ley')return 'LEY';
  if(item.seccion==='acuerdo')return 'AC';
  var t=sancTipoDe(item);
  if(t==='PR'||t==='PD'||t==='PC')return t;
  return 'OTROS';
}
function sancPrefCatsDynamic(){
  var set={};
  (SANCIONES_DATA||[]).forEach(function(it){
    if(it.seccion!=='preferencia')return;
    var t=sancTipoDe(it);
    if(t)set[t]=1;
  });
  return ['TODOS'].concat(Object.keys(set).sort());
}
function renderSancChips(){
  var html=SANC_CATS.map(function(c){
    var label=SANC_CAT_LABELS[c];
    return '<button class="chip'+(c===sancCat?' on':'')+'" onclick="setSancCat(\''+c+'\')">'+esc(label)+'</button>';
  }).join('');
  document.getElementById('sanc-chips').innerHTML=html;
}
function renderPrefChips(){
  var cats=sancPrefCatsDynamic();
  var html=cats.map(function(c){
    var label=c==='TODOS'?'Todos':(c+' · '+(TIPOS[c]||c));
    return '<button class="chip'+(c===sancPrefCat?' on':'')+'" onclick="setSancPrefCat(\''+c+'\')">'+esc(label)+'</button>';
  }).join('');
  document.getElementById('sanc-pref-chips').innerHTML=html;
}
function setSancCat(c){sancCat=c;renderSancChips();renderSanciones();}
function setSancPrefCat(c){sancPrefCat=c;renderPrefChips();renderPreferencias();}
function sancObsHtml(item){
  if(!item.observaciones||item.observaciones==='-')return '';
  var cls='sanc-obs'+(/^Ley N/.test(item.observaciones)?' ley':'');
  return '<div class="'+cls+'">'+esc(item.observaciones)+'</div>';
}
function buildSancCard(item){
  var exp=parseExpNumero(item.expediente);
  var p=exp?proyectoDeExp(exp):null;
  var urlExp=(p&&p.url)?p.url:'';
  if(!urlExp&&exp&&item.seccion==='ley'){
    /* Ley de un expediente que no está en la base de proyectos (p. ej. de años anteriores): link directo a la ficha del Senado */
    urlExp='https://www.senado.gob.ar/parlamentario/comisiones/verExp/'+exp.nro+'.'+String(exp.anio).slice(-2)+'/'+exp.origen+'/PL';
  }
  var linkHtml=urlExp?'<a class="od-nro" href="'+escAttr(urlExp)+'" target="_blank">'+esc(item.expediente)+'</a>':'<span class="od-nro">'+esc(item.expediente)+'</span>';
  var seccionHtml='<span class="od-tipo-tag">'+esc(SANC_SECCION_LABEL[item.seccion]||item.seccion)+'</span>';
  var odHtml=item.od_nro?'<span class="od-tipo-tag">OD N&ordm; '+esc(item.od_nro)+'</span>':'';
  var leyHtml=(p&&p.sancionado&&p.ley_numero)?'<span class="sanc-ley-badge">Ley N&deg; '+esc(p.ley_numero)+'</span>':'';
  var extractoHtml=p?'<div class="od-exp-extracto">'+esc(p.extracto)+'</div>':'';
  var solicitanteHtml=item.solicitante?'<span class="sanc-solicitante">Solicitada por '+esc(item.solicitante)+'</span>':'<span></span>';
  return '<div class="od-card"><div class="od-card-top">'+linkHtml+seccionHtml+odHtml+leyHtml+'</div>'+extractoHtml+sancObsHtml(item)+'<div class="sanc-card-bottom">'+solicitanteHtml+'<span class="sanc-fecha">'+esc(fechaSesionDisplay(item.fecha_sesion))+'</span></div></div>';
}
function renderSanciones(){
  var searchEl=document.getElementById('sanc-search');
  var q=(searchEl&&searchEl.value||'').toLowerCase().trim();
  var lista=(SANCIONES_DATA||[]).filter(function(it){
    var cat=sancCategoriaLanding(it);
    if(!cat)return false;
    if(sancCat!=='TODOS'&&cat!==sancCat)return false;
    if(!q)return true;
    if(it.expediente.toLowerCase().indexOf(q)>=0)return true;
    var exp=parseExpNumero(it.expediente);
    var p=exp?proyectoDeExp(exp):null;
    return !!(p&&p.extracto&&p.extracto.toLowerCase().indexOf(q)>=0);
  });
  lista=lista.slice().sort(function(a,b){return (b.fecha_sesion||'').localeCompare(a.fecha_sesion||'')});
  var el=document.getElementById('sanc-list');
  if(!el)return;
  if(!lista.length){el.innerHTML='<div class="no-results">Sin resultados para este filtro.</div>';return}
  var html='';
  lista.forEach(function(it){html+=buildSancCard(it)});
  el.innerHTML=html;
}
function renderPreferencias(){
  var lista=(SANCIONES_DATA||[]).filter(function(it){
    if(it.seccion!=='preferencia')return false;
    if(sancPrefCat!=='TODOS'&&sancTipoDe(it)!==sancPrefCat)return false;
    return true;
  });
  lista=lista.slice().sort(function(a,b){return (b.fecha_sesion||'').localeCompare(a.fecha_sesion||'')});
  var el=document.getElementById('sanc-pref-list');
  if(!el)return;
  if(!lista.length){el.innerHTML='<div class="no-results">Sin resultados para este filtro.</div>';return}
  var html='';
  lista.forEach(function(it){html+=buildSancCard(it)});
  el.innerHTML=html;
}
function setAmVista(id){
  var root=document.getElementById('am-root');
  root.querySelectorAll(':scope > .am-sub-nav .am-sub-btn').forEach(function(b){b.classList.remove('active')});
  root.querySelectorAll(':scope > .am-sub-content').forEach(function(c){c.classList.remove('active')});
  root.querySelector('[data-amvista="'+id+'"]').classList.add('active');
  document.getElementById('am-vista-'+id).classList.add('active');
}
function irASanciones(expediente){
  var it=(SANCIONES_DATA||[]).filter(function(x){return x.expediente===expediente})[0];
  if(it&&it.seccion==='preferencia'){
    switchMain('ayuda');
    setAmVista('preferencias');
    sancPrefCat='TODOS';
    renderPrefChips();
    renderPreferencias();
  }else{
    switchMain('sanciones');
    sancCat=(it&&sancCategoriaLanding(it))||'TODOS';
    var searchEl=document.getElementById('sanc-search');
    if(searchEl)searchEl.value=expediente;
    renderSancChips();
    renderSanciones();
  }
  window.scrollTo({top:0,behavior:'smooth'});
}

/* ── Tablero de Votación (artefacto) ─────────────────────────────────── */

(function () {
  "use strict";

  var SENATORS = [
    { banca: 1, nombre: "Juliana DI TULLIO", bloque: "Justicialista", provincia: "Buenos Aires", x: 230.9, y: 377.4 },
    { banca: 2, nombre: "Anabel FERNÁNDEZ SAGASTI", bloque: "Justicialista", provincia: "Mendoza", x: 239.7, y: 326.4 },
    { banca: 3, nombre: "José Miguel Ángel MAYANS", bloque: "Justicialista", provincia: "Formosa", x: 265.6, y: 281.5 },
    { banca: 4, nombre: "Marcelo Néstor LEWANDOWSKI", bloque: "Justicialista", provincia: "Santa Fe", x: 305.2, y: 248.2 },
    { banca: 5, nombre: "Fernando Aldo SALINO", bloque: "Justicia Social Federal", provincia: "San Luis", x: 353.9, y: 230.5 },
    { banca: 6, nombre: "Enrique Martín GOERLING LARA", bloque: "Frente PRO", provincia: "Misiones", x: 446.5, y: 230.5 },
    { banca: 7, nombre: "Luis Alfredo JUEZ", bloque: "La Libertad Avanza", provincia: "Córdoba", x: 495.1, y: 248.2 },
    { banca: 8, nombre: "Patricia BULLRICH", bloque: "La Libertad Avanza", provincia: "Ciudad Autónoma de Buenos Aires", x: 534.8, y: 281.5 },
    { banca: 9, nombre: "Ezequiel ATAUCHE", bloque: "La Libertad Avanza", provincia: "Jujuy", x: 560.7, y: 326.4 },
    { banca: 10, nombre: "Agustín Pedro COTO", bloque: "La Libertad Avanza", provincia: "Tierra del Fuego, A. e I. del Atlántico Sur", x: 571.1, y: 377.4 },
    { banca: 11, nombre: "Lucia Benigna CORPACCI", bloque: "Justicialista", provincia: "Catamarca", x: 163.4, y: 377.4 },
    { banca: 12, nombre: "Martín Ignacio SORIA", bloque: "Justicialista", provincia: "Río Negro", x: 167.9, y: 332.7 },
    { banca: 13, nombre: "Mariano RECALDE", bloque: "Justicialista", provincia: "Ciudad Autónoma de Buenos Aires", x: 181.7, y: 289.8 },
    { banca: 14, nombre: "Eduardo Enrique DE PEDRO", bloque: "Justicialista", provincia: "Buenos Aires", x: 204.2, y: 250.9 },
    { banca: 15, nombre: "María Florencia LÓPEZ", bloque: "Justicialista", provincia: "La Rioja", x: 234.4, y: 217.5 },
    { banca: 16, nombre: "Jesús Fernando REJAL", bloque: "Justicia Social Federal", provincia: "La Rioja", x: 270.7, y: 191.0 },
    { banca: 17, nombre: "Julieta CORROZA", bloque: "La Neuquinidad", provincia: "Neuquén", x: 311.9, y: 172.7 },
    { banca: 18, nombre: "Beatriz Luisa AVILA", bloque: "Independencia", provincia: "Tucumán", x: 355.8, y: 163.4 },
    { banca: 19, nombre: "María Victoria HUALA", bloque: "Frente PRO", provincia: "La Pampa", x: 444.5, y: 163.4 },
    { banca: 20, nombre: "Rodolfo Alejandro SUÁREZ", bloque: "UCR - Unión Cívica Radical", provincia: "Mendoza", x: 488.7, y: 172.7 },
    { banca: 21, nombre: "Mariana JURI", bloque: "UCR - Unión Cívica Radical", provincia: "Mendoza", x: 529.6, y: 191.0 },
    { banca: 22, nombre: "Eduardo Alejandro VISCHI", bloque: "UCR - Unión Cívica Radical", provincia: "Corrientes", x: 566.2, y: 217.5 },
    { banca: 23, nombre: "Daniel Ricardo KRONEBERGER", bloque: "UCR - Unión Cívica Radical", provincia: "La Pampa", x: 596.3, y: 250.9 },
    { banca: 24, nombre: "María Emilia OROZCO", bloque: "La Libertad Avanza", provincia: "Salta", x: 618.8, y: 289.9 },
    { banca: 25, nombre: "Bartolomé Esteban ABDALA", bloque: "La Libertad Avanza", provincia: "San Luis", x: 632.6, y: 332.7 },
    { banca: 26, nombre: "Agustín Aníbal MONTEVERDE", bloque: "La Libertad Avanza", provincia: "Ciudad Autónoma de Buenos Aires", x: 637.4, y: 377.4 },
    { banca: 27, nombre: "Daniel Pablo BENSUSÁN", bloque: "Justicialista", provincia: "La Pampa", x: 97.3, y: 377.4 },
    { banca: 28, nombre: "Sergio Mauricio UÑAC", bloque: "Justicialista", provincia: "San Juan", x: 100.3, y: 335.5 },
    { banca: 29, nombre: "Carlos Alberto LINARES", bloque: "Justicialista", provincia: "Chubut", x: 109.6, y: 294.5 },
    { banca: 30, nombre: "Cándida Cristina LÓPEZ", bloque: "Justicialista", provincia: "Tierra del Fuego, A. e I. del Atlántico Sur", x: 124.9, y: 255.4 },
    { banca: 31, nombre: "María Teresa Margarita GONZÁLEZ", bloque: "Justicialista", provincia: "Formosa", x: 146.1, y: 219.1 },
    { banca: 32, nombre: "Juan Luis MANZUR", bloque: "Justicialista", provincia: "Tucumán", x: 172.2, y: 186.2 },
    { banca: 33, nombre: "Guillermo Eduardo ANDRADA", bloque: "Convicción Federal", provincia: "Catamarca", x: 202.9, y: 157.7 },
    { banca: 34, nombre: "Sandra Mariela MENDOZA", bloque: "Convicción Federal", provincia: "Tucumán", x: 237.6, y: 134.0 },
    { banca: 35, nombre: "María Carolina MOISÉS", bloque: "Convicción Federal", provincia: "Jujuy", x: 275.5, y: 115.8 },
    { banca: 36, nombre: "Flavia Gabriela ROYÓN", bloque: "Primero los Salteños", provincia: "Salta", x: 315.6, y: 103.4 },
    { banca: 37, nombre: "Edith Elizabeth TERENZI", bloque: "Despierta Chubut", provincia: "Chubut", x: 357.2, y: 97.1 },
    { banca: 38, nombre: "Andrea Marcela CRISTINA", bloque: "Frente PRO", provincia: "Chubut", x: 443.2, y: 97.2 },
    { banca: 39, nombre: "Maximiliano ABAD", bloque: "UCR - Unión Cívica Radical", provincia: "Buenos Aires", x: 484.8, y: 103.4 },
    { banca: 40, nombre: "Mercedes Gabriela VALENZUELA", bloque: "UCR - Unión Cívica Radical", provincia: "Corrientes", x: 525.0, y: 115.8 },
    { banca: 41, nombre: "Eduardo Horacio GALARETTO", bloque: "UCR - Unión Cívica Radical", provincia: "Santa Fe", x: 562.6, y: 134.0 },
    { banca: 42, nombre: "Carolina LOSADA", bloque: "UCR - Unión Cívica Radical", provincia: "Santa Fe", x: 597.4, y: 157.7 },
    { banca: 43, nombre: "Silvana Lorena SCHNEIDER", bloque: "UCR - Unión Cívica Radical", provincia: "Chaco", x: 628.3, y: 186.2 },
    { banca: 44, nombre: "Flavio Sergio FAMA", bloque: "UCR - Unión Cívica Radical", provincia: "Catamarca", x: 654.5, y: 219.1 },
    { banca: 45, nombre: "Joaquín Alberto BENEGAS LYNCH", bloque: "La Libertad Avanza", provincia: "Entre Ríos", x: 675.4, y: 255.5 },
    { banca: 46, nombre: "Bruno Antonio OLIVERA LUCERO", bloque: "La Libertad Avanza", provincia: "San Juan", x: 690.8, y: 294.5 },
    { banca: 47, nombre: "Ivanna Marcela ARRASCAETA", bloque: "La Libertad Avanza", provincia: "San Luis", x: 700.1, y: 335.5 },
    { banca: 48, nombre: "Juan Carlos PAGOTTO", bloque: "La Libertad Avanza", provincia: "La Rioja", x: 703.7, y: 377.4 },
    { banca: 49, nombre: "Gerardo ZAMORA", bloque: "Frente Cívico por Santiago", provincia: "Santiago del Estero", x: 30.5, y: 377.4 },
    { banca: 50, nombre: "Elia Esther del Carmen MORENO", bloque: "Frente Cívico por Santiago", provincia: "Santiago del Estero", x: 33.7, y: 330.0 },
    { banca: 51, nombre: "José Emilio NEDER", bloque: "Justicialista", provincia: "Santiago del Estero", x: 43.6, y: 283.6 },
    { banca: 52, nombre: "Adán Humberto BAHL", bloque: "Justicialista", provincia: "Entre Ríos", x: 59.3, y: 238.9 },
    { banca: 53, nombre: "Jorge Milton CAPITANICH", bloque: "Justicialista", provincia: "Chaco", x: 81.2, y: 196.8 },
    { banca: 54, nombre: "María Celeste GIMÉNEZ NAVARRO", bloque: "Justicialista", provincia: "San Juan", x: 108.5, y: 158.0 },
    { banca: 55, nombre: "Alicia Margarita KIRCHNER", bloque: "Justicialista", provincia: "Santa Cruz", x: 140.9, y: 123.3 },
    { banca: 56, nombre: "Ana Inés MARKS", bloque: "Justicialista", provincia: "Río Negro", x: 177.5, y: 93.4 },
    { banca: 57, nombre: "Natalia Elena GADANO", bloque: "Movere por Santa Cruz", provincia: "Santa Cruz", x: 218.2, y: 68.8 },
    { banca: 58, nombre: "José María CARAMBIA", bloque: "Movere por Santa Cruz", provincia: "Santa Cruz", x: 261.7, y: 49.8 },
    { banca: 59, nombre: "Carlos Omar ARCE", bloque: "Encuentro Misionero", provincia: "Misiones", x: 307.4, y: 37.0 },
    { banca: 60, nombre: "Sonia Elizabeth ROJAS DECUT", bloque: "Encuentro Misionero", provincia: "Misiones", x: 354.3, y: 30.6 },
    { banca: 61, nombre: "Alejandra María VIGO", bloque: "Provincias Unidas", provincia: "Córdoba", x: 445.8, y: 30.5 },
    { banca: 62, nombre: "Carlos Mauricio ESPÍNOLA", bloque: "Provincias Unidas", provincia: "Corrientes", x: 492.9, y: 37.0 },
    { banca: 63, nombre: "Romina María ALMEIDA", bloque: "La Libertad Avanza", provincia: "Entre Ríos", x: 538.6, y: 49.8 },
    { banca: 64, nombre: "Gonzalo GUZMÁN CORAITA", bloque: "La Libertad Avanza", provincia: "Salta", x: 582.2, y: 68.8 },
    { banca: 65, nombre: "Vilma Facunda BEDIA", bloque: "La Libertad Avanza", provincia: "Jujuy", x: 622.7, y: 93.4 },
    { banca: 66, nombre: "Francisco Manuel PAOLTRONI", bloque: "La Libertad Avanza", provincia: "Formosa", x: 659.5, y: 123.3 },
    { banca: 67, nombre: "María Belén MONTE DE OCA", bloque: "La Libertad Avanza", provincia: "Tierra del Fuego, A. e I. del Atlántico Sur", x: 691.9, y: 158.0 },
    { banca: 68, nombre: "Carmen ÁLVAREZ RIVERO", bloque: "La Libertad Avanza", provincia: "Córdoba", x: 719.3, y: 196.8 },
    { banca: 69, nombre: "Nadia Judith MÁRQUEZ", bloque: "La Libertad Avanza", provincia: "Neuquén", x: 741.0, y: 239.0 },
    { banca: 70, nombre: "Mario Pablo CERVI", bloque: "La Libertad Avanza", provincia: "Neuquén", x: 757.0, y: 283.6 },
    { banca: 71, nombre: "Enzo Paolo FULLONE", bloque: "La Libertad Avanza", provincia: "Río Negro", x: 766.4, y: 330.0 },
    { banca: 72, nombre: "Juan Cruz GODOY", bloque: "La Libertad Avanza", provincia: "Chaco", x: 770.1, y: 377.4 }
  ].map(function (s) { s.id = s.banca; return s; });

  var PHOTOS = {
    1: "data:image/jpeg;base64,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",
    2: "data:image/jpeg;base64,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",
    3: "data:image/jpeg;base64,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",
    4: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV0fhbwF4h8Xyf8SuxY24OGuZfkhT/gR6/QZPtXoXw2+Cz6gkOseKYillIm+GxyyySZ6M+MFV7gdT7Dr7tb2sFpbR29tDHBBGMJHEoVVHsBwKAPKdC+Aeh2axyaze3GpSgfNHF+5izznkfMRyO45HvXb6d4G8MaVD5VpoFgowFJkhErNjpkvnmuiICjJOB61AbglSyRnYOrPwAPXjP64oDYdt4AAwBwKjuLSC7gMFzBFcRNgmOVA6nHIyDxVu3urKSPLsElTqjHhvcetMTWNLd2R4whHBwenvTsF7nM6r8PfCmtJtvNCtA20KHgTyWABzwUx615v4j/Z+Ahabw5qbM45Fte4G7gdJBgZ69QByOe9e6tbqYhNA4lhP8Q6j61FtpDPjHWvD+q+Hb42erWE1nOOQsi4DD1B6Ee4rOr7R1nQtN8Q6Y+n6raR3dq3O1uqnBG5T1U8nkV82fEf4XXngiZbu2d73SJTtWcrhom/uuBwD6HofrQI4GiiigAHWvavgn8NIdRRfFOtWyy2yt/oETEFZGUkM7L3AIwAepB4wK88+HvhN/GfjWy0r5hbk+bcuv8ES8sfbPQe5FfYNvaQ2lrDbW8QiggRY40HRVAwB+QoAaVycnkmoLmZLaEuwJPZQMk1d2Vja0s80n2e3kKuy9FQMef5U0rsG7I4TXvEF7e69HZWkJurgfdhi4KfmPzzXV6N4e1+aFGubxojnIWM42/j1/pVzw9olj4ch2/629mOZpn5Zj6ewHpW+kjmUbJMj0HasHUd7I6Y01y3ZWt/BJaLEk6uevHHNPufA9u65kYHjHB5q7PHeBd4duewPBpY3vJoywwF9qu5NjOtdAuNMeT7NctLbsDuiYZYfT1pFG7p83uK0IrqaCTLOGAPaoyiLetPDhYpPmZeyn1HsaUHd2Yqsbaoqbahu7G21Cyms7yCO4tp0KSRSDKup7GrzKCxI4GeKTZWhkfKHxT+HTeBdaje0Mk2k3uWt5GHMZB5jY9yBg57gjvmuCr7S8W+FbPxh4ZutHvAFEwzFLgZikH3WBwcc8H1BIr421GwuNK1O5sLuMxXFtI0UiHsynBoEfRP7O3h0WfhC812WMCbUZvKibHPlR9cHPQuT2B+XuDXsG2svwdpP9ieCNF00o6Nb2causgwwYjcwPuCSPwrZ20DIttcrrF69h4tgK7mBiDeWO57V2G2uO8X2rPrlhKpI/dMD+f8A9ek3bUcVd2KUN2rXc93dSMlsGyGJ6modR8b2FvF+5mlXnAMa5zWT4kknjeGFLV3TG5Ih0Y+/sK5xl1k3GySdI4cElVQdfSuS92zvtZI7fSfHV3MwjimMinkbxzUeofEG5tJ3juJnUIcbYx196zvh7pE174mje7CJAqkyFRwT2FVfHGlTWviqdoVTyWYbGI6D/wCtSu7XuX7t7WOq0vx3pmoMkck7gvwCy7T+dbQ1BoJ5bVvmikjOxq8osbjVU3CeOG7t1/5ZhhuK9yPQ13/h/N/pUfzeY0LKEJ6lc/xD1q4u0lYykrxdzslTCL9BS7am2c0ba6jhIdtfNn7RHh82HjS11iNAItUgG8gAfvU+U5wO67Tk8nn0r6Y21k+IfCWi+LbKG11qwF7FA5kjQuy7WIwT8pHagDdK88Ck21NtB5HQ9KNtAivJhInZjtVVJJ9BjrXkWl61f6lesL64edUiLqSf4d4wSO2eK9jeISRtG33XBU/Q8V5ANObR7u7bcQzMAYyvTaSBz3FY1L3R1UGuWSe+hvw6hY6oGtWtnlCHHmqcbT9ahurDQNOia4u3eXaOFJ5NYU15LbxYiPllzk4PWqqQfaD9ov5isCnCg9zXOtWdTslc7jStc03RRmfyIpXG7yo+fLHZSe59abqt9pmoeXcMiNZSP5byKfmikPTPsfWvJdRtHjmkktWLbjlhuyfyrW0OzthFcG7ubhVmUblZ/l3Z44q73VhNRXvHoVt4Z0yIi4huPMXqAAMn8atNfwRRtFbIUeMbhzycVxdtfXWmMIvPEsR+6watpZlmmhuAfnchWz70lvsDSave53mnea+mWzzsHleNWcjpkjPFWdtNsoylhApzlUA5qxtrrWx50t2Q7afGShJHen7afHEGJyQMetMk5r4baqmufDPw/fJs5s0hYISQGjHlkc/7vPvXT7a8I/Zi8UJNpmp+Fppf30D/AG23U9ShwsgHPYhTj3J7173toAj21594y0G4szcao1/5ltLMAIDHgxlup3Z56elei7ayPFWn/wBoeFdQg25byi6j3X5v6VMldFwk0zyC4IN1hj+7BOcHgUsujLrR+eaaG1QAqsbYLH6iqk7B4o5g45ABB7/WtrQ9RhER80qFQZwB1+tcvLd6Hbz23OYudHsrebyo7O6kxxu85h/KtHTfDmmalAYVhvrOQdZFnYhvqG610d7r1hvEkMYLJ0zxnir1r4js51MbRxKcduCaai+5cqmhzdrpD6eZrOa4N1ggo7CtDTl+1yw2KNtleRVB67cnrVPVtSha8TyyVaNh91sZz2rp/BtoLnxDHKqg+RGZZW9+ij9SfwqlHUydT3WdvYWklnYRW81y91JGMNM6hS/vgdKs7ak20ba6TibvqR7a5Tx58Q9F+HljZz6ulzL9skZI0tlR3+UZJwzLxzjPrXX7favkn9oTxUNe+JMmnQuWttFT7IoDZUyZzI3sc4X/AIAM0COF8G+J7rwd4v0/XLQbntJQzJnHmIeGTPupI/GvuXQdZsfEmgWesaZKJbO8jEkbA5x2Kn3BBB9wa/P6vTvhP8X9Q8APPp0/+l6VcDKRSMdtvLkfvB3xjIIGM8HtyAfYe3JxXNeO/FFn4X8OyPNLF9quWW3ghZhuYuQpOPQAkmvINZ+JniPVYmP9om3gYZC2oCKQenI5P515trlxcXhZ5ZmaQ872bJz25raVJx3M1NPY7+6Rra4mt2B2oxQg+xxUUUoijMakgehqa+uYb/wvYa6bmO1uJY41/eH5ZyRjb7MCDz6day3mkjdftEewsMqwO5W/GvPlCUH5HpwnGovMfM9xuIjPXv7Vas1nXBab5z0PXFUTL833hirMWowxDkZx3xQ5WKcC1FARfedIN57bj0r0n4baxYrquq6RLJHHqCmOTDMAXG3JUe4yMj3rzqC/t7e4e61R47e3tbdrtbZmxJOF6HHZckfWuDtNQubu/lvbg/v7l2mfHqxz/wDWrelBy1ZyVpqPuxPsgoQeQRSba+c9E+IHiDRGRbe+d4Rj9zNmRCPoen4V6DbfG7RbbSpLvXbeSz8teWg+cOeyqDzk10yoySucqqJ6Gv8AFTx1H8P/AAPcaijqNSuMwWCFc5lP8RGMYUZbnrgDvXxNPPJc3Ek8zmSWVi7sxyWJOST+NdR8RvHt98QvFcuq3SGCBR5dtbByywxjoPqepPc/hXJ1iaBRRRQBu6V4ourGCO0n/f2keQicApk5JB7/AEP6V1KNb3lv9pt3EyNn5/T8O1ec1NbXc9pKJLeV4mHdTjP19a0jUtoyHG56NdatDcaDoWkRzK0tpJLJKmcbTu+Qflk11CXU985F8qxJIoX7pJUjofavL9M8T28YdNU09bhWO4SxHY6cdux5xXonhXWotShMSiV4gFAMgAcbhkDg89PanpIpNxLkcKQSFJIyXHFXbWw8+0nu0Kx/ZyANwyM4zn61Jq8QsI0P+sHAXPXB6Z+hpdSmk0/TUsrfb5jZZnbpn1x+X5VywpNVLPZHZOqnSTW7PN9UkmbU7uO5ZvtE7KuGByYwckk+5AFW7aIDDrgMOoPeoPEoTRryCa7eSeSe3FwWHJbc5Xknp938sVzN14qu5YjHbotsp6spy/59vwFdylGO5wNOWx2eo63ZaVahp2LSg4ESkbyPoen1rgdY1u71mZWnIWNMhI14Vf8AE+9UHdnYs7FmPUk5JptZzquWnQcYKOoUUUVkWf/Z",
    5: "data:image/jpeg;base64,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",
    6: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV03hX4feIvGEmdMsWFsDhrqb93Cv/Aj1+gyfavRfhv8ABNb22t9a8UqwglBaLTuUdwQNruwOVHU7RyeM4BxXt8hgsbHLmO3tbaPjoqRIo7DoAAKAPLNC+AmgWSpJrF5c6pKB80cf7iLPPp8x6juOR3BxXcWng3wzpySfZvD+mQq+NxNurZx05bOOprz7xP8AHCOGVrfw9bLKBx9puBwf91fT61wd94+1fWHL319LLu42D5VA9lGBU3KsfRc2t6bGxE2qWqkf3p1H9aFutM1m3a3FxZ6hC2N0RZJVODkZXnvXzJORdJvVFUHnnt+dZzu0Lh43IYdw+3+VFwsfSupfDvwlqvmfa/D9mHlxueFTC/HTBUjHTt1rznxH+z8ggebw5qbtIORbXuBu4HSQYGevUAcjnvVT4e/FBtHglstZnlngHMLM24g/3cntXr2h+KtO12NWt5NpboGPU0XFY+Ttb8Pat4dvjZ6tYTWcw5AkXAYeqnoR7is2vtLV9F07X9MfT9Vs47y1fJ8tx904I3Kf4WGTgivm34lfC278ETJeWjyXujykKs7Lhon/ALr44Hseh+tUI8/ooooABXuXwW+F0Nxbx+KtetGZSwbT7eVRskA/5bMO4BGFBGD15AFed/DTwVJ458ZQaeSY7OEefdyAfdiUjIHuxIUfXPQGvryOCOGNYoYkhiQBUjRQqoo4AAHQAUARkZJJySeST3ryL47+Ims9Ms9Cgm2td5muFU87AflB9icn/gNexhMkD1r5L8fajc67401O9l6G4aNPZVO1VH4CkxnMkhjwP1qaG1llG5VYD1rV8O+FrzXLsxxrsVT8zNwBXsvhj4faTpSo9wgup/7z9B9BWM6ijob06Mp6nj+n2F3ACXs7hg64G0ZBpreHNTuX/dabPtbofLP86+qbHRbIRhxAowOPlqS406IIQEAx6Cs/avc6Pq8drnyxfeCtWsrMXJtnwoDMMcjNanhLXJ9Eu47qE7lT/WQnkOO9e46pBHMjRlBgjnivA/GGjvoviWc2y7IZF81QOg9adOpzOzIrUeRcyPp+xuYb+wgu7dw8MyCRGHcEU67sba/sprO7gjuLadCkkUgyrqeoNedfA7xCdW8OXOmyvmSxfcoJ5CN/9fNeo7K6UcZ8o/FX4ct4F1mOSzMs2kXuWgkdeY2HWJj3IGCD3B9c1wNfafivwrZeMPDdzo18NqzDMcoA3RSD7rA4OOeD6gkV8balp9xpWqXOn3cZjuLWVopEPZlODTEfSX7PvhsaZ4Dm1mRCtxq8xwd3/LGM4Xjtli5+gGOterbaqaBo/wDYPhnTNIxg2NrHAw3lwGA+bB7jcWx7YrQ20DK8w2wSMDjajHPpxXxhf3PmTlgxOXJznpzya+1zEsgKMMq3ykeoPBr4w8T6YumeJb+zh3eVFcOibhg4DECk9xpOx6B8PX/cyzoP3ZYKD6mvWLZGbyyvTHPavMNHsbiy8NWsdiAsqpuJxnnv+NZ1/wCIr2OIia91PG4xM8KDhsZxXA1zyuenCXs4JH0JZsBEMsAfrT5yvlEhgSeMZzXh+jJreh6ir3F1fSwsy7jNyFDYwTzx1FdX41m1aMQ2unTSCSVNzspxgdKe2g9XqdNdxLuz8pHevH/iohiRJkxlCUzj1FVoP7asdQvIJjfzmFDI7vLhWAx9zsTz69jSeIbS6uvB13c3AmPR0EnJAB5pxjyyTInPng1Y6f8AZ4075da1HIGRHAFH4tmvbdtcz8NPDcXhzwHp8ARRc3MYubhl/iZhkc+wIH4V1m2u1HmkO2vm39onw8bHxnaazEgEWqQAOQB/rY/lOcDuu05JyefSvpjbWbrfhjRfE1pFba3pkWowwuZI0kLAKxGCflI7UwNhgWYsepOaTbU7x7XI9DSbaBEIXBzXzn8W9Dgg1a5uolIlS6KsuOx5B/WvpLbXnPxN8NNeRT30VrLKj2zeYY03FXUZBIHQEDr7VlVTsmjei1dxfVHJeA7yKW08iRVOecN2rq18LW7TNcRsEDtkgAYP6da8u8P3f2QLOpwA67selenW/iP9yIrfDOR1Y4Vfc1xbM9KOsblTWNMjtQkayO0krAsGbjg9P0q5qMay3drJImY2TY+Djg9K5PxN4oOkapFLdRyXNsxUvOvIjIzkY9OlWdc8e6dcxWtvpWby6kwdiHoPUnsKfKyuaNtzq5PDkMqYSRlXrggH+YrlPHaBtDl06DBkmAjQAYySRk1rReJGtoVLTi4iwAxxhkPv6isix3eJviDYW0BUiN/Mfd0AX5m+vH86Em5JGc2lBs9isrX7Lp9tb9fKiRPyUCpttTFckn1o216J5BDtpyEoSR3qTbTo4g5OSB9TQBieB9Z/4SPwHourNIZJLm0QyMXDkyAbXyR3yCT9a3tteHfsz+Lku9CvfCdxIftFm5u7YMc5iYgOo9MNz/wM17rtoAj21HPbi5t5YG6TI0Z/EEf1qxto2ntQB8n6aWs7+40uf5JI2aMBvUEjH5iuutoG1LTEazuFhnXKMCMgN74rK+IcWmy/EC/n0i7injkcTq8Z+QOeJFz3G4HkdCar6XfGzvVnUssNwwSZGODG4/z+Ncco2Z3wloay/wBqzo1nf6DBOqnZxcZD/TiobfS20OFxZ+F47aZzn99MSW9vpXRIk0zedBIVdxgkdiOKJbO/YZub6V93HzMDxUJ6HVeGmhkW9lNHavqOpSxxkqXNvCcqv4nkn9K6j4Q6W0+p6hrLJiOJPIQjoXchm/JQo/GuR1CObWdZsNAsHDXF1IEXJ4H19uCfwr3rQtDtfD+h22mWg/dQLguRzIx5Zz7k81tSjd8zOKvNL3UXNtG2pNtG2uk4yPbXJeP/AIi6R8OrCzuNUguLn7ZIyRx2xTeNoyWwxHHOM+tdjtPpXyT+0N4p/t34kvp0T5ttFT7IoDhlMmd0jcdDnC/8A55oQ07HC+DPE9z4O8YadrlqNz2koZkzjzEPDr+KkivurStTstc0i11TTpvPsruMSwyYIyp9j0PYivz5r1v4JfF1fAt9JpOtvNJoV0QQykt9kk/vhe6n+ID0BHfII+tttebfGTx5B4W8MTaTbyE6tqkLRxhGwYYzw0h9O4HqfpXEeLvj/qF8Xt/C1v8AYLYji7nUPM49VXov45NeRahqN5q17LeahdTXV1JjfJM5Zj6cmqUbiueueE/DWmeJPCtmpXymSMLHJGMNGcYx/wDWNZXinwFrmiI8iwm6tCOJoRnA+nUfT9ab8HteW21B9Mmc7JPmQH9f8fzr30Irw7G5UirdOM1qSqkoPQ+bNJ8W3VhgSgyAYG5ev1x61evfiA0lq0cMUkkjZHzLjFd74u+E9rqU0l7pmLa6blk6RyfUdj7iuL0P4fXGpaybKSFrbym/0mQ8mMdwO249vzrllScZWtudUK143vsWfhhazN4oi8W6pMLeys3IaZ+FyVIJz6KDyfevo1NrxrIjBkcZVlOQw9Qe9ef6vpFnZ+D5tNtoFjt1t2hSMdAMGvnnw1458R+E3H9karPBGp5hY+ZC31Q8flg10OnyqxzKpzu59j7aNteQeE/2gdMvvLtfEtodOuDwbqAF4CfUr95f1Feiat448N6N4Vl8Rz6rby6bGOJIJBIZWPRFAPLH0/E4ANTaxRj/ABU8dR/D/wAD3Goo6jUp8wWCFc5lP8RGMYUZbnrgDvXxLPPJc3Ek8zmSWVi7sxyWJOST+NdR8RvH198Q/Fcmq3SeRAg8u2tg5YQxjoOe56kjGTXJ0gCiiigC9Z6nNbARsS8Q42nt9K24p454w8Thwfz/ABrlqfFK8L742KsO4NUpWE0dzo+oy6RqttfxctA4fH94dx+IyK+tNPuYr3TLe6gkEkM0YdHByCpGRXxLb69LGf30Syc9R8pr6Q+BviuPV/DUOl7JQ0DOgLAbQMFxjn0yD7geprWMkZyR6LrWrw6JoF5qU5XbbxlgrHAZuir+JIFeDJ4p1vRrwa5FqU0nmxrJN5gd4mByCrJwPvcZHTseMV1/x41a5sdA0yC2keON7kSuUbaxKg7B9Ack/hXmd5D51zZ6VdFdzXMcJkRclhKVPJJ5xu9PWqvcix7foniW18X+GrfUbdDGH+SaFjzFIPvKfz4PcEV8238RtdXuISu3DspB7YYivY/GHi/QPhv4imtrawu3DRxw3EEQRYywTMbqSeu35TwM/hXhHiHxM2t6rc3kVotkJ5DJtVyxXIGRnjvk9O9TN2epUF2Jby7itCAzZPZV6/8A1qw7m8muWO9sKTnaOgqEsWJJJJPc0lYt3NUgooopDP/Z",
    7: "data:image/jpeg;base64,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",
    8: "data:image/jpeg;base64,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",
    9: "data:image/jpeg;base64,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",
    10: "data:image/jpeg;base64,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",
    11: "data:image/jpeg;base64,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",
    12: "data:image/jpeg;base64,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",
    13: "data:image/jpeg;base64,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",
    14: "data:image/jpeg;base64,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",
    15: "data:image/jpeg;base64,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",
    16: "data:image/jpeg;base64,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",
    17: "data:image/jpeg;base64,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",
    18: "data:image/jpeg;base64,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",
    19: "data:image/jpeg;base64,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",
    20: "data:image/jpeg;base64,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",
    21: "data:image/jpeg;base64,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",
    22: "data:image/jpeg;base64,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",
    23: "data:image/jpeg;base64,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",
    24: "data:image/jpeg;base64,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",
    25: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV03hX4feIvGEmdMsWFsDhrqb93Cv/Aj1+gyfavRfhv8ABNb22t9a8UqwglBaLTuUdwQNruwOVHU7RyeM4BxXuaRJFDHDGixxRKERFGFRQMAADoABQB5RoXwE0CyVJNYvLnVJcfNHH+4izz6fMeo7jkdwcV3Nn4M8NWAcWvh7TIg+N3+jq+cdPvZ9T0rdkZIkLyMFHqayp9aXfsgTd2yaznUjD4ma06UqjtFGkxZvvMT9TUdxbxXdu1vcxR3ELY3RyoHQ4ORkHg81npcX8vzA8enSrCXksZ2ypn3xWKxUGzoeDqJXMfUvh34S1YSfavD9mHlxukhUwtx0wVIx07da858R/s/IIHm8Oam7SDkW17gbuB0kGBnOeoA5HPevbInSZcqfwp+2ulNPVHI007M+Mtb8Pat4dvjZ6tYTWcw5AkXAYeqnoR7is2vtLV9F07X9MfT9Vs47y1fnY4+6cEblPVWGTgivm34lfC278ETJeWjyXujykKs7Lhon/uvjgex6H60yTz+iiigAFe5fBb4XQ3FvH4q160ZlLBtPt5VGyQD/AJbMO4BGFBGD15AFed/DTwVJ458ZQaeSY7OEefdyAfdiUjIHuxIUfXPQGvryOCOGNYoYkhiQBUjRQqoo4AAHQAUARlckk5JPUnvUF3PHZ2klxLwka5OOp9qu7K5Px7cPDp9rbrnEshZvcDp+pqZPlVy4rmaRnXmtSXshPQHgAHgCrmlwGVc45PrzXM2bF7kxk844rq9MnEaLtxjoa8WcnKV2fQU4qEbRNyG1IQDAPHWlmtuCMZI9qW3uVIzhePwNOkuMt0Gf96nZWDmdzOUi2lweFJ7dq0LaZbgMOjocMP5Gsu9kDyYxtx39aNEnL6o0ZJyYyD+ByK6cNUtLlOPF0k485tbKiu7G2v7Kazu4I7i2nQpJFIMq6nqDVzZRsr0jyT5R+Kvw5bwLrMclmZZtIvctBI68xsOsTHuQMEHuD65rga+0/FfhWy8YeG7nRr4bVmGY5QBuikH3WBwcc8H1BIr421LT7jStUudPu4zHcWsrRSIezKcGgR9Jfs++GxpngObWZEK3GrzHB3f8sYzheO2WLn6AY616ttqpoGj/ANg+GdM0jGDY2scDDeXAYD5sHuNxbHtitDbQMi21wvxLkaCCyYDg7+fpg135XAJxnHNeHax44n16KTT9RiEdxBOWCEBcDBGFPcdODzWNWSSs+pvRhKT5l0K9pqBjukkcgIIyxJ9K0Lfx8I2KWOlXV4RwHA2r+dc7DY3F0yhWAWNRkH+IGtNE8TXoig06ztYLMnY5ZQZMZ689B14HNedGMWz1JSkloehaL4oiv49s0D28uRlWIP6irWpa7Z6bE8sgLYGcAc1xcuhy6Xe21xFd718zbtI5x/h2xWvrWjprF3bYmMXyls9QT9KHa9i0pctynH8R/D167pK8tq6nBWVMZ+mOtaug3sL6/BNDKrwyD7+cggiuPufCfiAXdzjVLa608gmOG6jVgPY8Ar35FXvDOjf2ZeQxY8lZX8t4gSVUsccH0q1FRkmjGTlKLUj13bRtqbZjgDpRtr1DxyHbXzb+0T4eNj4ztNZiQCLVIAHIA/1sfynOB3Xack5PPpX0xtrN1vwxovia0ittb0yLUYYXMkaSFgFYjBPykdqANhgWYsepOaTbU7x7XI9DSbaBEO2vAfiRo8en+I7toZSGjuFk8sj+FgCCD+Y/CvoTbXmHxl0Rn0yDWoQAY/8ARrjC5JQnKk/Q5H41jWjeN+x04afLKz6nM+FDHNCu5dyjp7V2VlYRiQeXlixJ5GMfWvNPC161vAmG43lT/SvRbbUfLgBTqecmvLtaR7MWmiDxCinU7W1Q7AuDu6fp2q7d23kvBKDkDA57e9cn4l0nUtdujc6fqTQyqVKANgZUdD6g+lWLe08RX8MZ1i6jhEDgxpDIevQlvUdeOnrWns7q4vaW907WWFJFDPGpOOpHINY98At/Yopxm4jAx1PzCrL3ZhhAQ8AYx1xWXZv9t8VachOR9pTHtg5P8qlaySFOyg2eoFfmP1pNtTbaNtewfPkO2nIShJHepNtOjiDk5IH1NAGJ4H1n/hI/Aei6s0hkkubRDIxcOTIBtfJHfIJP1re214d+zP4uS70K98J3Eh+0Wbm7tgxzmJiA6j0w3P8AwM17rtoAj21ieM1/4oTXBnANjLz/AMBNb+2uG8ceLLcXMvg6wT7Xqt9bSeeFPy2sRXG5v9o5AC++TSlsOO6PCtGuWheeMjlDuKmvRL6KS40GO4sZE37fut0P1rzYxy2dyrTxtFcQnyLqNhgjsGrsdD1HFmbZmyYmGOfvDsa8qSs7ntx10IdP1XWoyEfRZptneGRXB+mDWxLqurvEDb6Hdxr3+0MEGafBpV004uLOZVDcsmePwrRXTdQY7ZrhkQ9cnJNaKatsXyLsU9ETUplefUfKjTnCI5bHtnArT8HwDUPG0ckagxWitMx98bV/U/pVDUbhbKzaJX4C4GOSSegFegeCfDbaDou65XF9d4kmB/g9E/Dv7k0UYc879jmxM+SHL3Og20bak20ba9I8kj21yXj/AOIukfDqws7jVILi5+2SMkcdsU3jaMlsMRxzjPrXY7T6V8k/tDeKf7d+JL6dE+bbRU+yKA4ZTJndI3HQ5wv/AADnmhDTscL4M8T3Pg7xhp2uWo3PaShmTOPMQ8Ov4qSK+0bv4geE7Hw/a61ca1bxWV7EJrfcSZJFPon3s9jx1r4Sq5ZXnknY/wBw8A/3aBH0f4s/aHje3ntPC1hKkjDat9dYBT/aWPnn03H8KyvgBA2r+LtdvLuV57r7OjF5G3M5aT5mJ7ngV40jBlGOeK9U/Z71NbL4mGycgDUbR4lz/fXDj9A1O2gXPdPF3w30vxbYsXjW21BUIiukHI9mH8S+x/CvB9T0bUfCurf2fqyG2nT/AFcgOVkXsQe4/Wvq5elYPjDwfp3jDR2s76IMwBMcg+8h9Qf6VhUpqWx0Uqzg7PY8J0vxG1oAS2dvUrzVm88fIICo3Zrm9b8B694Q1U2lxueBz+4nXo49PqPQ0WuiXc0iJKCQx7iuJpRdmenGUpK6Ou+Gkk/if4jR3M64trCJ50jPO5/uqfqMk/hXue2vHP8AhEZtK+FPiTVY2kt7iaz22zIxVgqkOXBHTJXj6e9eb+Gfjb4u8PzoLm9OsWn8UN6dxx/syfeB/Me1d1GNoHl4iV5s+q9tG2uL8J/Fzwn4sSOOO/XT75xzaXhCNn0Vvut+B/Cuj8TeJNK8IaBPrOs3AgtIR25aRj0RB/Ex7fn0BNamBzvxU8dR/D/wPcaijqNSnzBYIVzmU/xEYxhRlueuAO9fEs88lzcSTzOZJZWLuzHJYk5JP411HxG8fX3xD8VSardJ5ECjyra2DlhDGOg57nqSMZNcnQAUUUUAWbW8e3IByyenpXT+HNefRNf0/WrNsyWM6zgeuDyp+oyPxrj6ckjRsGRipHcU7gfoxY3kOo6fb3ts4eC4jWWNh3VhkH8jVivkr4dftG33hLRLXRNY0lNRsbVRHFNC/lzIoB4IOQ3OPTAz1r3Xwf8AEU/EmG5/sGFtNS2iiaaW7QO4MikgIqnBxg8k/hSA6zxDp2napo8ttqbJHA3IkZguxuxBPevJb4+HPCcqXGv6vbtZtlokgJkmuBngKi84Pc9Kf8UfhdrPiG1/tD/hIWuGtEZ8XJIUlRk4RRtHTgjBFcbp/gHS/F+kXM8l3eW+pW1urecu0pINuclTzn15p/VlVd+xSxEqSaXU9bn8d+HvElm2gxmezur23YQQXUBj8xSpX5eo/DOeK+Rrm1msbqWzuYzHPbuYpFPVWU4IrvtH1nwx4H0i4TX7PUtR1aK/BgubSRY9ieWGX5mJOc9Rj8a4Hxr4zk8XeJrjV47CLTTcIgeOJt25lUAsSQOTjsB/Wj4XZk77FO4uY7YfMdxPRRVbUvEGq6ta29re6hc3Fra58iGSQskWeu0Hp0FZpOTk8k0UXAKKKKQH/9k=",
    26: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAoAK6bwr8P8AxF4vkzpliwtgcNdTfJCv/Aj1+i5PtXonw4+Ci3ltb614pVhBKC0Wncozgj5XdgcqOp2jk8ZwOK9zSJIoY4Y0WOKJQiIgwqKBgAAdAAKAPKNC+AmgWSpJrF5c6pLj5o4z5EWefT5j1HccjuDiu5tPBnhqwVxa+HtNiD43Zt1fOOn3s+p6VuuUjXc7BR6k4qWK3aVyoBBHY8HHr9KTaQ7Fc72+8xP1NR3FtFd2zW9zFHcQtjdHKgdTg5GQeOtbC6WMYMuXIyABximvpbgjYwYGp50OzOJ1L4d+EtWEv2rw/Z75cbpIVMLcdMFSMdO1ec+Iv2f0EDTeHNTdpByLa9wN3A4EgwM5z1AHI5717rJZSxZJXIHcVDtqk09hWPjLW/D+reHb42mrWE1nMOQJFwGHqp6Ee4rOr7R1bRNO17TX0/VbOO8tXydkg+6cEblPVWGTgivm74k/C668ETJeWjyXujy4VZ2Ubon/ALr44Gex6H60xHn9FFFABXuPwX+F8NxBH4p160ZlLBtPt5VGxwP+WzDuAeFBGD15GK88+GvgqTxx4xg08sY7OEfaLuQD7sSkZA92JCj656A19dJBHDGsUMSQxIAqRxqFVFHAAA6ACgCMgkkk5J5JpkzxwQvNKdqINzHrxVnbWbrOfLgiD7Qz7m9wP/r1MnZXKWo7SpUuHaeZ96s3yoy42r6Y9a3RcWqyKVYKU6DsR6V57fO8d6ojmZR1OOK0rC5d0G9i3YZrk9qk7HdDC8yvc6+S7i8wFOg3DjuD/gaBfrvYYyDg9Ky7dlOAWBPXFXvLQx8FcjmqU2zT2EVoy/DexyyYcDnpVTVrVUeOZANrjBx61nPcGOQc/lWpC6z6ZIGLEqcirp1E2c9ahyLmRmbKiu7G3v7Oa0u4EuLadCkkUgyrqexq5so2V0HIfKXxU+HTeBdZjkszLNpN7loJHXmNgeYmbuQMHPcH1zXA19p+KvCtl4w8N3Oj3wAWYZjlAG6KQfdYHBxzwfUEivjXUtPuNJ1S50+7jMVxayNFIh7MpwaBH0j+z94bGmeBJtYkUrcatMcfN/yxjOF47ZYufpjHWvVdtVNA0f8AsHw3pmkY5sbWOBgH3gMB82D3G4tj2rQ20AR7aw9akVLsFukcf8zXRBMkD1NeYjxNLrkWpmdEiaCdoVVeuAcDP5VhVlZG1KDk7gZvtNw5DZHY5rWsbdw4LsoBGQa4ibVJLW6EaEDPUk4xSHxfPpsihr+zuI252+aC6/UVwJXdz2FJRVj1ZbUsEYEZxUghfkL2Hc4ArlPDPixdWxDGxYqOuOB7Zqpr/jG50i6aBgiurZG9gFZexzWl0O3U6x0aNtzEN9DkVe0+6JtZY+5HI9q4bT/El7dIty89tKp58u3lV8D39K6jQ7gXd75obapXrniiGkjKtaVM3EGUU9eKdtqvpGpQaxp/2u2VhEZHRdy4J2tjNXdteindXPHlFxbTIttfNv7RHh82PjO01mNAItTgAcgD/Wx/Kc4HddpyeTz6V9L7aztb8M6L4mtIrbW9Mi1GGFzJGkhYBWIwT8pHamI1m+Zix6k5pNtSvHtdh6Gk20CGAc8V4j4k0x9H+JdxbxfLBcF7sfRx0/76zXuW2uB+JdpCkmnXwAE5Dw5xyV4PX6/zrnrq8b9jqws+Wdu5ytz4Rj1u384Fcj7yk8NVi28BW8UTMdMtI5JV8svjeSPSn6FqHlsIZWOM+vWun1LXodP01pyCfKUsB6+grihpsz1XFS3MDwZpFvout3EVuAEcgsBwqnp+FXtZ8KW+p6k9w0EUk+clZFzuXpgH6Vyei+Oba0v5lwZDN+8bOep6itc+PIbu7e6ihmX7GUDEKdm1iAST+VUaWTViS2+GelRtH9l0+S0ZW3F0mx9fcj2NdDd27aRYrHpy/PjaATng9a0o9VgvLFXRiNwrP09jPrFtFK5dGkx9fajeW5k0oR1WiOn0vT49N0u3tIxgRpz7k8k/mat7al20m2vSSsrHhuTk7sj205GKHIp22nxxByQSB9aZJheCdZ/4SPwLourGTzJLm0QysXDkyAbXyR3JBJ+tbuK8Q/Zq8Wx3ehXvhSeQ/aLNjd2wY9YmIDqPo3P/AAM17ligBgFcd8TNPM/hyK8RctaTAsfRG4P64rtcVHc2kV7aS2s674ZkKOvqCMGolHmi0XCXJJSPBFuUiKSKcOnFO1LV4fsay3UirGTtQMeCazGuLWPUriOK4ju7WKZohOnKyBSRn9Kt3VhDqDmZYQwXAXcucfQdhXmfC7M92L5ldFewsNFv705vLdCeQDIBXTvq+iR2Elj9ptWRl8uQI45B4rKs/D5uUCjSLCQDoZEXmtaPRkaPy7nS7WJQNp2IuCPwp3SRdkRaHcz2w/s+Z87DhH/vL2NdfpUZl8R2EcfKqWkb2UDr+ZriYIo9GaW2cmS3zmBiclR/dP07e1d98Pbizuvt+Zs6nEyrLCwwY4yAykA9VOc5q6UeaZz4mfJD1Ox20bal20m2vSPEI9tcv45+IWh/D2ytLjWkupReSMkcdqqM/wAoySQzLxzjI711m32r5M/aF8U/278SX06F91toqfZVAcMpkzukbjoc4X/gHPNAHC+DfE9z4P8AF+n65ajc9rKGZM48xDw6fipIr7FvPiT4QstJttSk1qEwXcSzQooLSspGR8g5B+uK+Hqv6bf/AGYtG+fKc9v4T60AfS2vftC6fBEU0LSJrmXoJLs+Wg99qkk/mK808RfF/wAW+INPns7nUEt7WXh47WIRbh/dLdce2ea4p2O0MvzD29KhkGRigD1TQ9IZvhjpGoW6fvEEhlA6spkbB/D+VFlrEto5LHcG9TXWfDOJp/hzpybc7VZceo3GsfxJ4Yazd7q0T91kl4/7vuPavNqr3melh6tlysltfEyRfMH2c5+8KtN4xEqbIR5rnpXIraxmHzCoIOMH1rs/BHgqXX7kSbfLskb95MO/+yPf+VZqLlojtdRRV5Ms+C/Dl74q1oXN/wD8eEDbpABw5/ue/v7Vk/FXUbjwz8X4tQ0qU2twbOF9y9MjK4I7ggAY9K990/TrbS7GO2tYhHFGMBRXzj8eyy/EuEjj/QYj/wCPNXo0qfIjxq1V1ZXO80H466NdRRx65aTafPjDywr5kRPrj7w/WvQ9J8QaNrsQk0vU7W8B7RyDcPqvUflXxy02eFGSf0prX32EfaTKYynRlOGz7H1raxgfVHxT8cx/D/wRcagjAalPmCxRlzmU/wARGMYUZbnrgDvXxPPPJczyTzOZJZGLuzHJYk5JNaOveJNU8R3McupX1xdCBfLhWaQv5aegzWVSGFFFFAFu1vngARvnj9PT6VqxyRzAGNgwNc/To5HicMjFSO4oA+uvhPaIfh7pZwATGT/48aPHttfXumsLDy47OM5nyuXnGeg9F/nXi/g743Xvh7QodFvrBbiziZQs0DeXKEByVOcg5OOeOM9a9rtPGemeOvBmo3em291bNBCjss6qMFgSACpOcbTzgVLj1BGD4Z0PR4Q9vqmixTxNgb9rBh/wEnA/DFdFb6jceDL2K50m3W58Nv8A68JwRk/fUf3h39elaOmWtzrngfzr2eNsAgMkW1/l685/CuqksLX7JBbJCqwCIAJjIA9KtpLRaPqSm3vqaVrd29/ZRXVrKs0Eyh0dejA18z/HeYy/FJ1/hitIkH6k/qa9A8T/ABZ0L4XatJpI0y9uFJDvFFsWNHZQ2VJJ4IIyMDkV87eO/iDeeNfE0urG0TTxJGsYjjcuQB/tEDnk9hSQyvd30VmPmbL9kHX/AOtWBd3kt3JukbgdFHQVASWJJOSe5pKBhRRRQB//2Q==",
    27: "data:image/jpeg;base64,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",
    28: "data:image/jpeg;base64,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",
    29: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toopURnYKoJYnAA6mgBK6zwh8N/EPjL97YWyw2QYq93OdsYIxkDux56AGvSvh38EPJZNU8XQfOCrwWAcY7HMuPy2fXPpXtCxqiKiIqIowqooVVHoAOAPYUAeX6J8CPDWnbZNSmudWlAGVJ8mLOB/CvzHnPU9DyK7vTvDmjaOVOm6RY2bISVaKBQy54OG+9z061qttRSW4Aqi9/l9sa5/rQMs7c89aUAqcgkVUa92DLsqY65NQrr1qHCyOACcBscUAU9S8EeGdXtfs95oNgyDODFCImXOM4ZMHsK878Q/s/2U0Ukvh7UpLebqsF58yH2DgZHtkHp1r2KGWKdN0Tqw9Qal20AfG3iHwprfhW8FvrGny2rNnYxGUkx3Vhw34HvWRX2pqmj6frenSWGp2cV5ayDDRyD9Qeqn3BBr53+JXwju/CfnavpZN1ohk6cmS2B6B/VcnAb25xkZBHmdFFFAAOte8fA34c7Eh8Y6mnzHcLCB4xj0845/HbjuM+mfNvhl4M/4Tfxrb6dN5i2MSme7dDgrGOwPqSQB9a+uoreKCFIYYkhijUIkaLtVFAwAB2AoAZtpCoAyelT7Ko6xdJYaa8rHkkKo7kntQMzr5ri5n8i2ILdT7D3qrBY7ZW812lYn7qjAqexkC2iFm+eQbjzjPp+FWkv7ONQqzR7xwQrVHNrY1jDS7HjRHuIEcMsWR0xmqsnhtYlIdlfJ5zUv9vWkOSLpYnHBVm61Sm8VxzMVWePaB2YZNNyVhqnK5mXFpfaFcfbbEGSBT+9iz/D6j6V09lfxXgRfuyMm8DsR7VjxakLgZOBn3BBqolyNPaOTb8sMpGPVTzx9KKb5tCKkeU7DbTXhSWJ45Y0kjkUo6OoZWU8EEdwamiKyxJIhBVhkEd6dtqiD5W+LXw7fwXrYvLMbtI1B3aDCn9w3UxMfbPynPIHsa88r7Z8S+H7fxR4Zv9FuTtjvIigb+445RvwYA/nXxfqWn3Glanc2F3GYri2kaKRD2ZTg0CPpH9nzw0NN8Dz61KhE+rSkLz/yxjOBx7tuP0Ar1jbVHwzpP9i+EtI0wxtE1paRRMjPvKttywz3+YmtTZQMh21x3jqSQ3ul2ucRtvfA7twP0Gfzrt9tcB4588+KdPWPn9ztUehZjk/oKT2Gld2IUX7SVjlcIp+Uc4GKsLomm2kTvZvGsjn5i7HHvXJeI/Gz6UhsbCNXKko7FM59ea41vFl1LJulWSP396wStqdy102PSJ4rR7giRYpCDjLAYrTt7jRrSDyx5PmHqqKoNeewam91pzOqZBIOTz+tcpe6jcXNw4WRhhvXvSUi5Q01Pbvs3nfv7eSN8jOFxj6Vi6tqj2xEeNofgg9iOhrzjT9Q1rRzHMs7iMtn1Gfc9q7tJYvE+kvcKQlwi7iD/eHUU1Lld0YTg5KzPSfC0rT+HLYsMMmUIznGDWvtrnPAcgl0ZxnkEEj0OMf0FdTtrpZxoh2cV85/tF+GhY+JrHX4YtsWpRGOdgDzMnGSemSpX3+UmvpLZVa90bTtYhWLUdMtNRSNtyJcwJKqkjBIDA4NIZfIycmk21MVGeDkUbaBEOzJwO9cF4h1HTdR1SK8srtJ3t0aNwONhBI79+teh7ea8S1+B9B8aarBcKW+2SGSIqMBgx3g/oRWc3Y6KMFO990cZqMV6Lm4lQRsI2Yhn+ZQSeuO5H5ViR29xcMVmuPMlJ52pgY9+len3RstTC2kUUoumGB5a5yPU+gqmNBs9JvbW2Msct9dSBE3gBIh3OPYZrBPod3Km7nR+EPC0Ft8P5PORpJpFOM9ga8r1TQBpl5IJEcjccENgH/Cvc4vFGl2elrbC7iVlXbuyADiuC13U7SK7t7m5uYr+zuWKSRBB+67g5qpdLGcE23dHnunaKzyOqiVUkzkls/QV6BommXGg2gFxgbxuPJyPw6VoQ6PY28K3mjeSHIyolG4fQelYV3ql9K0scylSCR04BqG3e7LUElZGzYaxqFh41srK1kZbKa6hEixn7+RyD9M17IUwcV438PdDlu/H5uLhj5UTm5VG6nC/K30yRXtJXmuiF3dnHXsuWK6Ih20oyvSpdtOji8wkZAx61ocxz3w81WDXPhxoN9b/cNnHCRnOGjHlsM/Va6TbXg/7MXinz9P1PwrM67oD9utwWO4qcLIB7A7T/wI+pr3zbQBHtrj/iJocV/pEeoBV8+xYkMeCUI5H4Hn867TbWfrehW/iDTTYXUk0cTOrloX2twen0qZK6sXCXLJM8gs7iOysGuxjzGXaMVzkNudV1Se9vGIiVSilj3NS38k1ndy2cmf3UjRkfQkf0rPayl1y+NlHPJDZwpvl8s4Jz2Fcq3PVvpoYuo20Ucoih1RVhA+bfJuK/jWx4ft9CSxu4prtZmlTbguTt98HtVefRdOt5PLt9GEpXq0r5Zvc06HQtL1CMgWgsLhOd6ttFW5IHHqaGjXsthMbUybo0baDnjHatXVriF1HzD5cc/WuTg/0OKS3kfzJI3xvHcdjWtoEEus+ItN08nIuLlFb/dB5/TNZbuwSfu3Z638OrNlS6updLuLGUKsBaeMoXxzxnqO/wCNdvtqUrk8dO1JtrtSsrHkzlzO5HtrlfHXxD0T4eWVnPrMd1L9skZI47VUZ/lAJJDMvHOM+tddtPpXyP8AtA+Ll8R/EZ7C3djaaKpswMnBlzmVsdvm+X/gApknD+DPE9z4O8X6frtqNz2koZkzjzEPDpn3UkV9yaBren+JtCtdX0udZ7S6QOhDAlT3U46MDwR6ivz/AK9W+CPxWbwNrQ0vVbgjw9euTL8m77PIRgSDHOOAG68c4yKAPrvbRtrjdZ+Knh7SmCQzG9ZgGQw8q4PQg9wfWuR1f4wam0RFlaw2pYfKW+dh712QwVaeqVvUxlXhHqZfxJ0tdO8T3rBfllPnqB/tdf1zXF6Tf24vWjlOM/MG6E+1bSSXmo6G2r39w8z3N7LArOc5Kopxn8Tx7ViTRRBm4XnvivNq0vZzcGevRqc9NSRrX2s2MUYS2ABH3iT9761XfxFp7W4zbDzRwGFc3PGVckNx6darGMk88ip9mjR1HtYnvNQkub5mRAE6Cuo8I3badey6wmd2lQG6GP4ipAI+hBauYjhyMkYA711ej2zR/DXxVq0i7Y2hFtDnvkjJ/En9KujFSmkuhz158sHfqfRGj6vY69pkWoadMJreUZB7r7H0Iq7tr5Z8EeN9T8J3oks38yBiBLA5+Vx/Q+9ezQ/GvwomkT3uoSzWTQJuaIpuZ27KuOpPavRq4ScFzR1R5cK0ZaPct/FfxxF4C8CXV8sm3UbkG3sV5yZSPvfRRlvqAO9fE080lxM800jSyyMWd3JLMT1JJ6mun+Inju++IHiy41a63xW/3LW2L7lgj7KPc9Se5P0rla4zcKM0UUAdD4Z8US6HcgTRi4tmwCGyWjHcr+HbpXdxaja6kpubS4W4Tn2YfVeoNeR1Lb3M1rMJoJXikXoyHBrvw+NnRXK9Uc9ShGeq3Ppy30c6l+z0/lqfPiuJ7lCOu5Xz+fFed204vbUO2ScZyP6isfwr8Y9e0F7Wzu5jc6OhKzWqooDozEucY++cnnI/LirXh2ZNRE09lujgQhtkoG4KzkKOOv6Vx4uam+aPmdmFvH3WWJFQNjJ5piqu6tG4ieKU5Kkj2zTrG2lnZnBTIUsARXDzHoqJUFtJc3MFnGCHnbaBjkDufwFeleO9Mj8P/BSOxUBDcXEKkevzZx+Qrzyy8VaV4M1K8v8AU7O51G8hkEMcUZVY+hblyc4yAD8vT9cTxz8a/EHjWKG1NtZ6ZZQOXjit03NnBAJZs5IB7Ac89a7qDjTV31PMxDc5WXQpTalBo8bG5J83AZIOjtnkduARzk9uma5TVdYutVuS8rlY9xKRA/Knbj3wBzVKWV5nLyOzuerMck0ytquInUXL0MIUoxd+oUUUVzGp/9k=",
    30: "data:image/jpeg;base64,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",
    31: "data:image/jpeg;base64,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",
    32: "data:image/jpeg;base64,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",
    33: "data:image/jpeg;base64,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",
    34: "data:image/jpeg;base64,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",
    35: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toopVUsQACSeABQAmK6Xwn4B1/xlcBdMtNtuCQ93PlIEwM8tg5PsATyK9L+G/wAE9yrqvi+1lj2srQac3yluh3S9wp6beCe+Oh9shgjt7aK3hjSKGFQkcaDCooGAAOwoA8m0D4B6LZpHLrd7cajMAC8UJ8mLPORn7xHT+70rvrHwf4c02HyrPQdOiXIbm3VzkDGctk5qXxL4m03wtp32rUJfmfiKFeZJW9FH9egrxfxF8QdW1yV2uZ306xX7ttb9fbe3c+1K4z3STU7RpjHJfwGUnlWmXdn6ZpZjb3MD285imhkGHikwysM5wVPB5H6V8uPdTTMZvKllB6ZG0H3wBVm28Ya3YRG3huZYo852A8g9+TRcdj3zVvh54T1xCLvQrQMQAJLdfJYAZxgpgd/TnvXnfiP9n5CiyeGtSIYD5ob9uvuHVf0I/Gsrwz8U9WsplimY3KA/cbgsPTPTNe3eH9esfEmmC8sZMqDtdD95G9CKLiPkfXfD+qeG9Uk0/VbOS1uIyeGGVYeqsOGHuOKza+z9b0DTfEelvp+rWiXdu2SA3VGwRuU/wsM9a+dPiL8JtQ8HPNqNjvvND3ACYkeZDnorge/G7GDkdCcUxHndFFFAAOte5fBD4a7/ALP4x1VXXy5C1hAy4Dkf8tjnqoOQo7kE9hnzr4a+DT438a22mSGRLNFM93JHgFIl64J7kkKPc19eQ20NtbxwW8McEMShI4o12qijgADsBQBHtyc+tZXiPX7Lwxos2o3rfKgwiD70jHoo9zW5sr51+NHiV9U8VnS43P2bTvkwDwzkcn+lAzGv9dl1/UrrW9WuAZm4ijU5Ea9lX0ArM1RG2QTxbJJN2FhQ7iCeenesN52aEA8DGABxxn/H+Ven/BfSjPf3eqXEe4f6tHYZ56nH6VnOfJG5pTh7SXKZukeBvEOtJGL6Wa1ib5tirgj61v23wx+xnzGLyMOQSOv1r2mC3hVAcfkBS3VvEYGx6Eg1xyqTetzvjSpx0sfL9/o0miazOtzCQjE4HTNavgnxX/wjHiSG4jcCxugI7lCe3ZvqK7jx7pCarpkojX98i5X3IrwyNpInaPBVl6g9iDXRRnzx8zkxFL2ctNmfY9vLHcwJNEwdHGQR3p0kEc0TwzRJNDIpSSN13K6ngqR3Brzz4R+Jxf6MunzuNylvLH90jG5P1DD2PtXpmyug5z5O+KPw8l8Da6Gt/Mn0q7y9vMV+4c8xsem4fqCD6gcJX2p4r8MWni7wxeaNdquJ1zE7Z/dSgHY/HoT+RPWvjO/sbjTdRuLK6jMVxbSNFIh6qynBH5igR9Jfs9eH/wCz/AVxq8iAS6rcEKeM+VH8o9+WLcH0B716xtqroGk/2J4Z0vSvLERsrSKFkD7wrBRvAPcbt1aGygZSvZ1s7Ge4kIVYkLknsAM18b6vetqes3d2clriZmH4nivqP4raidL+G+qyKwDyxiFeefmOD+lfMGm2puLtcD93EA0hPQUgH/2Y1xqdvYoArzAZLcBR6+wABNe6eENU8K6ZZw6fa6ta5hATG7GT3OT1ryLTRar4gu767UPa2xVAG6Hj07/SuwXxR4Z1Vkgl8LNK5G5ZVGxsYPII+neuaqud2Oyi+SPNdXZ7fDcWkiApIJFxnIOQapahq2l2Nq0l5exWyEcbzjP4VyvhAJFdR21q8jWTxNJCJfvLk4Kn6GsbxNFAl81/d6XJqJVvKijOTGuOpPp+Ncy1fKdjVo8yZen17w/qdyYbXVIZHfhVOVyfQE14x4ntfsfimYFNiE56cYbjNegt4tk1OBbSTwd5Fv8AczDFnHuRjpXN+PtNWC2splDZKeXznJHUZramuSdu5z1n7SnfsZXg/X5vCfiKGc5EDld4Y8KezfTqPoTX1Vp91DqOnQXduweKZAykHNfIUyx3FrZySlgoG1z3xXt/wb1u8XQIrK4BMcIXcpPOxz8kq/qrL7A12Hnnq+yvnD9onw0NP8VWWvQQ7YdUiKzMAcecnBJ4wMqV75OCa+ldlY/iPwfofjCyhtddsDew28hkjTzHTaxGCcqRnimBvMCzFj1JpNtTvHtcj0NNK4FAjxb9oHVGTQLPTowdsk2929cZwP614Rb3bW9tJCucyMCx9ga9Y+P94W8Q2tnGu4QxCaTH8JYnaPqcE147HnzBuGdxH86Qz1j4f2lveXV/DIQxM+8sRnnaK9Ht/DyW7DCQMh6FYlFeX/Du8W21KRXQK0uJOfqa9jF8Gtwikb2GM+lebV0qM9igk6SZn6WGl16adSCEHl8dqmS2Sa/lgkJVnORg4Nctpeua14c1mY3lmXtz92aFTJz7jFbumrq+oao+oXkcVvbP8yREHzDnoT2HrioSe5u2tjUfRgqu8sjMicgA15R8UpR/Z8RVQWD4H4V6rPqbC3eGU4dOCfUdjXjfxMn320AyBmQ4/Krp61EYVlakzz+G4L27Rlu2FH1P/wBevdfglZrcS6jcSHL2RS3iT0UZO4+pycD6V4NBbsJosAjfzj8a+mfg9o0tlof26Z0zfxh1VTk7V43H3JJr0lueP0PRttOQlCSO9SbadHEHJBIH1piMTwPrKeI/Aei6qkrTGe0QSO7hmMija+4j+LcCT9ea3SteHfsyeKDeaHqXheZ8yWTfbLcM+T5bkB1Az0DYPAxlznrXs+qX0lnEkdtEJ7ybIhjJwOOrMeyjjP5UAfP3x6tBY68JFlR11NI2kQ8sjR5Ax7ENXki2pZ4UT733SDxhia9A+MFtNH8QBbzXTXNxDAnnSn+KRsscDso4AFcpBgzs6hU29Se1Io6LwrLEdbe2dwWSNdpHU4PNenTm8s7QT28JuQyYPzAEH8a8FhvJrLXrS9h+6CAF/wBn0P1HNe5aFq8N7YxjzMo68e1cGIVpXPTwkrw5exPpfiLVrhi0OkxjAw3mXADfoKsT6vrjzmEWtmpbg4lb5f0qxa+HRdr5ke1t/J+bFaJ0RLC33FlB9B2rLm02Ou8TGuIJ1t2e5kVnPA28V5H8QrpbjU2tYyD9kiDN7Mx/wFen+JNattM0+e5kfMcC59yewrw+GSfVItZvZSTJIA7c98nj6cVrh468xx4udoqAqrG1gny7ZYsOp9iOle7/AAQ1w32nx2jr80SGIE99vP8Ah+VeBCfdZwAYOFKN7Yr0D4M+I10rxbHBP8tvdOFDDoHPA/MV39Tzeh9Oba5Xx98QtK+HemWd3qtrdXSXcrRItsU3AgZydxHHPauvC56V8kftCeKF174lyWNvOJLXR4/sgCsSvmZzIeuM7vlOP7o9KZJw/gzxVfeC/Fllrlgf3lu/zoekkZ4dDweoyM9uvavr3XfHOm2fgJvF+nMLlb6MLYKww0jcgLjrwdxb6GviWuq8L+NJ9D0+802eL7TbXETJDvYn7I7YDSIOmSBg/ge3ICEvdWu9Q1Ce+vJ2nvJ2Lyysckk02O4H2Ccn+IE59OKv2XgnXtRthdQWMrwEb1bGFZfUE9RXQeH/AAb9pkK38bkA/wCpUfMx9D6CspTUFdmsIObsjFuNElj1F0Cjyk8sAryGJUHIP1/rXUaVJPpqq5DeUT1HSuku9AEFvscNKWGTIRjB7AfTFS6TpoubN4ZRkhsZ7HjI/nXDUq856NGlyGroviuG2g2OzYPRhzT9R8VR3cOyFnYHrxiuau/Dd7ZTl7dWMeeQKv6Zo0zKzTA/SsWzpRxvju4mk0OV2z5fmIv5n/61c74VR30jX8YINtjrwT8x/pXqfiDRY5NHSBlDMzBmyK4g+Hru2mvLTS5GtTeIA6ADbkZzj6gnj3rqpVFy2Zw16bc+ZHG2cZlJUAEYyc13fgnRpZ/DPiW5g4lsI4po3/usjbx+WK5WXQNT01vLkTyyOM9M16fpdvH4W8HX8f2ho9F1aJGe/nUDyiOJUIHJY/wqOTXZFp7HFKLjuemfEH4jx+C/hpBrGAdUv4VSzhPeUqCzH2UEn3OB3r4wlleaZ5ZGLu5LMxOSSepNdL478bXvjfXxe3KrFb28Yt7S3TpDECcDPUnnJJ6k+mBXMVZmFFFFAHpfwx+L154JePTdShOo6Ez5MROZIM9THk468lTwe2Cc19K6JdeGPHmlDU9CuY7uPG19nyTRH0ZTyPx4PbNfD9XtI1rU9A1GO/0q+uLG6jOVlgcq30OOo9jxUuKe41JrVH2JqPhi6hRmj/0uD1C4YfUf4Vz9raNYh1lhZoyc7l5x9a4Lwz+05rFmscPiPSoNSVQAbq3byZj15I5Vj07L0717L4X8UeH/AIjrcNYWt5azQIju8qIv3wcfdY7uncCuSeG6xO2niukzPt1ili3IwkU8GqcaCK+MEnyg8qfWtTW9Bk0qfzVmUbujJkZ+o6Vz11esvE6gsPuslcslZ2Z2xfMron1CyWW4kEgwu3C1mPppk2EABlz82KxvEfxT0/w88tlcWV1cTxMFYptCnIyMEn+leZa/8Xde1aJrexWPSbc8fuCTKRjoXPPr0Aq4UpT2M51oQ3PQ/FHiHQ/D1q6anILi6A+S2jIMh4PX+6Pc/ka8d8WeMdS8W3yTXWy3t4lCQ2sGRFEAMcAk8nqSf8KwZHaSRndizMckk5Jptd9OmqaPOq1XUYUUUVqYn//Z",
    36: "data:image/jpeg;base64,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",
    37: "data:image/jpeg;base64,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",
    38: "data:image/jpeg;base64,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",
    39: "data:image/jpeg;base64,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",
    40: "data:image/jpeg;base64,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",
    41: "data:image/jpeg;base64,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",
    42: "data:image/jpeg;base64,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",
    43: "data:image/jpeg;base64,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",
    44: "data:image/jpeg;base64,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",
    45: "data:image/jpeg;base64,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",
    46: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV03hX4f+IvF8mdMsWFsDhrqb5IV/4Eev0GT7V6L8N/got7bW+teKVYQSgtFp3KO4IG13YHKjqdo5PGcA4r2LWtWsfDOgPe3W2G1tUCRxIAB0wqIvTsABQB5zoXwE0CyCPrF5c6pKB80cf7iLPOenzEcjuOR3BrYnufhp4ankt/sujRStgOiW4mII6ZyGweTXlviT4l654imkjN1JZWjnAtrdtoI9Gbqa5hJsOoK4cnjPb3qbjPoJfix4Wml2Ne3IX++1u22rS+OfCOrRm0m1O1lifGY7qM7G54yGGOuOtfOsjvGrKsijI5PqfT2qBZbh2WNSR2xu6/nRcZ9IXfgPwX4ghklbRdPmEuAZrX92eOmChAHTtXn3iP8AZ+TyHm8Oam7SDkW17gbuB0kGBnOeoA5HPeuL8OeKb7wrrAu7ByCOJrZ2wko7ggd/evoLwd4wsPGelNd2iSQSwsFmgkxujJ6cjqD2PtTTFY+U9b8Pat4dvjZ6tYTWcw5AkXAYeqnoR7is2vtLV9F07X9MfT9Vs47y1fnY4+6cEblPVWGTgivm34lfC278ETJeWjyXujykKs7Lhon/ALr44Hseh+tMR5/RRRQADrXuXwW+F0Nxbx+KtetGZSwbT7eVRskA/wCWzDuARhQRg9eQBXnfw08FSeOfGUGnkmOzhHn3cgH3YlIyB7sSFH1z0Br68SCOGNYoYkhijAVI0UKqKOAAB0AFAEZUkknJJ7nvXzn8XPFFxqviu5sUn3WOnv5UaKflLAfMx988fQV9JqnzD6ivkLxPbSHxTqkGC0i3kq+5+c0mMx1aR2A3c447ACpTHltsCb2PHWuu8L/D2/1ktNOhihHc/wAX0rsD8P7izkT7FbQwkrgyCESt+R6GsJVop2OqGGnJXPKFkjC/6REEkVcZxiqxtPMPmbsegHU19C6X8KLG+hAv4SzEZLvw30A/qay9Z+Fb2kkxtYQ8Yzs2gNx2z70e1Vrj+rO9rnhLiQSc5JB4z1rp/AXie48MeLrS4SVhbTyLFcRryGQnuPbrXVv8Mri2haW4iRmyCAOTXJXmkyaPrdrJImGEisB7hhxTjVjJ2IqUJQV2fVRTn1qK7sba/sprO7gjuLadCkkUgyrqeoNXNuefXmjZW5znyj8Vfhy3gXWY5LMyzaRe5aCR15jYdYmPcgYIPcH1zXA19p+K/Ctl4w8N3OjXw2rMMxygDdFIPusDg454PqCRXxtqWn3Glapc6fdxmO4tZWikQ9mU4NAj6S/Z98NjTPAc2syIVuNXmOPm/wCWMZwvHbLFz9AMda9W21U0DR/7B8NaZpGMGxtY4GG8uAwHzYPcbi2PbFaG2gZFt5r5a16xd/ivq9vgDN/J16Y3ZzX0f4w1mXw74Zn1KKMSNE6KRjOATgnHfFeJ+J/s9543svENjtaHVYyZCh4MoGG47ZAHHrmsak0tDoo0nL3+lzv9Hl2WqoMEKAvpW7bzxFdxkQe+4V5tqF9LFppQJMI85JTOWHoKw9kuo63Z6N/Y80NxdhWjkmunIwc8sAMcY5rghDmPUqVVE+gLaWF4lkS4Rx35yKW88kRbi6nPpxXmPg641PTNYWwvrZI4GGBsYnpU/jr+1dS1RdP01YxCwwWdyMZOKu62Js17x0d5LajeGljDdMFxmvMPHWktdTW80I+ZZUQjvhmAB/Osmy0+/h1HUrP+zBcSWWTJI7yLuAbHynOOeo9q6PTmnH2WS9T9xHMkg3tjCqwYgn2xRy8kk7kOftINWPbxHsAX+6MUu2s7wzq7eINCj1E7SJZHClV2hgGwDitfbXop3VzyZRcW0+hDtr5t/aJ8PGx8Z2msxIBFqkADkAf62P5TnA7rtOScnn0r6Y21m634Y0XxNaRW2t6ZFqMMLmSNJCwCsRgn5SO1MRsMCzFj3OaTbU7x7XI9DTdtAjH8SWMd/wCG76CRA6mItg+3NeG6/oM2jyIUMYtEkDxhD1JBBI/Kvolo1dCrAMrAgg9weorw7xxpk2kiSwnbcLaUNbuzEs8LdB746e2K5a62Z34Wa5ZQfqbegtb3mnQl0Rio/iGea3rCzgWXfFGA2MY7AV534cuprdShPCnmvQtKud8QDY6c1xpWZ6XxRMe+mzripGP3iv6YzU2sxvYalbySouXAzg5rnvGtrrh1hZtIXhSjKxIIOOq9etUvJ8VT6na3d0I1iHyC3GM9QSxOf0p8t1cpzSfKd1cQrMyvKBgjOAOKwNXsI7+eOwQovnE5z0x1OfwFbt5Ofsu5McVgaVZz6z4ytLQjMXLSnnhB1/w/GiK5pEVGoxuz1DRtPj03RLO0iQIkUSjA9cZNXdtTbfbFG2vUSsjwG23dkO2nIShJHepNtOjiDk5IH1NMRieB9Z/4SPwHourNIZJLm0QyMXDkyAbXyR3yCT9a3tteHfsz+Lku9CvfCdxIftFm5u7YMc5iYgOo9MNz/wADNe67aAI9tZHirT01DwrqcRijeQ2kojZlBKnaeh7dK29tI0QkRkYAqwKnPTBGKQ0fOHh25S6hXBAcxkfXjiuqh1OaGy3xqwBTIKqWOfoK8yimm8Pax5cyssQkYKfYEgj8K7/w3qxEDWu4Hbnaw7qeleXNW1PchLmViK38STFlki0y/vHU/eaFsZHtTr7xJe3UYT/hHb2ONOSzIQQe+DxW4mjyXBD2l69qx54Gefxol8N3kQzf6rPcY5IOAD+lCkrG1orSxi2N1eyWZlkguIoZCcCYDpjrXQfDaNrnxTc3I+7FZ4b6swx/I1g+ItQFlpptk2orfL17V6L8NdISx8JQ324PNqQFwzDsuMIv4D9TWtCPNLmOLFTUYcvc6rbRtqTbRtr0DySPbXJeP/iLpHw6sLO41SC4uftkjJHHbFN42jJbDEcc4z612O0+lfJP7Q3in+3fiS+nRPm20VPsigOGUyZ3SNx0OcL/AMA55oQ07HC+DPE9z4O8YadrlqNz2koZkzjzEPDr+KkivurStTstc0i11TTpvPsruMSwyYIyp9Qeh7EV+fNeufBD4uL4H1F9H1uWVtCvGBDAlhaSf3wv90/xAemR3yCPrGeWG1t5J7iVIYYlLPI52qoHUk186/Erx3eeNr/+zNIlkt9LVtkXzFftDZxvb2x0H49TVr4hfEObxfeyafYOY9ChbK463RHR2/2fQfiea4JCVcjkMhyDUspeZ2sXhqPUPDMdrKMvENofuGHGf0rk3fVPC2oCOTIC/cbsRXq3hdkv9LScAHzfnP8AvfxD881Nr/hu21e0MMsYJwSp7ivMjdNpntys0nE4a2+IhjVT5LFh1CnINOuviRNLCUEMvrksOaw7vwXf2d0yICyg8Grmm+FHW5jkvVJgU5YdeKu0UReZn3Mupa4TdzqUikO1F9vb/GvpjwX5LeB9GEEiSxraRpuRgRkDBH1ByDXhN9NFLqDfZ122ttFhBUPww8e3PgjXpbDU3ZtLun3zKMny93SZR/MDqPcV0UXrY4sTF2PpfbRtpLW5t760jurWaOe3lUMkkbblYH0NZ/ibxLpXhDQLjWdYuBBaQDty8jdkQd2Pp+JwATXUcRzvxU8dR/D/AMD3Goo6jUp8wWCFc5lP8RGMYUZbnrgDvXxLPPJc3Ek8zmSWVi7sxyWJOST+NdR8RvH198Q/Fcuq3SeRAg8q2tg5YQxjoOe56kjGTXJ0AFFFFAG1oniOfSiIpAZrX+5nBX3B/pXY293bXkiXFpKssbnDY6g+47V5pUtvczWsyywSNE69CpxSsO59B+ANbXT9Q/s+4fEVy37on7qyen0PH416jMnyg4r5OsfG1zHhbyFZwCPnQ7GH9P5V9G/DfxhF438NtI0csd1aBUmZwMPnOCMHrgc9K5K1O3vI7sPVv7rNC6hQksVB9eKybx41hZMAZ4rp7mzGx8Njj0rno7UXMhViMhiCcVys9BM428tcvJ5ak+cwjX+ZrB8QWsMem2k7RL51vO0BfHO1uQPpn+db/jTxppHhXV4LaazuriS3P7wJtVTuTIwSff0FeW+JfiNe6/byW0NjBp9vIQW2Eu7YxgFjx1BPAB5relCTaaOTEVIWae50um/EHUPAFz5mn3zxseTa/eR/95Txj36+lcn48+I2v/ELUo7nWJ0EUGRBbQgrFECcnAzyemSeTgVyrOXYsxLMepPJNJXeeWFFFFAH/9k=",
    47: "data:image/jpeg;base64,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",
    48: "data:image/jpeg;base64,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",
    49: "data:image/jpeg;base64,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",
    50: "data:image/jpeg;base64,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",
    51: "data:image/jpeg;base64,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",
    52: "data:image/jpeg;base64,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",
    53: "data:image/jpeg;base64,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",
    54: "data:image/jpeg;base64,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",
    55: "data:image/jpeg;base64,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",
    56: "data:image/jpeg;base64,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",
    57: "data:image/jpeg;base64,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",
    58: "data:image/jpeg;base64,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",
    59: "data:image/jpeg;base64,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",
    60: "data:image/jpeg;base64,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",
    61: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV0nhbwF4h8Xy/wDErsWNuDhrmX5IU/4Eev0GT7V6D8Nvgs+oJDrHimIpZSJvhscsskmejPjBVe4HU+w6+7W9rDa20dtbQRwQRjCRRIFVR7AcCgDynQvgHoVmscms3tzqUoHzRxfuYs89x8xHI7jke9dvp3gbwvpUPlWmgWCgqFJkhErNjoSXzzUWs+NbSwuWtLKL7bcrw2GwiH3Pf6CsK78a30EW6edImPOyNBx+NYyrRi7GsabZ3+zAwBgDio7i0gu4GguYIriJsExyoHU49QeK8w/4T67mkAiuWJzxkcH9K63Q/FzXUP8Ap0BRVHMqDj8qFVTdnoN0miTVfh74U1pMXmhWgbAUPAvksADngpj1rzfxH+z8BC03hzU2dxyLa9wN3A6SDAz16gDkc969XbxTpCuqtcFQ38RQgVrxPHPEskTrIjchlOQa0Uk9mZuLW58Z614f1Xw7fGz1awms5hyFkXAYeoPQj3FZ1faOs6FpviHTH0/VrSO7tm52v1U4I3Keqnk8ivmz4kfC688ETLd2zve6RKdqzlcNE391wOAfQ9D9aok4GiiigAHWva/gn8NIdRRfFOtWyy2yt/oETEFZGUkM7L6AjAB6kHjAFedfD3wm/jPxrZaSNwtyfNuXX+CJeWPtnoPcivsK3tYbS1htreIRQQIscaDoqgYA/IUANK5OTyTXCePvFw01G0mylK3LD9/Kv/LJT/CD/eP6Cur8S61F4e0G4v5MF1GIlP8AE/Yf1r5xvNRkvr2SeeQyOzF3Yn7zHkmspvojSC6m1BqkdtGXAx6A/wBTU+j6bc+ML3yonMcSn52x2/z0FcZdXTysI1yWY/dH6Cvdvh3of9i6BEssYNzJ88n49vwrHkS1OiLuaGh+BdN0yFAtuJHxy8g3MaXxXosg0tvsqlHAJAXiuwjwEXgdKjvY1uISrDI9qco6FKWp4fp14LqNo5yQwOCD2NdBousTaJLkSM1qT88ecge49v5Vy3jCzm8OeKXYgi1uuhHQGjT9T86NlJG5eMdjWNmtUOWuh7jbzRXVtHPCweOQblIpLuxttQsprO8gS4tp0KSxSDKup7GuM+H2sA3D6Wz7opAZbfJ6Y+8td/trthLmVzjlHldj5Q+Knw6bwLrUb2hkm0m9y1vIw5jI6xse5HBz3BHfNcFX2l4t8K2fjDw1daPeAKJhmKXAzFIPusDg454PqCRXxtqNhcaVqdzYXcZiuLaRopEPZlODVkH0V+zt4dFn4QvNdljAm1Gbyomxz5UfXBz3cnsD8voa9f21meEdKGj+CtF04RNEbeziDI4+ZWK7mB9wxIrZ2UAeP/G/UWhtLCzRsFmZiO/AH9T+leNF9lquemNze/oK9R+PJCa/poKkqLYsffLH/CvIrqYMiqn3ccD1+tZ2uzVOyOs8CaXBPqI1fUpYora3fKGVgAz/AP1q9w0TX9HvHKWuoQzsnVVbn8q8R0ua20vR4WuYHuHfCoifeyecAnp7mtLTRJq0El/baXPAYCYy32li6HBOcY6cc4zScb6msZJaHuw1BDaiVW+RJACR27f4Vjah4806C6e1hjnupYztkMafKp9M/wCFQ+GSLnwbsmwzH5XB556GuL19vE+nzv8A2fPbQpGw8uJYwGYHOSzHuOPrUr3tC5WWps+L5LPxZ4ZniWF4byMGWJX6nHXB715JpN4S3JwfuP8A0Neq+G9Q1DVIHi1m0VbiJ9sc4jKebxyMH615Lq1hN4e8S3NpICE3cA91PQ1PLuhN6JnTeH9YfT9Ut50bDRS7hn1HUfiK+hoXS4gjmjIZJFDKR3Br5XedknWZG/1nJ/3h3/EV9B/DXV11fwdAC26S2JibnoO36VVPR+plU11Oo2182ftE+HzYeNLXWI4wItUgG8gD/Wp8rZwO67Tk8nn0r6Z21keIvCWi+LbKG11qwF7FBIZI0Lsu1iME/KR2rcxN0rk0m2pioPI6HpRtoEeK/tBaf/oOk6ljhS9u30OGH9a8KtoTNdwxscIZFQfnX0Z8e087wbYQrjeb0NnPQBCDx+Ir56Rl+2IsYyICCMd8Hk1OzLWqPZbTwpZXfk70V41XDI3Y+oroX0ez0jRZhaRCKFVLPg5JHeuc0e9VGWZmY7wCOeK2dduri50kpbME/i+p7Vg5PY7FBWudB4VSI6IyrwXG9vYnmtaG1gvctlRMnDAgHj6V5H4ds/FE2+EyOkcjbROePLz3A6HFd5ZaXqWm6XHJJqrX1/A3yysoUun9w4wDT22CyZ0zQwQyBti5HTArxn4yafGZ7e7QBZACMgdR716xHqa3ECSDqRyO4NcN4500arPDGzDacryf9nNTfW4OOljxi2uNwEcnAPf0r1n4HahLHrt3YEkxzQs2OwZSMH8ia8rmsxHfSwDjZnAH16V638B7ETapqV62cwRhAPdj/wDWrXdqxzy0Tue0baehKEkd6ftp8cQdiCQMetamBzXw31VNd+Gfh++TbzZpCwUkhWjHlkc9/lrp9teEfsxeKI5tM1PwtNKPOgf7bbqepQ4WQDnsQpx7k969720AeffFuCCLwJfzLBF9ocKgk2DcAWGcHt0r5eiBtZmugoZImCkZ+9uzwPwBP4V9a/EvSZtW8FT29vkzGRNo7Hnof0/GvlC9t5o4p4SrAxyb2XHPAKn8u9R1NFsdxpF02oaTbSW8mzK4y3txitW9uNdt7WG2ESsNwkMzPhSOwriPBWoApPpzttJJkiJ7/wB4f1/OvRraVLyG2imky8a7Tn0zWM9GdVN8yLejv4iWML/adlEjNkIYCSPcGtaS08SXaSJLf2aDadreSck++DVrQbCzUtFIoCdB83FdAIIIYxtwMUuhq30sc5ZW13bwwyXU4kldcEKOprhPilrl3YRWNvZztDK7yF3UdtuMfrXo0lzChZ052ghV9DnpXk/xPtJRcacWY7HL7mPID8HP5E/lSha+pFS9jIt4LU36BRtidUK/7O4c/kTXuHwY0VtP8P39264+13OFOOoX+mTXz6LsSXQeIHanCL1JxgD+VfWfg3S5NI8G6XZzArMkCtID1DNyR+GcVtFa3Oab92xrba5Xx58Q9F+HljZz6ulzL9skZI0tlR3+UAkkMy8c4z611+0+lfJP7Qnir+3viTJp8Lk22ip9kUBsqZM5kb2OcL/wAZrUwOF8G+J7rwd4v0/XLQbntJQzJnHmIeGTPupI/GvuXQdZsPEmg2esaZKJrO8j8yNgc47FT7ggg+4Nfn9XrXwQ+LJ8EaudJ1q4lbw/dnp94WshI/eAddvUMB9e3IB9ayQpNGY5FDKeoP51yXiX4W+GPFFw91dWj214/wB64tX8tmPqR0J/CuxhkjuIEmhkSWKRQ6SI25XU8ggjqD60/bSauNOx4dcfs4RJfRXGm+JpojG4ZRPbBiPxUj+VcHJNLbTygEho3MbAdiDivbfif8S/+EFt0s7Kxa91a5tpJ4xvCrAq/KJGB5b5jwo64NeA29/9uQ3LO7/aB5haTG4seSTjjOc9KiaNqbZt2XiO6gbO9mHXae9an/CS6vLEVVgu7oQOlcxp8ayXRBB6ZxXY20amKMlQTgA4rmk7HbBNot6HFcSKrTyMxzuweufWq3xF0ttR8HmSGJpZ4p1aKNBlm5wQB9M/lWzZFi4jjAy3fv8A/qrI+IesXmi2WnXmnbC9jdJKVcZDsAwUH1GTn8KIbiqaRZo/Bf4c6bLZxeKb5kup1lZIICMiF0O1i3YsCOMZHeva9ua8e+Gr61ofhnfOxie6uHuBEcEENgklRwMnJ4ruNR+IekaDoc+p64WtIoR/CN3mt2RB13HsPzOK6FUjflOGUJW5ir8VPHUfw/8AA9xqKOo1KfMFghXOZT/EeMYUZbnrgDvXxLPPJc3Ek8zmSWVi7sxyWJOSSfrXUfEbx7ffELxXLqt0pggUeXbWwcssMY6D6nqT3NcnWpkFFFFAHp3wt+NOrfD+YWV2JdU0R8A2rSYaDnloienf5eh9ute6aj8W/wC2bNZvCzxmzlU4uWXMgIPI2n7h+o9xXx7VvT9UvdKuhcWN1LbSj+KNsZ9j6j2NTJNrRlRaT1PRvE2tXg8R6ncXjXF3fXG2KB3Yt+728HP+8TxUVlbPBZwxHOVjC59656z8ZrNrJvtYtPPJGN1viMjC4Hy9D+nUnmvSfDcGneJbJrm0WaMQhC6zAfxAnAwTnofSspvlR0U7SZi20kqBkVWMp6YHb/69djo32u7hXMBgZVwS4wTzxjtWjHpdqo2+Xh1+UOOvNadhCFwNq4Jz9DXO3c60rEtjA0AwG+duM+vtXlvjy/1LUdYu2tmkfTtLljgZVOEeYnkEdzzt9q7fxJ8QdM8JSXNvc213PPAEJWJVCEMARhic9D6V4FceKb5/PFu724mn+0tiQsRJnIYdgQc8gZ9+K2pwe5zVqi2PpHxJ410fwVpgfUJg9wAqx2MTjzmyPQ/dUYPJ9vUV87eMvHGreNdQSfUHVIYciG3iGEjBP6npljycVz888txM800jyyucs7sWZj6knrUdaQpqBhOo5hRRRWpkf//Z",
    62: "data:image/jpeg;base64,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",
    63: "data:image/jpeg;base64,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",
    64: "data:image/jpeg;base64,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",
    65: "data:image/jpeg;base64,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",
    66: "data:image/jpeg;base64,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",
    67: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV03hX4f+IvF8mdMsWFsDhrqb5IV/4Eev0GT7V6J8OPgqt5bW+teKVYQSgtFp3KM4I+V3YHKjqdo5PGcDivckiSKGOGNFjiiUIiKMKigYAA7AAUAeU6F8BdAslSTWLy51SUD5o4z5EWefT5j1HccjuDiu5tPBvhqwVxa+H9NiD43Zt1fOOn3s+prXu7u2sbZ7i5lWKJASWY4H0+teOa58WtVuZ3XS2isYQTtygeQjtkngfgKTY7Hs53v1LEVFc20d1bm3uoUnhbGY5kDocHIyDwea+abnxPrk8plm1G6mJPXziP0q/o3jnV9NmXyr65iHdWYup+oORRcqx7PqXw78JasJftXh+z3y43SQqYW46YKkY6dq858Rfs/oIGm8Oam7SLyLa9wN3A4EgwM5z1AHI5712Hhz4lQ3qrHq0SxZ4+0w5Kf8CXt9RXeoUljWSNg6MMqynII9RQhNWPjTW/D+reHb42mrWE1nMOQJFwGHqp6Ee4rOr7R1bRdO1/TX0/VbOO8tX52SD7pwRuU9VYZOCK+bviT8LrrwRMl5aPJe6PLhVnZRuif+6+OBnseh+tMk8/ooooAB1r3H4L/C+G4t4/FOvWjMpIbT7eVRscf89mHcA8KCMHryAK88+GvguTxx4xg08sY7OEfaLuQDpEpGQPdiQo+uegNfXSQRwxrFDEkMSAKkcahVRRwAAOgAoAiKkkk5JPJJrnvF3i6w8J2Ie5YGeUHyoupYj/PWuo2V8z/E3VZ9T8f6pvbKW832WIZ4VU4/U80mUhb3XNa8aavummZgfuoDhI19AOlW5fAlw1uJYlL5HLYxzW18PdFVdO+0sOWP516jp0CvGEdRjtXBOq3LQ9SlQjyXkj5qv9OuLC4dXQqQeRio4o1uBtGVlH3SK+l9S8AaNrQLXFuQx/iU4NcbqfwFLBpdL1Xb3CSrj9RW8Kt9zCpQt8J5Xp13NYv87GNx1BGQwrv/AAP47FhMbafc1oT8yDnZ/tL/AIVlXvw38R6ePljE7L/CG6VxOpNqdndE3CSQvG20jP3SK254y2ZzunKC95aH1bGySxLJGwdHAZWHQg96Zd2Nvf2c1pdwJcW06FJYpBlXU9jXE/CbxEdV0VtPmfc9uoeInqUPUfgf516FsqlqZNWPlL4qfDpvAusxyWZlm0i9y0EjrzGwPMTN3IGDnuD65rga+0/FXhWy8X+G7nRr4YWYZjlAG6KQfdYHBxzwfUEivjbUtPuNK1S50+7jMdxaytFIh7MpwaZJ9I/s++GxpngSbWZEK3GrTHad3/LGM4Xjtlt5+mPWvVdlVdA0f+wfDWmaRjBsbWOBhvLgMB82D3G4tj2xWhsoGVpZEtoXnlO2OJS7E9gBk/yr5E1i6/tDV5LsHMt1O7sP95iR/Ovp/wCIV5/Z3w+1if1gMY/4Fx/WvleN/M1e1VAGVmXHsc1MmVFHs2iS3FppsEFpbiWQKBy21F92P+FPu/EPi20Y7G0gonZAxOKqXCXsGjF7RN8m3hc9azdEuNfm8Rx2j3ymxcAybY1Cp6jbjJPbGRXn0lzHr1Xy23+R6d4V8VXGo2YF15QuM4YR9K0fEfiXUdNtv+JfFBJMe0xIH6Vy3hGxnt/EO+4iEZPVVOQcdwf8ea3vGFnczAyWYUSA9W6KO59/pQm72KaVrmPpXijxJqU5S5i0dt3RFdkY/nXC/FnTQkR1MWzQNKyiWN+qsOM5HBBGOauaRN4ukupI7q5iuVVwEgk2sHy38JUZTA710HxL0q4u/h7dMwJmgQSYPJ4IyPyrR3jJGNlKDPN/hlr/APY/iSwLNiJiY3+hr6WUAqCDkHkEV8b2Mk1p9nuQcYfI96+s/CGprrXhWxvVIbfHgnOeRwa7FoeY9dTW2182/tE+HjY+M7TWYkAi1SAByAP9bH8pzgd12nJOTz6V9Mbazdb8MaL4mtIrbW9Mi1GGFzJGkhYBWIwT8pHaqJNdgWYsepOaTbU7x7XI9Dim7aBHlXx31E2vgiKxRsNeTjP+6oyf1Ir520wiPVLaZ84EqkD2Br2b9oG6Lavp1sM7YrdmPuWb/AV4vbjzbxI9yhhkglto45qXsy46NH0j4fWGW3VHXJxwa3DYQQAukSqT3A5rjvDF+Pslu+7h0U/pXcR3KvbHBBJHFeVE+gkk9TI0udDru0MF25HPc11k3ly3Hlvtbd6HOK8zPhHXLvX0uIr/AGRxhiBuwGzzkj1Fdpo/hy80++kuptVmuYp1U+U4GEYDHy+31q0mJ22NqKwiiPCqR645rn/HUsUXhLUieFWBxz9K6GW5MS7W4PSuG8eCbVtAudPtQzyT/LtQZZh1IA7ninu0Ta0Wz5pysjBQduGIH0r6H+BuqF9HudKlb5oiJkB9Dwf6V85xIySkEMvXAPUH/GvXPg9q/wBl8ZWqO2I54zCfqen616TPCirpn0RtpyEoSR3p+2nxxByckD6mmQYfgjWf+Ej8CaLqzSeZJc2iGRi4cmQDa+SO+QSfrW6V4rw/9mfxdHd6Fe+E55D9os2N3bBjnMTEB1Hphuf+BmvcZm8qF3P8IzQB8z/Gy/8AtfjO4hUhhboqj6968nmA5xyD6123ja++2+MNTm4IEhXjocHH9K4y5APmAdjuqUW0ex+F5vN8O6fNG3BhX9Bj+ldDd6vqNjp0T2kH2h2bld20AfWvKfAniT7K39l3B/dZ3Rv/AHc9QfavULZvOj2CT3FeXOLhNpnuUZqpBNCW3iPxM0okVbeJwP8AVnIB9iSK27PxB4nJCCK2uieSmSu323AYpum6VBNJl534P3VPFdLb6VHCuYZm2nse1VfQ3bjtYqxXF7qFs0V0ht5lbBwc/ke9ee/F2aTRvDtglpdSR3bXgkR0YhwFU5OR9f1rv9X1O00e2kuricIkSkknqcfzNfO/ivxjc+L9b87YY7dBshQ8kKTnJ9zWlCHNO5xYqoo0+Xuc7JHImJHJd255+tdR4Muntry3uFba8T7x+FYrSqIZA65wBj2q/wCGiQFYkAAlT+NegzyI7n2LZXCXthBcxnKTIHH4iua8f/EXSPh1YWdxqkFxc/bJGSOO2KbxtGS2GI45xn1qP4U6sNU8EQxlt0tm7QNzzjqv6H9K+fv2hvFP9u/El9OifNtoqfZFAcFTJndI3HQ5wv8AwDnmhMWzOF8GeJ7nwd4v0/XLUbntJQzJnHmIeHX8VJFfal9r1jfeCjrenzCeyuLYzwuQV3LjjOeh7Gvg+u68GfEi78PeHNT8O3Rkn02/T92N/wDx7Sd2Uejdx7A/VMFuQzu13fXch53Nn9TWPMn+tY9uP1rUtSfKuZFIIJUA+vvWdOwED9ixzz9eKEtByepJ4d51ZQe4xXp9lNPaRqVckL0yeleU6Y5gv43BwQa9W09vPsVJ54rhxXxXPTwT91o6C01uWIb2Qlj6VfXxXf8Al+Vb2w3NwGY1Q0ywNyAB0rpLPR4Y5UABkbrx2rmV2d7aW5w/jS3uV8MXV7eys8pU4BPC59q8bjYwzIe2Aa9x+L+YPCBUcBnVcV4Y/wC8YcAfKF49R3r0MOrRPHxbvNG3CEa0mDjd5gHPoRTtEfyjMh6qf5UzTHV7d42XJx/SoIrqKxLTuxABKkeveug5UejaB8SH+H+gaxPFzdXsG2zBGQJwcBiPRQSeeuAO9eJTzyXNxJPM5kllYu7McliTkk/jVjUtRk1G6Mj5VBwiZyFFU6SVgk7u4UUUUyS/YapJZxmFhvhY5K9wfUGrUsqXEe6Js88/0rGpySNG25GKn2oA1EJVh6ivU/A8322yRG5KnbXkKX7dJFDDrkcGvV/hAyalNexplTAiS/MOOWx/WuevHmideFnyzser6VZRRYyvNb8aRwxkooBNJJpgRAVfacdRUkFuGtyXbIHB965Ej0mzyP4z3rNpNta9d8wJx2wDXjD8OR6HFepfG3XrNNRj0yOKUS2zhn4ATlcjHOf0rx2S8kkGBhfp1rtpK0Ty8Q7yNuHUIdOy8uWLjhB1PP6Vh3V1JdTM78AnIUdBUBOeT1orY5gooooA/9k=",
    68: "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAcFBQYFBAcGBgYIBwcICxILCwoKCxYPEA0SGhYbGhkWGRgcICgiHB4mHhgZIzAkJiorLS4tGyIyNTEsNSgsLSz/2wBDAQcICAsJCxULCxUsHRkdLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCwsLCz/wAARCABuAG4DASIAAhEBAxEB/8QAHwAAAQUBAQEBAQEAAAAAAAAAAAECAwQFBgcICQoL/8QAtRAAAgEDAwIEAwUFBAQAAAF9AQIDAAQRBRIhMUEGE1FhByJxFDKBkaEII0KxwRVS0fAkM2JyggkKFhcYGRolJicoKSo0NTY3ODk6Q0RFRkdISUpTVFVWV1hZWmNkZWZnaGlqc3R1dnd4eXqDhIWGh4iJipKTlJWWl5iZmqKjpKWmp6ipqrKztLW2t7i5usLDxMXGx8jJytLT1NXW19jZ2uHi4+Tl5ufo6erx8vP09fb3+Pn6/8QAHwEAAwEBAQEBAQEBAQAAAAAAAAECAwQFBgcICQoL/8QAtREAAgECBAQDBAcFBAQAAQJ3AAECAxEEBSExBhJBUQdhcRMiMoEIFEKRobHBCSMzUvAVYnLRChYkNOEl8RcYGRomJygpKjU2Nzg5OkNERUZHSElKU1RVVldYWVpjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKkpOUlZaXmJmaoqOkpaanqKmqsrO0tba3uLm6wsPExcbHyMnK0tPU1dbX2Nna4uPk5ebn6Onq8vP09fb3+Pn6/9oADAMBAAIRAxEAPwD5toooAzQAV0fhbwF4h8Xyf8SuxY24OGuZfkhT/gR6/QZPtXoXw2+Cz6gkOseKYillIm+GxyyySZ6M+MFV7gdT7Dr7tb2sFpbR29tDHBBGMJHEoVVHsBwKAPKdC+Aeh2axyaze3GpSgfNHF+5izznkfMRyO45HvXb6d4G8MaVD5VpoFgowFJkhErNjpkvnmt+eWK2iMs8qRRjqznArida+J2nafdGGxhGo4GNyvsBb0GR0FJtIpK52m3jAGAKjuLSC7gMFzBFcRNgmOVA6nHTIPFeST/F7WZbgpBaWcHPAZS/H1zVm3+LOq2rB9Q0+1nizz5RKH8+aVx8rO01X4e+FNaTbeaFaBsBQ8CeSwAOeCmPWvN/Ef7PwELTeHNTZnHItr3A3cDpIMDPXqAORz3r1bw54o0vxRZ+dp837wDLwvw6fh3HuK2ttUTY+Mda8P6r4dvjZ6tYTWc45CyLgMPUHoR7is6vtHWdC03xDpj6fqtpHd2rc7W6qcEblPVTyeRXzZ8R/hdeeCJlu7Z3vdIlO1ZyuGib+64HAPoeh+tAjgaKKKAAda9q+Cfw0h1FF8U61bLLbK3+gRMQVkZSQzsvcAjAB6kHjArzz4e+E38Z+NbLSvmFuT5ty6/wRLyx9s9B7kV9g29pDaWsNtbxCKCBFjjQdFUDAH5CgBpXJyeSaraheW+mafPe3biOCBC7t7D+tX9leQ/HDxMttb22gwsdx/wBJuPQjoi/ieT9BSbKSucV4s8c3mvakLjJEKNmKAn5UXtx3Y1dk8Laxqvhm1ubO2LSKzE5BB2nnH51lfDbwlL4o1o3l0pNhbtzno7elfSlpBFb2iRRoqogwFA6Vy1anK7I7aNHnV3sfJ11pmq6bdEXdpNHg8kDiql7fyK6qWPP94YJH1r6w1Kxs7qEiS2jZvdeteW+LPhraajCz2qCFxzgURrp7lSwrWsWeT6PrlzpWoR3llO8U0Tbsqef8+1fSHgjxha+MNJ81MR3kIAni/wDZh7GvmPV9IvNA1FrW7QqR0b1Hrmtnwd4ouPDuv21/AT+7b94meJEP3h+I/pW9+qORq+jPqnbUN3Y22oWU1neQR3FtOhSSKQZV1PY1NZXUGoWEF5av5kFwgkjYd1IyKn2VoZHyh8U/h03gXWo3tDJNpN7lreRhzGQeY2PcgYOe4I75rgq+0vFvhWz8YeGbrR7wBRMMxS4GYpB91gcHHPB9QSK+NtRsLjStTubC7jMVxbSNFIh7MpwaBH0T+zt4dFn4QvNdljAm1Gbyomxz5UfXBz0Lk9gfl7g17BtrL8HaT/YngjRdNKOjW9nGrrIMMGI3MD7gkj8K2dtAyLZXyn8VtSN9491bBLEXBjAznAUbQP519XyMIYnlb7salz+AzXxq+/XvHMSfee9uwef9p85pMpH0F8OdHXR/C9lbgfOEDuf9o8mu5VRjJauV+1zadB5VpECUTLOxwqL0GSaxofEHiK5vjEsmlugPOxnzj0zjGa89x5tWerGXLZI7yZQWxuyKqXMI24O3p0NVLW4uprFpHGH6YBzyK5fU9Q8QNN50Fzp1tbknDXJJb8hWfJd2NnJJXIPGHhS08Qae8cqBZQP3cndTXgLQS6dqklnNw8TlD+Hevo61uNQmtN1xLaXyZG9rY5MefavH/ivox0vXI9QjXC3Izn/aHX+ldFBtPlZw4hKS50eq/AvXpNQ8OXekTuGfT5N0XqI25I+gb+dep7a+X/g14iOlfECyaQhYNQJtZOeBu+6f++gPzr6l2V2I4WRba+bP2iPD5sPGlrrEaARapAN5AA/ep8pzgd12nJ5PPpX0xtrJ8Q+EtF8W2UNrrVgL2KBzJGhdl2sRgn5SO1MRuleeBSbam2g8joelG2gRzvja7GneBdaud20raSAH3I2j+dfMXw5sYrrx9p1w4yscjYJPdVOP5V7/APGy6Nn8LL/BIM0kcf8A49n+lfO3w6nnXxBF5Cb3t3M3XHyj736VnPZm1L4kfSb6emoQBJPmjjcMUA4LDkZ9R7VmR+HSly/kRMqyNucscDNdFp0itEp7HofUVLe3GyPZE4EjdPp3NcSbPUUdSKziWDTnt0XcEB/Gubl8Pjy5kKtLBITkBuQCc49vwrSXxLZBp44GLi3co7MpXtnOT1HuKg0jxHDeslzAzm2mUgh1xtYHjrzyKnVO5py3WhFZeG4oDBND5kRgQxqT3U9QfUfWuD+MGnpPocQk+ZlmG0/gc/yr1aedJAGQhc/rXmPxOzPaqCzbLeNrhwq5LY4A9u/JojNuaZlUglFo8TtLhrW7SWE4eKQOpHGCDkfrX2hoWpLrnh6w1RRgXcCSkdcEjkfnmviG2cuxYn7zZr6q+BWp/wBo/DWK3ZsvYzvD/wABPzD+Zr0jyGeh7afGShJHen7afHEGJyQMetMk5r4baqmufDPw/fJs5s0hYISQGjHlkc/7vPvXT7a8I/Zi8UJNpmp+Fppf30D/AG23U9ShwsgHPYhTj3J7173toA8p/aEkWL4X7T96S9iVfyYn9K+avC3iFvDes/bhbLdLseNomYrncPX2PNe3ftL6x/yB9FVvuq91IPc/Kv8AWvnyD+PI4NJ6lJtWsfWvhPVl1rwpYahEMCeBX29wcYI/AgipZ9Sgsi73jmJ2+UfKW4zgdBXkPwe8aLaRf8I7dsVYs0lq56c8sh/mPxr2USvcW+5Vz64rhkuWVj1aUuaNzCuNQ06afbtdpP7ojOWP0p9xNDZ2Cp9lukZzkDyDjP4dK00glDApGq49Tin+TJypiQBu470m9De66GbbXM5g3SLjHQ+o9a8c+KXiq9/t6fSbSfZE9sqXG3qwJ3bfp0NereIdRTSdJmnblIVJwOrY7Cvmm51GbUdXn1G45lncu3oM9vwFVRjeV+xyYqdo27kEBAbC+te7/s56x5WuappDFQtzEJ4xnncp5H5E14Sq7ZmHqQ1emfBa9Nl8T9IbIAmZrZ+ezKcfriuw89H1btrlfHnxD0X4eWNnPq6XMv2yRkjS2VHf5RknDMvHOM+tdftPpXyT+0J4qGvfEmTToXLW2ip9kUBsqZM5kb2OcL/wAZqiDhfBvie68HeL9P1y0G57SUMyZx5iHhkz7qSPxr7l0HWbHxLoNnrGmSiWzvEDxsDnHYqfcEEH3Br8/q9O+FHxeuvAUd9pt609zpNzC5iiXB8icj5XGex6MB657cgEHxf1oa18SdXnSUyIkvkp/shflwPyrhYxtT65rbfY+k3t/cvunuJQsfI+f5ssR9P61ij7oFSUaOhXhsPEdjcocGOVT+HQ19L2l3NFaRXFuTJGwBKH09jXy5bAm7j29QeK+l/C9yJ9Ft1PJEYyPwrnqq524Z6NG1/aPnKMxsOM9OlVbzUpkhKRowLdCauqy/N8owOlZ92u+YY6d65pXasd0fM4vxv5o8M300zE7bd9o7AkV4RChKjHXFe7/EmZV8IXiqekZGM+teGWzbSrH0x+NdOHVkzhxbvJD5ojG6564IP4GtvwtfSWHiGyuojiSG4jkX6g9P0rB+0NNeOzcqxOR9av6fKltOs8pCrAwZiR1KsCF+pwRXQzjW59dfEz4hW/gr4fPrVtIpvr5AmnKVyGkYZ3EdMKDk564A718VTzyXNxJPM5kllYu7McliTkk/jW14u8V3nivWWuZnlW1iylpbPJvFvFkkIDgevJxzWDVEBRRRQBMlwwVUY5QcD2q0ozDvByoOMis+nJI0bZRiDSsO5v+H4km1GNH+8eV5r3/wAOI1mIEJ42gV85abqq2V7HcPEco2R5Zxxj7uPQ/X1r3fwFrMfiGyZ4xKrQbd3mAD7wJGMHnofSsai6nZh5XujvJ2RgcDn2qhfTCOEY+92xVu2hLu2TSz6ashLlunSsGjtR5T8QWddDZJP+W8gHXsOT/n3FeQTHEZ/3q9E+Ieqx3GsXUczSqtkqhFRQRtJHfPU5yeOwHvXnT6goi2Q2yxuWz5jMWboOB2HOe2eetdVONoI82vPmmxbeAxRm4nby4iQpGR5jZ5yqnkjjr06eoqO7vnuljQoiJGMAKMbj6se57Z9hVZmZ2JYliepNJWhzhRRRQB//2Q==",
    69: "data:image/jpeg;base64,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",
    70: "data:image/jpeg;base64,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",
    71: "data:image/jpeg;base64,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",
    72: "data:image/jpeg;base64,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"
  };

  window.__SENADO_DATA__ = { SENATORS: SENATORS, PHOTOS: PHOTOS };

  var VOTE_ORDER = ["pending", "positive", "negative", "abstention", "absent"];
  var VOTE_FILL = {
    pending: "var(--vote-pending-fill)",
    positive: "var(--vote-positive)",
    negative: "var(--vote-negative)",
    abstention: "var(--vote-abstention)",
    absent: "var(--vote-absent)"
  };
  var VOTE_LABEL = {
    pending: "Pendiente",
    positive: "Afirmativo",
    negative: "Negativo",
    abstention: "Abstención",
    absent: "Ausente"
  };

  var MAJORITY_OPTIONS = [
    { value: "two_thirds_body", label: "2/3 del cuerpo (48 votos)" },
    { value: "two_thirds_present", label: "2/3 de miembros presentes" },
    { value: "absolute_body", label: "Mayoría absoluta del cuerpo (37 votos)" },
    { value: "absolute_present", label: "Mayoría absoluta de los votos emitidos" }
  ];

  var votes = SENATORS.map(function () { return "pending"; });
  var selectedMajority = "absolute_body";
  var selectedBloque = "TODOS";
  var searchQuery = "";

  var majoritySelect = document.getElementById("majoritySelect");
  var bloqueSelect = document.getElementById("bloqueSelect");
  var searchInput = document.getElementById("searchInput");
  var resultBox = document.getElementById("resultBox");
  var chamber = document.getElementById("chamber");
  var tooltip = document.getElementById("tooltip");
  var rosterPanel = document.getElementById("rosterPanel");
  var rosterLabel = document.getElementById("rosterLabel");
  var rosterGrid = document.getElementById("rosterGrid");
  var downloadPdfBtn = document.getElementById("downloadPdfBtn");
  var printView = document.getElementById("printView");
  var undoBtn = document.getElementById("undoBtn");
  var scenarioSelect = document.getElementById("scenarioSelect");
  var newScenarioBtn = document.getElementById("newScenarioBtn");
  var saveScenarioBtn = document.getElementById("saveScenarioBtn");
  var deleteScenarioBtn = document.getElementById("deleteScenarioBtn");
  var scenarioStatus = document.getElementById("scenarioStatus");

  function normalizeText(str) {
    return String(str)
      .normalize("NFD").replace(/[\u0300-\u036f]/g, "")
      .toLowerCase();
  }

  function matchesFilters(sen) {
    var bloqueOk = selectedBloque === "TODOS" || sen.bloque === selectedBloque;
    var q = searchQuery.trim();
    var searchOk = q === "" || normalizeText(sen.nombre).indexOf(normalizeText(q)) !== -1;
    return bloqueOk && searchOk;
  }

  MAJORITY_OPTIONS.forEach(function (opt) {
    var el = document.createElement("option");
    el.value = opt.value;
    el.textContent = opt.label;
    majoritySelect.appendChild(el);
  });
  majoritySelect.value = selectedMajority;

  var bloques = Array.from(new Set(SENATORS.map(function (s) { return s.bloque; })))
    .sort(function (a, b) { return a.localeCompare(b, "es"); });

  var allOpt = document.createElement("option");
  allOpt.value = "TODOS";
  allOpt.textContent = "Filtrar por bloque (todos)";
  bloqueSelect.appendChild(allOpt);
  bloques.forEach(function (b) {
    var el = document.createElement("option");
    el.value = b;
    el.textContent = b + " (" + SENATORS.filter(function (s) { return s.bloque === b; }).length + ")";
    bloqueSelect.appendChild(el);
  });

  // Posiciones reales de dos alas, tomadas del plano oficial del recinto (recinto2026.pdf)
  var seats = SENATORS.map(function (s) { return { id: s.banca, x: s.x, y: s.y }; });
  var SEAT_RADIUS = 16;

  var svgns = "http://www.w3.org/2000/svg";

  function buildChamber() {
    chamber.innerHTML = "";

    var dais = document.createElementNS(svgns, "rect");
    dais.setAttribute("x", "355");
    dais.setAttribute("y", "400");
    dais.setAttribute("width", "90");
    dais.setAttribute("height", "34");
    dais.setAttribute("rx", "4");
    dais.setAttribute("class", "dais");
    chamber.appendChild(dais);

    var daisLabel = document.createElementNS(svgns, "text");
    daisLabel.setAttribute("x", "400");
    daisLabel.setAttribute("y", "421");
    daisLabel.setAttribute("text-anchor", "middle");
    daisLabel.setAttribute("class", "dais-label");
    daisLabel.textContent = "PRESIDENCIA";
    chamber.appendChild(daisLabel);

    var defs = document.createElementNS(svgns, "defs");
    chamber.appendChild(defs);

    seats.forEach(function (seat) {
      var sen = SENATORS[seat.id - 1];
      var g = document.createElementNS(svgns, "g");
      g.setAttribute("class", "seat");
      g.setAttribute("data-id", seat.id);

      var clipId = "clip-seat-" + seat.id;
      var clipPath = document.createElementNS(svgns, "clipPath");
      clipPath.setAttribute("id", clipId);
      var clipCircle = document.createElementNS(svgns, "circle");
      clipCircle.setAttribute("cx", seat.x);
      clipCircle.setAttribute("cy", seat.y);
      clipCircle.setAttribute("r", SEAT_RADIUS - 2);
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      var photoBg = document.createElementNS(svgns, "circle");
      photoBg.setAttribute("cx", seat.x);
      photoBg.setAttribute("cy", seat.y);
      photoBg.setAttribute("r", SEAT_RADIUS - 2);
      photoBg.setAttribute("fill", "#cfd8e0");
      g.appendChild(photoBg);

      var photo = document.createElementNS(svgns, "image");
      photo.setAttributeNS("http://www.w3.org/1999/xlink", "href", PHOTOS[seat.id]);
      photo.setAttribute("href", PHOTOS[seat.id]);
      photo.setAttribute("x", seat.x - (SEAT_RADIUS - 2));
      photo.setAttribute("y", seat.y - (SEAT_RADIUS - 2));
      photo.setAttribute("width", (SEAT_RADIUS - 2) * 2);
      photo.setAttribute("height", (SEAT_RADIUS - 2) * 2);
      photo.setAttribute("clip-path", "url(#" + clipId + ")");
      photo.setAttribute("preserveAspectRatio", "xMidYMid slice");
      g.appendChild(photo);

      var highlight = document.createElementNS(svgns, "circle");
      highlight.setAttribute("cx", seat.x);
      highlight.setAttribute("cy", seat.y);
      highlight.setAttribute("r", SEAT_RADIUS + 3.5);
      highlight.setAttribute("class", "seat-highlight");
      highlight.setAttribute("fill", "none");
      g.appendChild(highlight);

      var ring = document.createElementNS(svgns, "circle");
      ring.setAttribute("cx", seat.x);
      ring.setAttribute("cy", seat.y);
      ring.setAttribute("r", SEAT_RADIUS);
      ring.setAttribute("class", "seat-ring");
      ring.setAttribute("fill", "none");
      g.appendChild(ring);

      var badge = document.createElementNS(svgns, "circle");
      badge.setAttribute("cx", seat.x + SEAT_RADIUS * 0.72);
      badge.setAttribute("cy", seat.y + SEAT_RADIUS * 0.72);
      badge.setAttribute("r", 6.5);
      badge.setAttribute("class", "seat-badge");
      g.appendChild(badge);

      var badgeText = document.createElementNS(svgns, "text");
      badgeText.setAttribute("x", seat.x + SEAT_RADIUS * 0.72);
      badgeText.setAttribute("y", seat.y + SEAT_RADIUS * 0.72 + 0.5);
      badgeText.setAttribute("text-anchor", "middle");
      badgeText.setAttribute("dominant-baseline", "middle");
      badgeText.setAttribute("class", "seat-badge-text");
      badgeText.textContent = seat.id;
      g.appendChild(badgeText);

      g.addEventListener("click", function () { cycleVote(seat.id); });
      g.addEventListener("mouseenter", function (evt) { showTooltip(seat.id); });
      g.addEventListener("mouseleave", hideTooltip);

      chamber.appendChild(g);
    });
  }

  function showTooltip(id) {
    var sen = SENATORS[id - 1];
    tooltip.innerHTML =
      '<div class="name">' + sen.nombre + '</div>' +
      '<div class="bloque">' + sen.bloque + '</div>' +
      '<div class="prov">' + sen.provincia + '</div>';
    tooltip.hidden = false;
  }
  function hideTooltip() { tooltip.hidden = true; }

  var HISTORY_LIMIT = 30;
  var history = [];

  function pushHistory() {
    history.push(votes.slice());
    if (history.length > HISTORY_LIMIT) history.shift();
    undoBtn.disabled = false;
  }

  function undo() {
    if (history.length === 0) return;
    votes = history.pop();
    undoBtn.disabled = history.length === 0;
    render();
    saveState();
  }

  function cycleVote(id) {
    pushHistory();
    var idx = id - 1;
    var current = VOTE_ORDER.indexOf(votes[idx]);
    votes[idx] = VOTE_ORDER[(current + 1) % VOTE_ORDER.length];
    render();
    saveState();
  }

  function setVote(id, value) {
    votes[id - 1] = value;
  }

  function bulkAll(value) {
    pushHistory();
    votes = votes.map(function () { return value; });
    render();
    saveState();
  }

  function bulkFiltered(value) {
    pushHistory();
    SENATORS.filter(matchesFilters)
      .forEach(function (s) { setVote(s.id, value); });
    render();
    saveState();
  }

  function computeResult() {
    var positive = votes.filter(function (v) { return v === "positive"; }).length;
    var negative = votes.filter(function (v) { return v === "negative"; }).length;
    var cast = positive + negative;

    switch (selectedMajority) {
      case "two_thirds_body":
        return { approved: positive >= 48, text: "Se requieren 48 votos positivos (" + positive + " obtenidos)" };
      case "two_thirds_present": {
        var need = Math.ceil(cast * 2 / 3);
        return { approved: positive >= need, text: "Se requieren " + need + " votos positivos de " + cast + " presentes (" + positive + " obtenidos)" };
      }
      case "absolute_body":
        return { approved: positive >= 37, text: "Se requieren 37 votos positivos (" + positive + " obtenidos)" };
      case "absolute_present": {
        var need2 = Math.floor(cast / 2) + 1;
        return { approved: positive >= need2, text: "Se requieren " + need2 + " votos positivos de " + cast + " emitidos (" + positive + " obtenidos)" };
      }
    }
  }

  function render() {
    Array.prototype.forEach.call(chamber.querySelectorAll(".seat"), function (g) {
      var id = Number(g.getAttribute("data-id"));
      var sen = SENATORS[id - 1];
      var v = votes[id - 1];
      var matches = matchesFilters(sen);
      var filtersActive = selectedBloque !== "TODOS" || searchQuery.trim() !== "";
      g.style.opacity = matches ? "1" : "0.25";

      var ring = g.querySelector(".seat-ring");
      ring.setAttribute("stroke", VOTE_FILL[v]);
      ring.setAttribute("stroke-width", v === "pending" ? "2" : "3.5");
      if (v === "pending") ring.setAttribute("stroke-dasharray", "");

      var highlight = g.querySelector(".seat-highlight");
      if (filtersActive && matches) {
        highlight.setAttribute("stroke", "var(--brass-strong)");
        highlight.setAttribute("stroke-width", "2.5");
      } else {
        highlight.setAttribute("stroke", "none");
      }
    });

    var positive = votes.filter(function (v) { return v === "positive"; }).length;
    var negative = votes.filter(function (v) { return v === "negative"; }).length;
    var abstention = votes.filter(function (v) { return v === "abstention"; }).length;
    var absent = votes.filter(function (v) { return v === "absent"; }).length;
    var pending = votes.filter(function (v) { return v === "pending"; }).length;

    document.getElementById("totalPositive").textContent = positive;
    document.getElementById("totalNegative").textContent = negative;
    document.getElementById("totalAbstention").textContent = abstention;
    document.getElementById("totalAbsent").textContent = absent;
    document.getElementById("totalPending").textContent = pending;

    if (positive + negative > 0) {
      var result = computeResult();
      resultBox.hidden = false;
      resultBox.className = "result " + (result.approved ? "approved" : "rejected");
      resultBox.innerHTML = (result.approved ? "✓ Aprobado — " : "✗ Rechazado — ") +
        '<span class="detail">' + result.text + "</span>";
    } else {
      resultBox.hidden = true;
    }

    renderRoster();
  }

  function getReportData() {
    var positive = votes.filter(function (v) { return v === "positive"; }).length;
    var negative = votes.filter(function (v) { return v === "negative"; }).length;
    var abstention = votes.filter(function (v) { return v === "abstention"; }).length;
    var absent = votes.filter(function (v) { return v === "absent"; }).length;
    var pending = votes.filter(function (v) { return v === "pending"; }).length;

    var majorityLabel = MAJORITY_OPTIONS.filter(function (o) { return o.value === selectedMajority; })[0].label;

    var resultLine = null;
    if (positive + negative > 0) {
      var result = computeResult();
      resultLine = (result.approved ? "APROBADO" : "RECHAZADO") + " - " + result.text;
    }

    var now = new Date();
    var fecha = now.toLocaleDateString("es-AR") + " " + now.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });

    return {
      fecha: fecha,
      majorityLabel: majorityLabel,
      resultLine: resultLine,
      positive: positive,
      negative: negative,
      abstention: abstention,
      absent: absent,
      pending: pending
    };
  }

  function renderRoster() {
    var filtersActive = selectedBloque !== "TODOS" || searchQuery.trim() !== "";
    if (!filtersActive) {
      rosterPanel.hidden = true;
      return;
    }
    rosterPanel.hidden = false;
    var miembros = SENATORS.filter(matchesFilters)
      .sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); });

    var label = selectedBloque !== "TODOS" ? selectedBloque : "Resultados de búsqueda";
    if (miembros.length === 0) label = "Sin resultados";
    rosterLabel.innerHTML = label + ' <span class="count">(' + miembros.length + " senadores)</span>";

    rosterGrid.innerHTML = "";
    miembros.forEach(function (s) {
      var btn = document.createElement("button");
      btn.className = "roster-item";
      btn.innerHTML =
        '<span class="dot" style="background:' + VOTE_FILL[votes[s.id - 1]] + '"></span>' +
        '<span class="who"><div class="n">' + s.nombre + '</div><div class="p">' + s.provincia + '</div></span>';
      btn.addEventListener("click", function () { cycleVote(s.id); });
      btn.addEventListener("mouseenter", function () { showTooltip(s.id); });
      btn.addEventListener("mouseleave", hideTooltip);
      rosterGrid.appendChild(btn);
    });
  }

  majoritySelect.addEventListener("change", function (e) {
    selectedMajority = e.target.value;
    render();
  });

  bloqueSelect.addEventListener("change", function (e) {
    selectedBloque = e.target.value;
    render();
  });

  document.querySelector("#herr-vista-votacion .bulk-actions").addEventListener("click", function (e) {
    var action = e.target.getAttribute("data-action");
    if (action === "all-positive") bulkAll("positive");
    if (action === "all-negative") bulkAll("negative");
    if (action === "all-clear") bulkAll("pending");
  });

  document.querySelector("#herr-vista-votacion .roster-actions").addEventListener("click", function (e) {
    var action = e.target.getAttribute("data-action");
    if (action === "bloc-positive") bulkFiltered("positive");
    if (action === "bloc-negative") bulkFiltered("negative");
    if (action === "bloc-clear") bulkFiltered("pending");
  });

  undoBtn.addEventListener("click", undo);

  searchInput.addEventListener("input", function (e) {
    searchQuery = e.target.value;
    render();
  });

  function escapeHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function renderPrintView() {
    var data = getReportData();

    var resultHtml = data.resultLine
      ? '<div class="pv-result">' + escapeHtml(data.resultLine) + "</div>"
      : "";

    var bloqueSummary = {};
    SENATORS.forEach(function (s) {
      var v = votes[s.banca - 1];
      if (!bloqueSummary[s.bloque]) bloqueSummary[s.bloque] = { positive: 0, negative: 0, abstention: 0, absent: 0, pending: 0 };
      bloqueSummary[s.bloque][v]++;
    });
    var bloqueRows = Object.keys(bloqueSummary).sort(function (a, b) { return a.localeCompare(b, "es"); }).map(function (b) {
      var c = bloqueSummary[b];
      return "<tr>" +
        "<td>" + escapeHtml(b) + "</td>" +
        "<td>" + c.positive + "</td>" +
        "<td>" + c.negative + "</td>" +
        "<td>" + c.abstention + "</td>" +
        "<td>" + c.absent + "</td>" +
        "<td>" + c.pending + "</td>" +
        "</tr>";
    }).join("");

    var legendHtml = '<div class="pv-legend">' +
      VOTE_ORDER.filter(function (v) { return v !== "pending"; }).map(function (v) {
        return '<span class="pv-legend-item"><span class="pv-legend-dot" style="background:' + VOTE_FILL[v] + '"></span>' + VOTE_LABEL[v] + "</span>";
      }).join("") +
      "</div>";

    printView.innerHTML =
      '<div class="pv-toolbar no-print">' +
        '<button id="printNowBtn" class="btn-brass">Imprimir / Guardar como PDF</button>' +
        '<button id="printBackBtn" class="btn-neutral">Volver al tablero</button>' +
        '<p class="pv-hint">Se va a abrir el diálogo de impresión del navegador. Elegí <strong>“Guardar como PDF”</strong> como destino.</p>' +
      "</div>" +
      "<h1>Tablero de Votación — Senado de la Nación</h1>" +
      '<div class="pv-meta">Generado el ' + escapeHtml(data.fecha) + " · Mayoría requerida: " + escapeHtml(data.majorityLabel) + "</div>" +
      resultHtml +
      '<div class="pv-tally">' +
        "<span>Afirmativos: " + data.positive + "</span>" +
        "<span>Negativos: " + data.negative + "</span>" +
        "<span>Abstenciones: " + data.abstention + "</span>" +
        "<span>Ausentes: " + data.absent + "</span>" +
        "<span>Pendientes: " + data.pending + "</span>" +
      "</div>" +
      '<div class="pv-chamber-wrap">' +
        '<div id="pvChamberSlot" class="pv-chamber-bg"></div>' +
        legendHtml +
      "</div>" +
      '<table class="pv-bloque-table">' +
        "<thead><tr><th>Bloque</th><th>Afirm.</th><th>Neg.</th><th>Abst.</th><th>Aus.</th><th>Pend.</th></tr></thead>" +
        "<tbody>" + bloqueRows + "</tbody>" +
      "</table>";

    var chamberSnapshot = chamber.cloneNode(true);
    chamberSnapshot.removeAttribute("id");
    chamberSnapshot.setAttribute("class", "pv-chamber");
    // clipPath ids se clonan iguales a los del #chamber original (que sigue en
    // el DOM detrás del printView) -> con el id duplicado en el documento, el
    // navegador puede no resolver bien url(#clip-seat-N) y la foto queda sin
    // recortar (se ve el rectángulo completo detrás del círculo). Se renombran
    // acá, por seat, para que sean únicos.
    Array.prototype.forEach.call(chamberSnapshot.querySelectorAll(".seat"), function (g) {
      g.style.opacity = "1";
      g.removeAttribute("class"); // sin :hover/click en el PDF
      var highlight = g.querySelector(".seat-highlight");
      if (highlight) highlight.setAttribute("stroke", "none");
      var id = g.getAttribute("data-id");
      var clipPath = chamberSnapshot.querySelector('clipPath[id="clip-seat-' + id + '"]');
      var image = g.querySelector("image");
      if (clipPath && image) {
        var newClipId = "pv-clip-seat-" + id;
        clipPath.id = newClipId;
        image.setAttribute("clip-path", "url(#" + newClipId + ")");
      }
    });
    document.getElementById("pvChamberSlot").appendChild(chamberSnapshot);

    document.getElementById("printNowBtn").addEventListener("click", function () {
      window.print();
    });
    document.getElementById("printBackBtn").addEventListener("click", closePrintView);
  }

  function openPrintView() {
    renderPrintView();
    document.body.classList.add("print-view-active");
    printView.hidden = false;
    if (printView.scrollIntoView) printView.scrollIntoView({ block: "start" });
  }

  function closePrintView() {
    document.body.classList.remove("print-view-active");
    printView.hidden = true;
  }

  downloadPdfBtn.addEventListener("click", openPrintView);

  // ---- Persistencia local (localStorage) ----

  var STATE_KEY = "senadoVotacion.state.v1";
  var SCENARIOS_KEY = "senadoVotacion.scenarios.v1";
  var activeScenarioId = null;
  var storageAvailable = true;
  try {
    var testKey = "__senadoVotacion_test__";
    window.localStorage.setItem(testKey, "1");
    window.localStorage.removeItem(testKey);
  } catch (e) {
    storageAvailable = false;
  }

  function saveState() {
    if (!storageAvailable) return;
    try {
      window.localStorage.setItem(STATE_KEY, JSON.stringify({
        votes: votes,
        selectedMajority: selectedMajority,
        selectedBloque: selectedBloque,
        activeScenarioId: activeScenarioId
      }));
    } catch (e) { /* almacenamiento lleno o bloqueado: se ignora */ }
  }

  function loadState() {
    if (!storageAvailable) return;
    try {
      var raw = window.localStorage.getItem(STATE_KEY);
      if (!raw) return;
      var saved = JSON.parse(raw);
      if (Array.isArray(saved.votes) && saved.votes.length === SENATORS.length) {
        votes = saved.votes;
      }
      if (saved.selectedMajority) selectedMajority = saved.selectedMajority;
      if (saved.selectedBloque) selectedBloque = saved.selectedBloque;
      if (saved.activeScenarioId) activeScenarioId = saved.activeScenarioId;
    } catch (e) { /* estado guardado corrupto: se ignora */ }
  }

  function getScenarios() {
    if (!storageAvailable) return [];
    try {
      var raw = window.localStorage.getItem(SCENARIOS_KEY);
      return raw ? JSON.parse(raw) : [];
    } catch (e) { return []; }
  }

  function saveScenarios(list) {
    if (!storageAvailable) return;
    try { window.localStorage.setItem(SCENARIOS_KEY, JSON.stringify(list)); } catch (e) { /* ignorar */ }
  }

  function renderScenarioSelect() {
    var scenarios = getScenarios();
    scenarioSelect.innerHTML = "";
    var blank = document.createElement("option");
    blank.value = "";
    blank.textContent = scenarios.length ? "Sin escenario (trabajo actual)" : "No hay escenarios guardados";
    scenarioSelect.appendChild(blank);
    scenarios.forEach(function (sc) {
      var opt = document.createElement("option");
      opt.value = sc.id;
      opt.textContent = sc.name;
      scenarioSelect.appendChild(opt);
    });
    scenarioSelect.value = activeScenarioId || "";
    updateScenarioStatus();
  }

  function updateScenarioStatus() {
    if (!activeScenarioId) {
      scenarioStatus.textContent = "Trabajando sin guardar en un escenario. Los votos igual se conservan en este navegador.";
      deleteScenarioBtn.disabled = true;
      return;
    }
    var scenarios = getScenarios();
    var sc = scenarios.filter(function (s) { return s.id === activeScenarioId; })[0];
    deleteScenarioBtn.disabled = !sc;
    if (sc) {
      var d = new Date(sc.updatedAt);
      scenarioStatus.textContent = "Escenario “" + sc.name + "” · guardado " + d.toLocaleDateString("es-AR") + " " + d.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });
    }
  }

  function createScenario(name) {
    var scenarios = getScenarios();
    var scenario = {
      id: Date.now().toString(36) + Math.random().toString(36).slice(2, 6),
      name: name,
      votes: votes.slice(),
      selectedMajority: selectedMajority,
      updatedAt: Date.now()
    };
    scenarios.push(scenario);
    saveScenarios(scenarios);
    activeScenarioId = scenario.id;
    renderScenarioSelect();
    saveState();
  }

  function updateActiveScenario() {
    if (!activeScenarioId) return;
    var scenarios = getScenarios();
    var sc = scenarios.filter(function (s) { return s.id === activeScenarioId; })[0];
    if (!sc) return;
    sc.votes = votes.slice();
    sc.selectedMajority = selectedMajority;
    sc.updatedAt = Date.now();
    saveScenarios(scenarios);
    renderScenarioSelect();
    saveState();
  }

  function loadScenario(id) {
    var scenarios = getScenarios();
    var sc = scenarios.filter(function (s) { return s.id === id; })[0];
    if (!sc) {
      activeScenarioId = null;
      renderScenarioSelect();
      return;
    }
    pushHistory();
    votes = sc.votes.slice();
    selectedMajority = sc.selectedMajority || selectedMajority;
    majoritySelect.value = selectedMajority;
    activeScenarioId = id;
    render();
    renderScenarioSelect();
    saveState();
  }

  function deleteScenario(id) {
    var scenarios = getScenarios().filter(function (s) { return s.id !== id; });
    saveScenarios(scenarios);
    if (activeScenarioId === id) activeScenarioId = null;
    renderScenarioSelect();
    saveState();
  }

  scenarioSelect.addEventListener("change", function (e) {
    var id = e.target.value;
    if (id) {
      loadScenario(id);
    } else {
      activeScenarioId = null;
      renderScenarioSelect();
      saveState();
    }
  });

  newScenarioBtn.addEventListener("click", function () {
    var name = window.prompt("Nombre para el nuevo escenario:", "");
    if (name && name.trim()) createScenario(name.trim());
  });

  saveScenarioBtn.addEventListener("click", function () {
    if (activeScenarioId) {
      updateActiveScenario();
    } else {
      var name = window.prompt("Nombre para guardar este escenario:", "");
      if (name && name.trim()) createScenario(name.trim());
    }
  });

  deleteScenarioBtn.addEventListener("click", function () {
    if (!activeScenarioId) return;
    var scenarios = getScenarios();
    var sc = scenarios.filter(function (s) { return s.id === activeScenarioId; })[0];
    var ok = window.confirm("¿Eliminar el escenario \"" + (sc ? sc.name : "") + "\"? Esta acción no se puede deshacer.");
    if (ok) deleteScenario(activeScenarioId);
  });

  loadState();
  majoritySelect.value = selectedMajority;
  bloqueSelect.value = selectedBloque;
  renderScenarioSelect();

  buildChamber();
  render();
})();

/* ── Contador de Quórum (subtab de Herramientas para sesión) ──────────── */
(function () {
  "use strict";

  var DATA = window.__SENADO_DATA__ || { SENATORS: [], PHOTOS: {} };
  var SENATORS = DATA.SENATORS;
  var PHOTOS = DATA.PHOTOS;

  var Q_ORDER = ["pending", "presente", "ausente"];
  var Q_FILL = {
    pending: "var(--vote-pending-fill)",
    presente: "var(--vote-positive)",
    ausente: "var(--vote-negative)"
  };

  var qstates = SENATORS.map(function () { return "pending"; });
  var qSelectedBloque = "TODOS";
  var qSearchQuery = "";

  var qBloqueSelect = document.getElementById("qBloqueSelect");
  var qSearchInput = document.getElementById("qSearchInput");
  var qResultBox = document.getElementById("qResultBox");
  var qChamber = document.getElementById("qChamber");
  var qTooltip = document.getElementById("qTooltip");
  var qRosterPanel = document.getElementById("qRosterPanel");
  var qRosterLabel = document.getElementById("qRosterLabel");
  var qRosterGrid = document.getElementById("qRosterGrid");
  var qDownloadPdfBtn = document.getElementById("qDownloadPdfBtn");
  var quorumPrintView = document.getElementById("quorumPrintView");
  var qUndoBtn = document.getElementById("qUndoBtn");

  var QUORUM_NEEDED = Math.floor(SENATORS.length / 2) + 1;
  var qNeededEl = document.getElementById("qQuorumNeeded");
  if (qNeededEl) qNeededEl.textContent = String(QUORUM_NEEDED);

  function qNormalizeText(str) {
    return String(str).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
  }
  function qMatchesFilters(sen) {
    var bloqueOk = qSelectedBloque === "TODOS" || sen.bloque === qSelectedBloque;
    var q = qSearchQuery.trim();
    var searchOk = q === "" || qNormalizeText(sen.nombre).indexOf(qNormalizeText(q)) !== -1;
    return bloqueOk && searchOk;
  }

  var qBloques = Array.from(new Set(SENATORS.map(function (s) { return s.bloque; })))
    .sort(function (a, b) { return a.localeCompare(b, "es"); });
  var qAllOpt = document.createElement("option");
  qAllOpt.value = "TODOS";
  qAllOpt.textContent = "Filtrar por bloque (todos)";
  qBloqueSelect.appendChild(qAllOpt);
  qBloques.forEach(function (b) {
    var el = document.createElement("option");
    el.value = b;
    el.textContent = b + " (" + SENATORS.filter(function (s) { return s.bloque === b; }).length + ")";
    qBloqueSelect.appendChild(el);
  });

  var qSeats = SENATORS.map(function (s) { return { id: s.banca, x: s.x, y: s.y }; });
  var Q_SEAT_RADIUS = 16;
  var svgns = "http://www.w3.org/2000/svg";

  function qBuildChamber() {
    qChamber.innerHTML = "";

    var dais = document.createElementNS(svgns, "rect");
    dais.setAttribute("x", "355");
    dais.setAttribute("y", "400");
    dais.setAttribute("width", "90");
    dais.setAttribute("height", "34");
    dais.setAttribute("rx", "4");
    dais.setAttribute("class", "dais");
    qChamber.appendChild(dais);

    var daisLabel = document.createElementNS(svgns, "text");
    daisLabel.setAttribute("x", "400");
    daisLabel.setAttribute("y", "421");
    daisLabel.setAttribute("text-anchor", "middle");
    daisLabel.setAttribute("class", "dais-label");
    daisLabel.textContent = "PRESIDENCIA";
    qChamber.appendChild(daisLabel);

    var defs = document.createElementNS(svgns, "defs");
    qChamber.appendChild(defs);

    qSeats.forEach(function (seat) {
      var g = document.createElementNS(svgns, "g");
      g.setAttribute("class", "seat");
      g.setAttribute("data-id", seat.id);

      var clipId = "q-clip-seat-" + seat.id;
      var clipPath = document.createElementNS(svgns, "clipPath");
      clipPath.setAttribute("id", clipId);
      var clipCircle = document.createElementNS(svgns, "circle");
      clipCircle.setAttribute("cx", seat.x);
      clipCircle.setAttribute("cy", seat.y);
      clipCircle.setAttribute("r", Q_SEAT_RADIUS - 2);
      clipPath.appendChild(clipCircle);
      defs.appendChild(clipPath);

      var photoBg = document.createElementNS(svgns, "circle");
      photoBg.setAttribute("cx", seat.x);
      photoBg.setAttribute("cy", seat.y);
      photoBg.setAttribute("r", Q_SEAT_RADIUS - 2);
      photoBg.setAttribute("fill", "#cfd8e0");
      g.appendChild(photoBg);

      var photo = document.createElementNS(svgns, "image");
      photo.setAttributeNS("http://www.w3.org/1999/xlink", "href", PHOTOS[seat.id]);
      photo.setAttribute("href", PHOTOS[seat.id]);
      photo.setAttribute("x", seat.x - (Q_SEAT_RADIUS - 2));
      photo.setAttribute("y", seat.y - (Q_SEAT_RADIUS - 2));
      photo.setAttribute("width", (Q_SEAT_RADIUS - 2) * 2);
      photo.setAttribute("height", (Q_SEAT_RADIUS - 2) * 2);
      photo.setAttribute("clip-path", "url(#" + clipId + ")");
      photo.setAttribute("preserveAspectRatio", "xMidYMid slice");
      g.appendChild(photo);

      var highlight = document.createElementNS(svgns, "circle");
      highlight.setAttribute("cx", seat.x);
      highlight.setAttribute("cy", seat.y);
      highlight.setAttribute("r", Q_SEAT_RADIUS + 3.5);
      highlight.setAttribute("class", "seat-highlight");
      highlight.setAttribute("fill", "none");
      g.appendChild(highlight);

      var ring = document.createElementNS(svgns, "circle");
      ring.setAttribute("cx", seat.x);
      ring.setAttribute("cy", seat.y);
      ring.setAttribute("r", Q_SEAT_RADIUS);
      ring.setAttribute("class", "seat-ring");
      ring.setAttribute("fill", "none");
      g.appendChild(ring);

      var badge = document.createElementNS(svgns, "circle");
      badge.setAttribute("cx", seat.x + Q_SEAT_RADIUS * 0.72);
      badge.setAttribute("cy", seat.y + Q_SEAT_RADIUS * 0.72);
      badge.setAttribute("r", 6.5);
      badge.setAttribute("class", "seat-badge");
      g.appendChild(badge);

      var badgeText = document.createElementNS(svgns, "text");
      badgeText.setAttribute("x", seat.x + Q_SEAT_RADIUS * 0.72);
      badgeText.setAttribute("y", seat.y + Q_SEAT_RADIUS * 0.72 + 0.5);
      badgeText.setAttribute("text-anchor", "middle");
      badgeText.setAttribute("dominant-baseline", "middle");
      badgeText.setAttribute("class", "seat-badge-text");
      badgeText.textContent = seat.id;
      g.appendChild(badgeText);

      g.addEventListener("click", function () { qCycle(seat.id); });
      g.addEventListener("mouseenter", function () { qShowTooltip(seat.id); });
      g.addEventListener("mouseleave", qHideTooltip);

      qChamber.appendChild(g);
    });
  }

  function qShowTooltip(id) {
    var sen = SENATORS[id - 1];
    qTooltip.innerHTML =
      '<div class="name">' + sen.nombre + '</div>' +
      '<div class="bloque">' + sen.bloque + '</div>' +
      '<div class="prov">' + sen.provincia + '</div>';
    qTooltip.hidden = false;
  }
  function qHideTooltip() { qTooltip.hidden = true; }

  var Q_HISTORY_LIMIT = 30;
  var qHistory = [];
  function qPushHistory() {
    qHistory.push(qstates.slice());
    if (qHistory.length > Q_HISTORY_LIMIT) qHistory.shift();
    qUndoBtn.disabled = false;
  }
  function qUndo() {
    if (qHistory.length === 0) return;
    qstates = qHistory.pop();
    qUndoBtn.disabled = qHistory.length === 0;
    qRender();
    qSaveState();
  }
  function qCycle(id) {
    qPushHistory();
    var idx = id - 1;
    var current = Q_ORDER.indexOf(qstates[idx]);
    qstates[idx] = Q_ORDER[(current + 1) % Q_ORDER.length];
    qRender();
    qSaveState();
  }
  function qSetVote(id, value) { qstates[id - 1] = value; }
  function qBulkAll(value) {
    qPushHistory();
    qstates = qstates.map(function () { return value; });
    qRender();
    qSaveState();
  }
  function qBulkFiltered(value) {
    qPushHistory();
    SENATORS.filter(qMatchesFilters).forEach(function (s) { qSetVote(s.banca, value); });
    qRender();
    qSaveState();
  }

  function qRender() {
    Array.prototype.forEach.call(qChamber.querySelectorAll(".seat"), function (g) {
      var id = Number(g.getAttribute("data-id"));
      var sen = SENATORS[id - 1];
      var v = qstates[id - 1];
      var matches = qMatchesFilters(sen);
      var filtersActive = qSelectedBloque !== "TODOS" || qSearchQuery.trim() !== "";
      g.style.opacity = matches ? "1" : "0.25";

      var ring = g.querySelector(".seat-ring");
      ring.setAttribute("stroke", Q_FILL[v]);
      ring.setAttribute("stroke-width", v === "pending" ? "2" : "3.5");

      var highlight = g.querySelector(".seat-highlight");
      if (filtersActive && matches) {
        highlight.setAttribute("stroke", "var(--brass-strong)");
        highlight.setAttribute("stroke-width", "2.5");
      } else {
        highlight.setAttribute("stroke", "none");
      }
    });

    var presente = qstates.filter(function (v) { return v === "presente"; }).length;
    var ausente = qstates.filter(function (v) { return v === "ausente"; }).length;
    var pending = qstates.filter(function (v) { return v === "pending"; }).length;
    document.getElementById("qTotalPresente").textContent = presente;
    document.getElementById("qTotalAusente").textContent = ausente;
    document.getElementById("qTotalPendiente").textContent = pending;

    var alcanzado = presente >= QUORUM_NEEDED;
    qResultBox.hidden = false;
    qResultBox.className = "result " + (alcanzado ? "approved" : "rejected");
    qResultBox.innerHTML = (alcanzado ? "✓ Quórum alcanzado — " : "✗ Quórum no alcanzado — ") +
      '<span class="detail">' + presente + " de " + QUORUM_NEEDED + " senadores necesarios</span>";

    qRenderRoster();
  }

  function qRenderRoster() {
    var filtersActive = qSelectedBloque !== "TODOS" || qSearchQuery.trim() !== "";
    if (!filtersActive) { qRosterPanel.hidden = true; return; }
    qRosterPanel.hidden = false;
    var miembros = SENATORS.filter(qMatchesFilters).sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); });
    var label = qSelectedBloque !== "TODOS" ? qSelectedBloque : "Resultados de búsqueda";
    if (miembros.length === 0) label = "Sin resultados";
    qRosterLabel.innerHTML = label + ' <span class="count">(' + miembros.length + " senadores)</span>";
    qRosterGrid.innerHTML = "";
    miembros.forEach(function (s) {
      var btn = document.createElement("button");
      btn.className = "roster-item";
      btn.innerHTML =
        '<span class="dot" style="background:' + Q_FILL[qstates[s.banca - 1]] + '"></span>' +
        '<span class="who"><div class="n">' + s.nombre + '</div><div class="p">' + s.provincia + '</div></span>';
      btn.addEventListener("click", function () { qCycle(s.banca); });
      btn.addEventListener("mouseenter", function () { qShowTooltip(s.banca); });
      btn.addEventListener("mouseleave", qHideTooltip);
      qRosterGrid.appendChild(btn);
    });
  }

  function qEscapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  var Q_STATE_KEY = "senadoQuorum.state.v1";
  var qStorageAvailable = true;
  try {
    var qTestKey = "__senadoQuorum_test__";
    window.localStorage.setItem(qTestKey, "1");
    window.localStorage.removeItem(qTestKey);
  } catch (e) { qStorageAvailable = false; }

  function qSaveState() {
    if (!qStorageAvailable) return;
    try { window.localStorage.setItem(Q_STATE_KEY, JSON.stringify({ qstates: qstates })); } catch (e) {}
  }
  function qLoadState() {
    if (!qStorageAvailable) return;
    try {
      var raw = window.localStorage.getItem(Q_STATE_KEY);
      if (!raw) return;
      var saved = JSON.parse(raw);
      if (saved && Array.isArray(saved.qstates) && saved.qstates.length === SENATORS.length) {
        qstates = saved.qstates;
      }
    } catch (e) {}
  }

  function qRenderPrintView() {
    var presente = qstates.filter(function (v) { return v === "presente"; }).length;
    var ausente = qstates.filter(function (v) { return v === "ausente"; }).length;
    var pending = qstates.filter(function (v) { return v === "pending"; }).length;
    var alcanzado = presente >= QUORUM_NEEDED;
    var now = new Date();
    var fecha = now.toLocaleDateString("es-AR") + " " + now.toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit" });

    var bloqueSummary = {};
    SENATORS.forEach(function (s) {
      var v = qstates[s.banca - 1];
      if (!bloqueSummary[s.bloque]) bloqueSummary[s.bloque] = { presente: 0, ausente: 0, pending: 0 };
      bloqueSummary[s.bloque][v]++;
    });
    var bloqueRows = Object.keys(bloqueSummary).sort(function (a, b) { return a.localeCompare(b, "es"); }).map(function (b) {
      var c = bloqueSummary[b];
      return "<tr><td>" + qEscapeHtml(b) + "</td><td>" + c.presente + "</td><td>" + c.ausente + "</td><td>" + c.pending + "</td></tr>";
    }).join("");

    var ausentesRows = SENATORS.filter(function (s) { return qstates[s.banca - 1] === "ausente"; })
      .sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); })
      .map(function (s) { return "<tr><td>" + qEscapeHtml(s.nombre) + "</td><td>" + qEscapeHtml(s.bloque) + "</td><td>" + qEscapeHtml(s.provincia) + "</td></tr>"; })
      .join("");

    quorumPrintView.innerHTML =
      '<div class="pv-toolbar no-print">' +
        '<button id="qPrintNowBtn" class="btn-brass">Imprimir / Guardar como PDF</button>' +
        '<button id="qPrintBackBtn" class="btn-neutral">Volver al contador</button>' +
        '<p class="pv-hint">Se va a abrir el diálogo de impresión del navegador. Elegí <strong>“Guardar como PDF”</strong> como destino.</p>' +
      "</div>" +
      "<h1>Registro de Quórum — Senado de la Nación</h1>" +
      '<div class="pv-meta">Generado el ' + qEscapeHtml(fecha) + "</div>" +
      '<div class="pv-result">' + (alcanzado ? "QUÓRUM ALCANZADO" : "QUÓRUM NO ALCANZADO") + " (" + presente + " de " + QUORUM_NEEDED + " necesarios)</div>" +
      '<div class="pv-tally"><span>Presentes: ' + presente + '</span><span>Ausentes: ' + ausente + '</span><span>Pendientes: ' + pending + '</span></div>' +
      '<div class="pv-chamber-wrap"><div id="qPvChamberSlot" class="pv-chamber-bg"></div></div>' +
      '<table class="pv-bloque-table"><thead><tr><th>Bloque</th><th>Presentes</th><th>Ausentes</th><th>Pend.</th></tr></thead><tbody>' + bloqueRows + '</tbody></table>' +
      '<h2 class="pv-subheading">Senadores ausentes</h2>' +
      '<table class="pv-bloque-table"><thead><tr><th>Senador</th><th>Bloque</th><th>Provincia</th></tr></thead><tbody>' + (ausentesRows || '<tr><td colspan="3">—</td></tr>') + '</tbody></table>';

    var chamberSnapshot = qChamber.cloneNode(true);
    chamberSnapshot.removeAttribute("id");
    chamberSnapshot.setAttribute("class", "pv-chamber");
    Array.prototype.forEach.call(chamberSnapshot.querySelectorAll(".seat"), function (g) {
      g.style.opacity = "1";
      g.removeAttribute("class");
      var highlight = g.querySelector(".seat-highlight");
      if (highlight) highlight.setAttribute("stroke", "none");
      var id = g.getAttribute("data-id");
      var clipPath = chamberSnapshot.querySelector('clipPath[id="q-clip-seat-' + id + '"]');
      var image = g.querySelector("image");
      if (clipPath && image) {
        var newClipId = "q-pv-clip-seat-" + id;
        clipPath.id = newClipId;
        image.setAttribute("clip-path", "url(#" + newClipId + ")");
      }
    });
    document.getElementById("qPvChamberSlot").appendChild(chamberSnapshot);

    document.getElementById("qPrintNowBtn").addEventListener("click", function () { window.print(); });
    document.getElementById("qPrintBackBtn").addEventListener("click", qClosePrintView);
  }

  function qOpenPrintView() {
    qRenderPrintView();
    document.body.classList.add("print-view-active");
    quorumPrintView.hidden = false;
    if (quorumPrintView.scrollIntoView) quorumPrintView.scrollIntoView({ block: "start" });
  }
  function qClosePrintView() {
    document.body.classList.remove("print-view-active");
    quorumPrintView.hidden = true;
  }

  qDownloadPdfBtn.addEventListener("click", qOpenPrintView);
  qBloqueSelect.addEventListener("change", function (e) { qSelectedBloque = e.target.value; qRender(); });
  qSearchInput.addEventListener("input", function (e) { qSearchQuery = e.target.value; qRender(); });
  document.querySelector("#herr-vista-quorum .bulk-actions").addEventListener("click", function (e) {
    var action = e.target.getAttribute("data-action");
    if (action === "all-presente") qBulkAll("presente");
    if (action === "all-ausente") qBulkAll("ausente");
    if (action === "all-clear") qBulkAll("pending");
  });
  document.querySelector("#herr-vista-quorum .roster-actions").addEventListener("click", function (e) {
    var action = e.target.getAttribute("data-action");
    if (action === "bloc-presente") qBulkFiltered("presente");
    if (action === "bloc-ausente") qBulkFiltered("ausente");
    if (action === "bloc-clear") qBulkFiltered("pending");
  });
  qUndoBtn.addEventListener("click", qUndo);

  qLoadState();
  qBloqueSelect.value = qSelectedBloque;
  qBuildChamber();
  qRender();
})();

/* ── Cálculo de 2/3 (subtab de Herramientas para sesión) ──────────────── */
(function () {
  "use strict";
  var dtTotal = document.getElementById("dtTotal");
  var dtResultNum = document.getElementById("dtResultNum");
  var dtResultTotal = document.getElementById("dtResultTotal");
  if (!dtTotal) return;

  function dtRecalc() {
    var raw = parseInt(dtTotal.value, 10);
    if (isNaN(raw) || raw < 1) raw = 1;
    if (raw > 72) raw = 72;
    dtTotal.value = raw;
    var need = Math.ceil(raw * 2 / 3);
    dtResultNum.textContent = need;
    dtResultTotal.textContent = raw;
  }
  dtTotal.addEventListener("input", dtRecalc);
  dtTotal.addEventListener("change", dtRecalc);
  dtRecalc();
})();

/* ── Cálculo de Tiempos de oradores (subtab de Herramientas para sesión) */
(function () {
  "use strict";

  var DATA = window.__SENADO_DATA__ || { SENATORS: [] };
  var SENATORS = DATA.SENATORS.slice().sort(function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); });

  var temaSelect = document.getElementById("temaSelect");
  var newTemaBtn = document.getElementById("newTemaBtn");
  var renameTemaBtn = document.getElementById("renameTemaBtn");
  var deleteTemaBtn = document.getElementById("deleteTemaBtn");
  var horaInicioInput = document.getElementById("horaInicioInput");
  var horaFinEstimada = document.getElementById("horaFinEstimada");
  var oradorSelect = document.getElementById("oradorSelect");
  var oradorMinutos = document.getElementById("oradorMinutos");
  var addOradorBtn = document.getElementById("addOradorBtn");
  var oradoresList = document.getElementById("oradoresList");
  var importPdfBtn = document.getElementById("importPdfBtn");
  var oradoresPdfInput = document.getElementById("oradoresPdfInput");
  var importPdfStatus = document.getElementById("importPdfStatus");
  if (!temaSelect) return;

  var TIEMPOS_KEY = "senadoTiempos.state.v1";
  var temas = [];
  var activeTemaId = null;
  var dragIndex = null;

  function uid() { return "t" + Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
  function defaultTema(n) { return { id: uid(), nombre: "Tema " + n, horaInicio: "", oradores: [] }; }
  function getActiveTema() { return temas.filter(function (t) { return t.id === activeTemaId; })[0] || null; }

  function saveState() {
    try { window.localStorage.setItem(TIEMPOS_KEY, JSON.stringify({ temas: temas, activeTemaId: activeTemaId })); } catch (e) {}
  }
  function loadState() {
    try {
      var raw = window.localStorage.getItem(TIEMPOS_KEY);
      if (raw) {
        var saved = JSON.parse(raw);
        if (saved && Array.isArray(saved.temas) && saved.temas.length) {
          temas = saved.temas;
          activeTemaId = saved.activeTemaId;
          if (!getActiveTema()) activeTemaId = temas[0].id;
          return;
        }
      }
    } catch (e) {}
    temas = [defaultTema(1)];
    activeTemaId = temas[0].id;
  }

  function renderTemaSelect() {
    temaSelect.innerHTML = "";
    temas.forEach(function (t) {
      var opt = document.createElement("option");
      opt.value = t.id;
      opt.textContent = t.nombre;
      if (t.id === activeTemaId) opt.selected = true;
      temaSelect.appendChild(opt);
    });
  }

  function fillOradorSelect() {
    oradorSelect.innerHTML = "";
    SENATORS.forEach(function (s) {
      var opt = document.createElement("option");
      opt.value = s.banca;
      opt.textContent = s.nombre + " (" + s.bloque + ")";
      oradorSelect.appendChild(opt);
    });
  }

  function parseHora(hhmm) {
    if (!hhmm) return null;
    var parts = hhmm.split(":");
    if (parts.length !== 2) return null;
    var h = parseInt(parts[0], 10), m = parseInt(parts[1], 10);
    if (isNaN(h) || isNaN(m)) return null;
    return h * 60 + m;
  }
  function formatHora(mins) {
    mins = ((mins % 1440) + 1440) % 1440;
    var h = Math.floor(mins / 60), m = mins % 60;
    return (h < 10 ? "0" : "") + h + ":" + (m < 10 ? "0" : "") + m;
  }
  function escapeHtml(str) {
    return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function render() {
    var tema = getActiveTema();
    if (!tema) return;
    horaInicioInput.value = tema.horaInicio || "";

    var startMin = parseHora(tema.horaInicio);
    var cursor = startMin;
    oradoresList.innerHTML = "";

    tema.oradores.forEach(function (o, idx) {
      var inicio = null, fin = null;
      if (o.estado !== "no_habla" && cursor !== null) {
        inicio = cursor;
        fin = cursor + (parseInt(o.minutos, 10) || 0);
        cursor = fin;
      }
      var row = document.createElement("div");
      row.className = "orador-row" + (o.estado === "hablo" ? " is-hablo" : "") + (o.estado === "no_habla" ? " is-no-habla" : "");
      row.setAttribute("draggable", "true");
      row.setAttribute("data-idx", idx);

      row.innerHTML =
        '<span class="orador-drag" title="Arrastrar para reordenar">⠿</span>' +
        '<span class="orador-orden">' + (idx + 1) + '</span>' +
        '<span class="orador-nombre"><div class="n">' + escapeHtml(o.senadorNombre) + '</div><div class="b">' + escapeHtml(o.bloque) + '</div></span>' +
        '<span class="orador-minutos"><input type="number" min="1" max="120" value="' + o.minutos + '" data-idx="' + idx + '" class="orador-minutos-input"> min</span>' +
        '<span class="orador-horario">' + (inicio !== null ? formatHora(inicio) + '–' + formatHora(fin) : '—') + '</span>' +
        '<span class="orador-estado">' +
          '<button class="orador-check' + (o.estado === "hablo" ? " on" : "") + '" data-idx="' + idx + '" data-action="hablo" title="Ya habló">✓</button>' +
          '<button class="orador-cross' + (o.estado === "no_habla" ? " on" : "") + '" data-idx="' + idx + '" data-action="no_habla" title="No va a hablar">✕</button>' +
        '</span>' +
        '<button class="orador-remove" data-idx="' + idx + '" title="Quitar">🗑</button>';

      oradoresList.appendChild(row);
    });

    horaFinEstimada.textContent = (startMin !== null && tema.oradores.length) ? formatHora(cursor) : "—";
  }

  function addOrador() {
    var tema = getActiveTema();
    if (!tema) return;
    var banca = parseInt(oradorSelect.value, 10);
    var sen = SENATORS.filter(function (s) { return s.banca === banca; })[0];
    if (!sen) return;
    var minutos = parseInt(oradorMinutos.value, 10);
    if (isNaN(minutos) || minutos < 1) minutos = 1;
    tema.oradores.push({ senadorNombre: sen.nombre, bloque: sen.bloque, minutos: minutos, estado: "pendiente" });
    render();
    saveState();
  }

  addOradorBtn.addEventListener("click", addOrador);

  horaInicioInput.addEventListener("change", function () {
    var tema = getActiveTema();
    if (!tema) return;
    tema.horaInicio = horaInicioInput.value;
    render();
    saveState();
  });

  oradoresList.addEventListener("click", function (e) {
    var tema = getActiveTema();
    if (!tema) return;
    var btn = e.target.closest("button");
    if (!btn) return;
    var idx = parseInt(btn.getAttribute("data-idx"), 10);
    if (btn.classList.contains("orador-remove")) {
      tema.oradores.splice(idx, 1);
    } else {
      var action = btn.getAttribute("data-action");
      var o = tema.oradores[idx];
      if (!o) return;
      o.estado = (o.estado === action) ? "pendiente" : action;
    }
    render();
    saveState();
  });

  oradoresList.addEventListener("input", function (e) {
    if (!e.target.classList.contains("orador-minutos-input")) return;
    var tema = getActiveTema();
    if (!tema) return;
    var idx = parseInt(e.target.getAttribute("data-idx"), 10);
    var v = parseInt(e.target.value, 10);
    if (isNaN(v) || v < 1) v = 1;
    tema.oradores[idx].minutos = v;
    render();
    saveState();
  });

  oradoresList.addEventListener("dragstart", function (e) {
    var row = e.target.closest(".orador-row");
    if (!row) return;
    dragIndex = parseInt(row.getAttribute("data-idx"), 10);
    e.dataTransfer.effectAllowed = "move";
    row.classList.add("dragging");
  });
  oradoresList.addEventListener("dragend", function (e) {
    var row = e.target.closest(".orador-row");
    if (row) row.classList.remove("dragging");
  });
  oradoresList.addEventListener("dragover", function (e) {
    e.preventDefault();
    var row = e.target.closest(".orador-row");
    if (!row) return;
    e.dataTransfer.dropEffect = "move";
  });
  oradoresList.addEventListener("drop", function (e) {
    e.preventDefault();
    var row = e.target.closest(".orador-row");
    if (!row || dragIndex === null) return;
    var dropIndex = parseInt(row.getAttribute("data-idx"), 10);
    if (dropIndex === dragIndex) return;
    var tema = getActiveTema();
    if (!tema) return;
    var moved = tema.oradores.splice(dragIndex, 1)[0];
    tema.oradores.splice(dropIndex, 0, moved);
    dragIndex = null;
    render();
    saveState();
  });

  temaSelect.addEventListener("change", function () {
    activeTemaId = temaSelect.value;
    render();
    saveState();
  });

  newTemaBtn.addEventListener("click", function () {
    var name = window.prompt("Nombre del nuevo tema:", "Tema " + (temas.length + 1));
    if (!name || !name.trim()) return;
    var t = defaultTema(temas.length + 1);
    t.nombre = name.trim();
    temas.push(t);
    activeTemaId = t.id;
    renderTemaSelect();
    render();
    saveState();
  });

  renameTemaBtn.addEventListener("click", function () {
    var tema = getActiveTema();
    if (!tema) return;
    var name = window.prompt("Nuevo nombre para el tema:", tema.nombre);
    if (!name || !name.trim()) return;
    tema.nombre = name.trim();
    renderTemaSelect();
    saveState();
  });

  deleteTemaBtn.addEventListener("click", function () {
    if (temas.length <= 1) {
      window.alert("Debe quedar al menos un tema.");
      return;
    }
    var tema = getActiveTema();
    if (!tema) return;
    var ok = window.confirm('¿Eliminar el tema "' + tema.nombre + '"? Esta acción no se puede deshacer.');
    if (!ok) return;
    temas = temas.filter(function (t) { return t.id !== tema.id; });
    activeTemaId = temas[0].id;
    renderTemaSelect();
    render();
    saveState();
  });

  /* ── Importar lista de oradores desde PDF (planilla de Secretaría) ──── */
  function stripAccents(str) { return String(str).normalize("NFD").replace(/[̀-ͯ]/g, ""); }
  function nameTokens(str) {
    return stripAccents(str).toUpperCase().replace(/[^A-Z\s]/g, " ").split(/\s+/).filter(Boolean);
  }
  function findSenatorMatch(rawName) {
    var t = nameTokens(rawName);
    if (!t.length) return null;
    var exact = SENATORS.filter(function (s) {
      var st = nameTokens(s.nombre);
      if (st.length !== t.length) return false;
      return t.every(function (tok) { return st.indexOf(tok) !== -1; });
    });
    if (exact.length === 1) return exact[0];
    var subset = SENATORS.filter(function (s) {
      var st = nameTokens(s.nombre);
      return t.every(function (tok) { return st.indexOf(tok) !== -1; });
    });
    if (subset.length === 1) return subset[0];
    return null;
  }

  function extractPdfRows(file) {
    if (!window.pdfjsLib) return Promise.reject(new Error("pdf.js no cargó"));
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    return file.arrayBuffer().then(function (buf) {
      return window.pdfjsLib.getDocument({ data: buf }).promise;
    }).then(function (pdf) {
      var pageNums = [];
      for (var i = 1; i <= pdf.numPages; i++) pageNums.push(i);
      return pageNums.reduce(function (chain, num) {
        return chain.then(function (acc) {
          return pdf.getPage(num).then(function (page) { return page.getTextContent(); }).then(function (content) {
            var items = content.items.map(function (it) {
              return { text: (it.str || "").trim(), x: it.transform[4], y: it.transform[5] };
            }).filter(function (it) { return it.text; });
            items.sort(function (a, b) { return (b.y - a.y) || (a.x - b.x); });
            var rowsOnPage = [];
            var tol = 3;
            items.forEach(function (it) {
              var row = rowsOnPage.filter(function (r) { return Math.abs(r.y - it.y) <= tol; })[0];
              if (!row) { row = { y: it.y, items: [] }; rowsOnPage.push(row); }
              row.items.push(it);
            });
            rowsOnPage.forEach(function (r) { r.items.sort(function (a, b) { return a.x - b.x; }); });
            rowsOnPage.forEach(function (r) { acc.push(r.items.map(function (it) { return it.text; })); });
            return acc;
          });
        });
      }, Promise.resolve([]));
    }).then(function (rows) {
      var temaNombre = null;
      rows.forEach(function (texts) {
        if (temaNombre) return;
        var joined = texts.join(" ");
        var m = joined.match(/^TEMA\s*:?\s*(.+)$/i);
        if (m) temaNombre = m[1].trim();
      });
      var oradorRows = rows.filter(function (texts) {
        return texts.length >= 3 && /^\d+$/.test(texts[0]) && texts[1] !== "-";
      });
      return { temaNombre: temaNombre, rows: oradorRows };
    });
  }

  function importOradoresPdf(file) {
    importPdfStatus.textContent = "Leyendo PDF…";
    extractPdfRows(file).then(function (result) {
      if (!result.rows.length) {
        importPdfStatus.textContent = "No se encontraron oradores en el PDF.";
        return;
      }
      var tema = defaultTema(temas.length + 1);
      tema.nombre = result.temaNombre ? ("Tema: " + result.temaNombre) : tema.nombre;
      var sinMatch = 0;
      result.rows.forEach(function (texts) {
        var nombreRaw = texts[1], bloqueRaw = texts[2];
        var sen = findSenatorMatch(nombreRaw);
        if (sen) {
          tema.oradores.push({ senadorNombre: sen.nombre, bloque: sen.bloque, minutos: 5, estado: "pendiente" });
        } else {
          tema.oradores.push({ senadorNombre: nombreRaw, bloque: bloqueRaw, minutos: 5, estado: "pendiente" });
          sinMatch++;
        }
      });
      temas.push(tema);
      activeTemaId = tema.id;
      renderTemaSelect();
      render();
      saveState();
      importPdfStatus.textContent = "Importados " + tema.oradores.length + " oradores en \"" + tema.nombre + "\"" +
        (sinMatch ? " (" + sinMatch + " sin coincidencia exacta, revisar nombre/bloque)" : "") + ".";
    }).catch(function (err) {
      console.error(err);
      importPdfStatus.textContent = "Error al leer el PDF. Verificá que sea la planilla de lista de oradores.";
    });
  }

  importPdfBtn.addEventListener("click", function () { oradoresPdfInput.click(); });
  oradoresPdfInput.addEventListener("change", function (e) {
    var file = e.target.files && e.target.files[0];
    oradoresPdfInput.value = "";
    if (!file) return;
    importOradoresPdf(file);
  });

  loadState();
  fillOradorSelect();
  renderTemaSelect();
  render();
})();


"""

# ── Plantilla HTML ─────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sistema Legislativo &mdash; HSN</title>
<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 64 64'%3E%3Ccircle cx='32' cy='32' r='32' fill='%231B5EA2'/%3E%3Ctext x='32' y='42' font-family='Arial,Helvetica,sans-serif' font-size='24' font-weight='700' fill='%23ffffff' text-anchor='middle'%3EHSN%3C/text%3E%3C/svg%3E">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;700&display=swap" rel="stylesheet">
<script src="https://cdn.sheetjs.com/xlsx-0.20.3/package/dist/xlsx.full.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js"></script>
<style>{css}</style>
</head>
<body>

<div class="topbar">
  <div class="header">
    <div class="header-row">
      <span class="header-inst">Senado de la Naci&oacute;n Argentina</span>
      <span class="header-dep">Prosecretar&iacute;a Parlamentaria</span>
    </div>
    <div class="header-title">Sistema Legislativo</div>
    <div class="header-sub">&Uacute;ltima actualizaci&oacute;n: {fecha}</div>
  </div>
  <div class="main-nav">
    <button class="mtab-btn active" data-main="proyectos" onclick="switchMain('proyectos')">Proyectos</button>
    <button class="mtab-btn" data-main="comisiones" onclick="switchMain('comisiones')">Comisiones</button>
    <button class="mtab-btn" data-main="agenda" onclick="switchMain('agenda')">Agenda</button>
    <button class="mtab-btn" data-main="ayuda" onclick="switchMain('ayuda')">Ayuda Memoria</button>
    <button class="mtab-btn" data-main="sanciones" onclick="switchMain('sanciones')">Sanciones HSN</button>
    <button class="mtab-btn" data-main="pliegos" onclick="switchMain('pliegos')">Pliegos judiciales</button>
    <button class="mtab-btn" data-main="votacion" onclick="switchMain('votacion')">Herramientas para sesi&oacute;n</button>
  </div>
</div>

<!-- ====================== MAIN: PROYECTOS ====================== -->
<div id="main-proyectos" class="mtab-content active">
  <div class="sub-nav">
    <button class="sub-btn active" data-sub="buscador" onclick="switchSub('buscador')">Buscador</button>
    <button class="sub-btn" data-sub="estadisticas" onclick="switchSub('estadisticas')">Estad&iacute;sticas</button>
  </div>

  <!-- SUB: ESTADÍSTICAS (treemap + ranking + dashboard, unificado) -->
  <div id="sub-estadisticas" class="sub-content">
    <div class="section-block">
      <div class="section-header">
        <h2>Estad&iacute;sticas</h2>
        <span class="section-hint">Proyectos ingresados &middot; an&aacute;lisis pol&iacute;tico</span>
      </div>
      <div class="section-body">
        <div class="dash-toolbar">
          <span class="dash-anio-label">A&ntilde;o</span>
          <button class="dash-anio-btn on" id="dash-anio-2026" onclick="setDashAnio('2026')">2026</button>
          <button class="dash-anio-btn" id="dash-anio-2025" onclick="setDashAnio('2025')">2025</button>
          <span class="dash-cross" id="dash-cross" onclick="clearCross()" title="Quitar filtro"></span>
          <span class="dash-total" id="dash-total"></span>
        </div>
        <div class="dash-grid">
          <div class="viz-card span6">
            <div class="viz-head"><span class="viz-title">Bloques pol&iacute;ticos (Senado) &middot; clic para ver desglose por tipo</span></div>
            <div class="treemap-breadcrumb" id="treemap-breadcrumb"></div>
            <div id="viz-treemap"></div>
            <div class="viz-legend" id="treemap-legend"></div>
          </div>
          <div class="viz-card span3">
            <div class="viz-head"><span class="viz-title">Ranking bloques &times; tipo (Senado)</span></div>
            <div class="pivot-scroll" style="max-height:420px"><div id="ranking-body"></div></div>
          </div>
          <div class="viz-card span3">
            <div class="viz-head"><span class="viz-title">Tipo por bloque</span></div>
            <div id="viz-stacked"></div>
            <div class="viz-legend" id="stacked-legend"></div>
          </div>
          <div class="viz-card span2">
            <div class="viz-head">
              <span class="viz-title">Evoluci&oacute;n temporal</span>
              <div class="viz-toggle">
                <button id="evo-tipo" class="on" onclick="setEvoMode('tipo')">Por tipo</button>
                <button id="evo-bloque" onclick="setEvoMode('bloque')">Por bloque</button>
              </div>
            </div>
            <div id="viz-evolucion"></div>
            <div class="viz-legend" id="evo-legend"></div>
          </div>
          <div class="viz-card span2">
            <div class="viz-head"><span class="viz-title">Top 10 comisiones &middot; tendencia 8 semanas</span></div>
            <div id="viz-topcoms"></div>
          </div>
          <div class="viz-card span2">
            <div class="viz-head"><span class="viz-title">Distribuci&oacute;n por tipo</span></div>
            <div id="viz-donut"></div>
          </div>
        </div>
      </div>
    </div>
  </div><!-- /sub-estadisticas -->

  <!-- SUB: BUSCADOR de expedientes -->
  <div id="sub-buscador" class="sub-content active">
    <div class="detalle-layout">
      <div class="filters-top">
        <div class="filters-primary">
          <input class="search-box" type="text" id="search" placeholder="Buscar por extracto, autor o comisi&oacute;n&hellip;" oninput="onFilterChange()">

          <div class="select-wrapper">
            <select class="filter-select" id="bloque-select" onchange="setBloque(this.value)">
              <option value="">Todos los bloques</option>
            </select>
            <span class="select-arrow">&#9660;</span>
          </div>

          <div class="select-wrapper">
            <select class="filter-select" id="autor-select" onchange="onFilterChange()">
              <option value="">Todos los autores</option>
            </select>
            <span class="select-arrow">&#9660;</span>
          </div>

          <div class="select-wrapper">
            <select class="filter-select" id="origen-select" onchange="setOrigenShared(this.value)">
              <option value="">Todos los or&iacute;genes</option>
            </select>
            <span class="select-arrow">&#9660;</span>
          </div>

          <div class="select-wrapper">
            <select class="filter-select" id="tipo-select" onchange="setTipoSelect(this.value)">
              <option value="">Todos los tipos</option>
            </select>
            <span class="select-arrow">&#9660;</span>
          </div>

          <div class="select-wrapper">
            <select class="filter-select" id="com-select-1" onchange="onFilterChange()">
              <option value="">Comisi&oacute;n (1er giro)</option>
            </select>
            <span class="select-arrow">&#9660;</span>
          </div>

          <label class="checkbox-filter">
            <input type="checkbox" id="con-od-check" onchange="setConOD(this.checked)">
            <span>Con OD</span>
          </label>
        </div>

        <details class="filters-more" id="filters-more">
          <summary>M&aacute;s filtros <span class="filters-more-count" id="filters-more-count"></span></summary>
          <div class="filters-more-body">
            <div class="filter-group">
              <div class="filter-label" style="margin-top:0">A&ntilde;o</div>
              <div class="filter-row">
                <button class="chip on" id="anio-det-all" onclick="setAnioShared('')">Todos</button>
                <button class="chip" id="anio-det-2025" onclick="setAnioShared('2025')">2025</button>
                <button class="chip" id="anio-det-2026" onclick="setAnioShared('2026')">2026</button>
              </div>
            </div>

            <div class="filter-group">
              <div id="acuerdo-estado-filter" style="display:none">
                <div class="filter-label" style="margin-top:0">Estado del acuerdo</div>
                <div class="filter-row" id="acuerdo-estado-chips"></div>
              </div>
            </div>

            <div class="filter-group">
              <div class="filter-label" style="margin-top:0">Provincia</div>
              <div class="select-wrapper">
                <select class="filter-select" id="provincia-select" onchange="setProvincia(this.value)">
                  <option value="">Todas las provincias</option>
                </select>
                <span class="select-arrow">&#9660;</span>
              </div>

              <div class="filter-label">Comisi&oacute;n (giros adicionales)</div>
              <div class="select-wrapper">
                <select class="filter-select" id="com-select-adic" onchange="onFilterChange()">
                  <option value="">Todos los giros adicionales</option>
                </select>
                <span class="select-arrow">&#9660;</span>
              </div>
            </div>

            <div class="filter-group">
              <div class="filter-label" style="margin-top:0">Rango de fechas</div>
              <div class="date-range">
                <input type="date" class="date-input" id="fecha-desde" onchange="onFilterChange()">
                <span class="date-sep">hasta</span>
                <input type="date" class="date-input" id="fecha-hasta" onchange="onFilterChange()">
              </div>
            </div>
          </div>
        </details>

        <div class="active-chips" id="active-chips"></div>
      </div>

      <div class="results-panel">
        <div class="results-header">
          <span class="results-count" id="results-count"></span>
          <button class="btn-export" onclick="exportarExcel()">&#128196; Exportar Excel</button>
        </div>
        <div id="list" class="cards-grid"></div>
        <div class="pagination" id="pagination"></div>
      </div>
    </div>
  </div><!-- /sub-buscador -->
</div><!-- /main-proyectos -->

<!-- ====================== MAIN: COMISIONES ====================== -->
<div id="main-comisiones" class="mtab-content">

  <!-- NIVEL 1: lista de comisiones -->
  <div id="com-nivel1" class="com-nivel active">
    <div class="sub-nav">
      <button class="sub-btn active" data-comvista="lista" onclick="switchComVista('lista')">Comisiones</button>
      <button class="sub-btn" data-comvista="estadisticas" onclick="switchComVista('estadisticas')">Estad&iacute;sticas</button>
    </div>

    <div id="com-vista-lista" class="sub-content active">
      <div class="section-block">
        <div class="section-header">
          <h2>Comisiones permanentes</h2>
          <span class="section-hint">{com_hint}</span>
        </div>
        <div class="section-body">
          <div class="stats-bar" id="com-stats-bar"></div>
          <input class="search-box" type="text" id="com-search" placeholder="Buscar comisi&oacute;n&hellip;" oninput="renderComisionesList()" style="max-width:360px">
          <div id="com-list" class="com-grid"></div>
        </div>
      </div>
    </div>

    <div id="com-vista-estadisticas" class="sub-content">
      <div class="section-block">
        <div class="section-header">
          <h2>Estad&iacute;sticas</h2>
          <span class="section-hint">Composici&oacute;n del Senado y de cada comisi&oacute;n</span>
        </div>
        <div class="section-body">
          <div class="com-sub-nav" id="com-estad-nav">
            <button class="com-sub-btn active" data-comestad="bloque" onclick="switchComEstad('bloque')">Por bloque</button>
            <button class="com-sub-btn" data-comestad="senador" onclick="switchComEstad('senador')">Por senador/a</button>
          </div>
          <div id="com-estad-bloque" class="com-sub-content active">
            <div id="repr-global"></div>
            <div id="repr-cross"></div>
          </div>
          <div id="com-estad-senador" class="com-sub-content">
            <input class="search-box" type="text" id="senador-search" placeholder="Buscar senador/a&hellip;" oninput="renderComisionesPorSenador()" style="max-width:360px">
            <div id="senador-grid" class="senator-grid"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- NIVEL 2: detalle de comisión -->
  <div id="com-nivel2" class="com-nivel">
    <div class="section-block">
      <div class="section-header">
        <h2 id="com-detalle-nombre">&nbsp;</h2>
        <div style="display:flex;gap:8px">
          <button class="btn-volver" onclick="exportarComisionPdf()">&#128196; Exportar PDF</button>
          <button class="btn-volver" onclick="volverComisiones()">&larr; Volver</button>
        </div>
      </div>
      <div class="section-body">
        <div id="com-proxima-reunion"></div>

        <div class="com-sub-nav">
          <button class="com-sub-btn active" data-comsub="integrantes" onclick="switchComSub('integrantes')">Integrantes</button>
          <button class="com-sub-btn" data-comsub="proyectos" onclick="switchComSub('proyectos')">Proyectos en tr&aacute;mite</button>
          <button class="com-sub-btn" data-comsub="proyeccion" onclick="switchComSub('proyeccion')">Proyecci&oacute;n de dictamen</button>
        </div>

        <div id="com-sub-integrantes" class="com-sub-content active">
          <div id="com-integrantes-list"></div>
        </div>

        <div id="com-sub-proyectos" class="com-sub-content">
          <div class="com-proy-cats" id="com-proy-cats"></div>
          <div class="am-chips" id="com-proy-tratados-chips" style="display:none"></div>
          <div class="am-grid" id="com-proy-grid"></div>
        </div>

        <div id="com-sub-proyeccion" class="com-sub-content">
          <div class="proy-controls">
            <div class="proy-control-group" style="flex:1">
              <label>Tema en tratamiento</label>
              <input type="text" class="proy-input" id="proyTema" placeholder="Ingres&aacute; el tema a proyectar&hellip;" oninput="updateDictamenBanner()">
            </div>
          </div>
          <div class="dictamen-banner no-dictamen" id="dictamenBanner">
            <span class="dictamen-status" id="dictamenStatus">NO HAY DICTAMEN</span>
            <span class="dictamen-counter" id="dictamenCounter">0 mayor&iacute;a &middot; 0 may. c/ disidencia &middot; 0 minor&iacute;a &middot; 0 sin definir &middot; 0 total</span>
          </div>
          <div class="proy-actions">
            <button class="btn-reset-proy" onclick="resetProyVotos()">Resetear posicionamientos</button>
            <button class="btn-pdf" onclick="exportProyPdf()">&#128196; Exportar PDF</button>
            <span class="proy-mayoria-label" id="proyMayoriaLabel"></span>
          </div>
          <div class="proy-bloque-panel" id="proyBloquePanel"></div>
          <div class="proy-table-wrap">
            <table class="proy-table">
              <thead><tr>
                <th style="width:12px"></th>
                <th>Nombre</th>
                <th>Bloque</th>
                <th>Cargo</th>
                <th>Posicionamiento</th>
              </tr></thead>
              <tbody id="proyTableBody">
                <tr><td colspan="5" class="proy-empty">Sin integrantes cargados.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </div>

</div>

<!-- ====================== MAIN: AGENDA ====================== -->
<div id="main-agenda" class="mtab-content">

  <!-- NIVEL 1: calendario de reuniones -->
  <div id="agenda-nivel1" class="com-nivel active">
    <div class="section-block">
      <div class="section-header">
        <h2>Agenda de reuniones</h2>
        <span class="section-hint">{agenda_hint}</span>
      </div>
      <div class="section-body">

        <div id="agenda-hoy-wrap">
          <div class="agenda-hoy-header">
            <div class="agenda-hoy-titulo" id="agenda-hoy-titulo">Hoy</div>
            <div style="display:flex;gap:8px;flex-wrap:wrap">
              <a class="btn-export" href="editor.html" style="text-decoration:none;display:inline-block" title="Corregir horarios, salones, expositores o suspensiones">&#9998; Editar agenda</a>
              <button class="btn-export" onclick="toggleAgendaVista('calendario')">&#128197; Ver calendario completo</button>
            </div>
          </div>
          <div id="agenda-hoy-body"></div>
        </div>

        <div id="agenda-calendario-wrap" hidden>
          <button class="btn-export" style="margin-bottom:14px" onclick="toggleAgendaVista('hoy')">&larr; Volver a hoy</button>
          <div class="agenda-cal-controls">
            <input class="search-box" type="text" id="agenda-search" placeholder="Buscar palabra exacta (comisi&oacute;n o temario)&hellip;" style="max-width:320px">
            <div class="select-wrapper">
              <select class="filter-select" id="agenda-comision-select">
                <option value="">Todas las comisiones</option>
              </select>
              <span class="select-arrow">&#9660;</span>
            </div>
          </div>
          <div class="cal-header">
            <button class="cal-nav" id="cal-prev" onclick="agendaCambiarMes(-1)" aria-label="Mes anterior">&#8249;</button>
            <div class="cal-mes-label" id="cal-mes-label">&nbsp;</div>
            <button class="cal-nav" id="cal-next" onclick="agendaCambiarMes(1)" aria-label="Mes siguiente">&#8250;</button>
          </div>
          <div class="cal-dow-row">
            <div class="cal-dow">Lun</div><div class="cal-dow">Mar</div><div class="cal-dow">Mi&eacute;</div>
            <div class="cal-dow">Jue</div><div class="cal-dow">Vie</div><div class="cal-dow weekend">S&aacute;b</div>
            <div class="cal-dow weekend">Dom</div>
          </div>
          <div class="cal-grid" id="cal-grid"></div>
          <div class="no-results" id="cal-empty-msg" style="display:none">Sin reuniones para este filtro en el rango cargado.</div>
          <div id="agenda-asesores"></div>
        </div>

      </div>
    </div>
  </div>

  <!-- NIVEL 2: detalle de reunión -->
  <div id="agenda-nivel2" class="com-nivel">
    <div class="section-block">
      <div class="section-header">
        <h2 id="agenda-detalle-titulo">&nbsp;</h2>
        <button class="btn-volver" onclick="volverAgenda()">&larr; Volver</button>
      </div>
      <div class="section-body">
        <div id="agenda-detalle-meta"></div>
        <button class="btn-export" style="margin:10px 0" onclick="abrirFichaReunion()">&#128196; Generar ficha de reuni&oacute;n</button>
        <div class="filter-label" style="margin-top:14px">Temario</div>
        <div id="agenda-temario-list"></div>
      </div>
    </div>
  </div>

</div>

<div id="agenda-dia-overlay" class="dpp-modal-overlay" onclick="agendaCerrarDia(event)">
  <div class="dpp-modal agenda-dia-modal">
    <div class="dpp-modal-head">
      <span id="agenda-dia-titulo"></span>
      <button class="dpp-modal-close" onclick="agendaCerrarDia()">&#10005;</button>
    </div>
    <div class="dpp-modal-body" id="agenda-dia-body"></div>
  </div>
</div>

{pliegos_html}
<div id="main-votacion" class="mtab-content">
<div id="herr-root">
  <div class="sub-nav">
    <button class="sub-btn active" data-herrvista="quorum" onclick="switchHerrVista('quorum')">Contador de qu&oacute;rum</button>
    <button class="sub-btn" data-herrvista="votacion" onclick="switchHerrVista('votacion')">Tablero de votaci&oacute;n</button>
    <button class="sub-btn" data-herrvista="dostercios" onclick="switchHerrVista('dostercios')">C&aacute;lculo 2/3</button>
    <button class="sub-btn" data-herrvista="tiempos" onclick="switchHerrVista('tiempos')">C&aacute;lculo de tiempos</button>
    <button class="sub-btn" data-herrvista="reglamento" onclick="switchHerrVista('reglamento')">Reglamento HSN</button>
  </div>

  <!-- SUB: CONTADOR DE QUÓRUM -->
  <div id="herr-vista-quorum" class="sub-content active">
  <div class="page">
    <header class="masthead">
      <svg class="brand-mark" viewBox="0 0 64 38" aria-hidden="true">
        <circle cx="46.0" cy="32.0" r="1.6" fill="#2668af"/>
        <circle cx="44.1" cy="25.0" r="1.6" fill="#2668af"/>
        <circle cx="39.0" cy="19.9" r="1.6" fill="#2668af"/>
        <circle cx="32.0" cy="18.0" r="1.6" fill="#2668af"/>
        <circle cx="25.0" cy="19.9" r="1.6" fill="#2668af"/>
        <circle cx="19.9" cy="25.0" r="1.6" fill="#2668af"/>
        <circle cx="18.0" cy="32.0" r="1.6" fill="#2668af"/>
        <circle cx="52.0" cy="32.0" r="1.6" fill="#4e93cc"/>
        <circle cx="50.8" cy="25.2" r="1.6" fill="#4e93cc"/>
        <circle cx="47.3" cy="19.1" r="1.6" fill="#4e93cc"/>
        <circle cx="42.0" cy="14.7" r="1.6" fill="#4e93cc"/>
        <circle cx="35.5" cy="12.3" r="1.6" fill="#4e93cc"/>
        <circle cx="28.5" cy="12.3" r="1.6" fill="#4e93cc"/>
        <circle cx="22.0" cy="14.7" r="1.6" fill="#4e93cc"/>
        <circle cx="16.7" cy="19.1" r="1.6" fill="#4e93cc"/>
        <circle cx="13.2" cy="25.2" r="1.6" fill="#4e93cc"/>
        <circle cx="12.0" cy="32.0" r="1.6" fill="#4e93cc"/>
        <circle cx="58.0" cy="32.0" r="1.6" fill="#75bee9"/>
        <circle cx="57.1" cy="25.3" r="1.6" fill="#75bee9"/>
        <circle cx="54.5" cy="19.0" r="1.6" fill="#75bee9"/>
        <circle cx="50.4" cy="13.6" r="1.6" fill="#75bee9"/>
        <circle cx="45.0" cy="9.5" r="1.6" fill="#75bee9"/>
        <circle cx="38.7" cy="6.9" r="1.6" fill="#75bee9"/>
        <circle cx="32.0" cy="6.0" r="1.6" fill="#75bee9"/>
        <circle cx="25.3" cy="6.9" r="1.6" fill="#75bee9"/>
        <circle cx="19.0" cy="9.5" r="1.6" fill="#75bee9"/>
        <circle cx="13.6" cy="13.6" r="1.6" fill="#75bee9"/>
        <circle cx="9.5" cy="19.0" r="1.6" fill="#75bee9"/>
        <circle cx="6.9" cy="25.3" r="1.6" fill="#75bee9"/>
        <circle cx="6.0" cy="32.0" r="1.6" fill="#75bee9"/>
      </svg>
      <div class="eyebrow">Congreso de la Nación Argentina · Cámara de Senadores</div>
      <h1>Contador de Quórum</h1>
      <p class="subhead">Marcá presentes y ausentes para llevar el registro del quórum de la sesión. Hacé clic en una banca para alternar el estado, o filtrá por bloque para ubicar senadores más rápido.</p>
    </header>

    <div class="card">
      <div class="controls">
        <div class="controls-left">
          <select id="qBloqueSelect" aria-label="Filtrar por bloque"></select>
          <input id="qSearchInput" type="search" placeholder="Buscar senador..." aria-label="Buscar senador">
        </div>
        <div id="qResultBox" class="result"></div>
      </div>

      <div class="history-bar">
        <button id="qUndoBtn" class="btn-undo" disabled>↺ Deshacer</button>
      </div>

      <div class="bulk-actions">
        <button class="btn-positive" data-action="all-presente">Todos presentes</button>
        <button class="btn-negative" data-action="all-ausente">Todos ausentes</button>
        <button class="btn-neutral" data-action="all-clear">Limpiar todos</button>
      </div>

      <div class="pdf-bar">
        <button id="qDownloadPdfBtn" class="btn-brass">Ver / imprimir registro de quórum (PDF)</button>
      </div>

      <div class="chamber-wrap">
        <div id="qTooltip" class="tooltip" hidden></div>
        <div class="chamber-scroll">
          <svg id="qChamber" viewBox="0 0 800 460" role="img" aria-label="Hemiciclo del Senado (quórum)"></svg>
        </div>
      </div>

      <div id="qRosterPanel" class="roster" hidden>
        <div class="roster-head">
          <span class="label" id="qRosterLabel"></span>
          <div class="roster-actions">
            <button class="btn-positive" data-action="bloc-presente">Bloque presente</button>
            <button class="btn-negative" data-action="bloc-ausente">Bloque ausente</button>
            <button class="btn-neutral" data-action="bloc-clear">Limpiar bloque</button>
          </div>
        </div>
        <div id="qRosterGrid" class="roster-grid"></div>
      </div>

      <div class="tallies">
        <div class="tally">
          <div class="num" id="qTotalPresente">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-positive)"></span>Presentes</div>
        </div>
        <div class="tally">
          <div class="num" id="qTotalAusente">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-negative)"></span>Ausentes</div>
        </div>
        <div class="tally">
          <div class="num" id="qTotalPendiente">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-pending-fill); border:1.5px solid var(--vote-pending-stroke)"></span>Pendientes</div>
        </div>
      </div>
    </div>

    <footer class="credit">72 bancas · quórum requerido: <strong id="qQuorumNeeded">37</strong> senadores presentes</footer>
  </div>
  </div>

  <!-- SUB: TABLERO DE VOTACIÓN -->
  <div id="herr-vista-votacion" class="sub-content">
  <div class="page">
    <header class="masthead">
      <svg class="brand-mark" viewBox="0 0 64 38" aria-hidden="true">
        <circle cx="46.0" cy="32.0" r="1.6" fill="#2668af"/>
        <circle cx="44.1" cy="25.0" r="1.6" fill="#2668af"/>
        <circle cx="39.0" cy="19.9" r="1.6" fill="#2668af"/>
        <circle cx="32.0" cy="18.0" r="1.6" fill="#2668af"/>
        <circle cx="25.0" cy="19.9" r="1.6" fill="#2668af"/>
        <circle cx="19.9" cy="25.0" r="1.6" fill="#2668af"/>
        <circle cx="18.0" cy="32.0" r="1.6" fill="#2668af"/>
        <circle cx="52.0" cy="32.0" r="1.6" fill="#4e93cc"/>
        <circle cx="50.8" cy="25.2" r="1.6" fill="#4e93cc"/>
        <circle cx="47.3" cy="19.1" r="1.6" fill="#4e93cc"/>
        <circle cx="42.0" cy="14.7" r="1.6" fill="#4e93cc"/>
        <circle cx="35.5" cy="12.3" r="1.6" fill="#4e93cc"/>
        <circle cx="28.5" cy="12.3" r="1.6" fill="#4e93cc"/>
        <circle cx="22.0" cy="14.7" r="1.6" fill="#4e93cc"/>
        <circle cx="16.7" cy="19.1" r="1.6" fill="#4e93cc"/>
        <circle cx="13.2" cy="25.2" r="1.6" fill="#4e93cc"/>
        <circle cx="12.0" cy="32.0" r="1.6" fill="#4e93cc"/>
        <circle cx="58.0" cy="32.0" r="1.6" fill="#75bee9"/>
        <circle cx="57.1" cy="25.3" r="1.6" fill="#75bee9"/>
        <circle cx="54.5" cy="19.0" r="1.6" fill="#75bee9"/>
        <circle cx="50.4" cy="13.6" r="1.6" fill="#75bee9"/>
        <circle cx="45.0" cy="9.5" r="1.6" fill="#75bee9"/>
        <circle cx="38.7" cy="6.9" r="1.6" fill="#75bee9"/>
        <circle cx="32.0" cy="6.0" r="1.6" fill="#75bee9"/>
        <circle cx="25.3" cy="6.9" r="1.6" fill="#75bee9"/>
        <circle cx="19.0" cy="9.5" r="1.6" fill="#75bee9"/>
        <circle cx="13.6" cy="13.6" r="1.6" fill="#75bee9"/>
        <circle cx="9.5" cy="19.0" r="1.6" fill="#75bee9"/>
        <circle cx="6.9" cy="25.3" r="1.6" fill="#75bee9"/>
        <circle cx="6.0" cy="32.0" r="1.6" fill="#75bee9"/>
      </svg>
      <div class="eyebrow">Congreso de la Nación Argentina · Cámara de Senadores</div>
      <h1>Tablero de Votación</h1>
      <p class="subhead">Composición vigente de los 72 escaños. Hacé clic en una banca para recorrer los estados de voto, o filtrá por bloque para ubicar senadores más rápido.</p>
    </header>

    <div class="card">
      <div class="scenario-bar">
        <select id="scenarioSelect" aria-label="Escenario guardado"></select>
        <div class="scenario-actions">
          <button id="newScenarioBtn" class="btn-neutral">Nuevo escenario</button>
          <button id="saveScenarioBtn" class="btn-neutral">Guardar</button>
          <button id="deleteScenarioBtn" class="btn-neutral">Eliminar</button>
        </div>
        <span id="scenarioStatus" class="scenario-status"></span>
      </div>

      <div class="controls">
        <div class="controls-left">
          <select id="majoritySelect" aria-label="Tipo de mayoría requerida"></select>
          <select id="bloqueSelect" aria-label="Filtrar por bloque"></select>
          <input id="searchInput" type="search" placeholder="Buscar senador..." aria-label="Buscar senador">
        </div>
        <div id="resultBox" class="result" hidden></div>
      </div>

      <div class="history-bar">
        <button id="undoBtn" class="btn-undo" disabled>↺ Deshacer</button>
      </div>

      <div class="bulk-actions">
        <button class="btn-positive" data-action="all-positive">Todos afirmativos</button>
        <button class="btn-negative" data-action="all-negative">Todos negativos</button>
        <button class="btn-neutral" data-action="all-clear">Limpiar todos</button>
      </div>

      <div class="pdf-bar">
        <button id="downloadPdfBtn" class="btn-brass">Ver / imprimir resultados (PDF)</button>
      </div>

      <div class="chamber-wrap">
        <div id="tooltip" class="tooltip" hidden></div>
        <div class="chamber-scroll">
          <svg id="chamber" viewBox="0 0 800 460" role="img" aria-label="Hemiciclo del Senado"></svg>
        </div>
      </div>

      <div id="rosterPanel" class="roster" hidden>
        <div class="roster-head">
          <span class="label" id="rosterLabel"></span>
          <div class="roster-actions">
            <button class="btn-positive" data-action="bloc-positive">Bloque afirmativo</button>
            <button class="btn-negative" data-action="bloc-negative">Bloque negativo</button>
            <button class="btn-neutral" data-action="bloc-clear">Limpiar bloque</button>
          </div>
        </div>
        <div id="rosterGrid" class="roster-grid"></div>
      </div>

      <div class="tallies">
        <div class="tally">
          <div class="num" id="totalPositive">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-positive)"></span>Afirmativos</div>
        </div>
        <div class="tally">
          <div class="num" id="totalNegative">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-negative)"></span>Negativos</div>
        </div>
        <div class="tally">
          <div class="num" id="totalAbstention">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-abstention)"></span>Abstenciones</div>
        </div>
        <div class="tally">
          <div class="num" id="totalAbsent">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-absent)"></span>Ausentes</div>
        </div>
        <div class="tally">
          <div class="num" id="totalPending">0</div>
          <div class="lbl"><span class="dot" style="background:var(--vote-pending-fill); border:1.5px solid var(--vote-pending-stroke)"></span>Pendientes</div>
        </div>
      </div>
    </div>

    <footer class="credit">72 bancas · fuente: nómina de senadores 2026</footer>
  </div>
  </div>

  <!-- SUB: CÁLCULO 2/3 -->
  <div id="herr-vista-dostercios" class="sub-content">
  <div class="page dt-page">
    <header class="masthead">
      <div class="eyebrow">Congreso de la Nación Argentina · Cámara de Senadores</div>
      <h1>Cálculo de 2/3</h1>
      <p class="subhead">Ingresá el total de senadores a considerar (máximo 72) para saber cuántos representan las dos terceras partes.</p>
    </header>

    <div class="card dt-card">
      <div class="dt-field">
        <label for="dtTotal">Total de senadores</label>
        <input type="number" id="dtTotal" min="1" max="72" step="1" value="72">
      </div>
      <div class="dt-result">
        <div class="dt-result-num" id="dtResultNum">48</div>
        <div class="dt-result-lbl">senadores hacen los 2/3 de <strong id="dtResultTotal">72</strong></div>
      </div>
    </div>
  </div>
  </div>

  <!-- SUB: CÁLCULO DE TIEMPOS -->
  <div id="herr-vista-tiempos" class="sub-content">
  <div class="page">
    <header class="masthead">
      <div class="eyebrow">Congreso de la Nación Argentina · Cámara de Senadores</div>
      <h1>Cálculo de Tiempos</h1>
      <p class="subhead">Organizá el listado de oradores por tema de debate, asigná tiempos de exposición y obtené la hora estimada de finalización.</p>
    </header>

    <div class="card">
      <div class="scenario-bar">
        <select id="temaSelect" aria-label="Tema de debate"></select>
        <div class="scenario-actions">
          <button id="newTemaBtn" class="btn-neutral">Nuevo tema</button>
          <button id="renameTemaBtn" class="btn-neutral">Renombrar</button>
          <button id="deleteTemaBtn" class="btn-neutral">Eliminar</button>
        </div>
      </div>

      <div class="tiempos-config">
        <label>Hora de inicio del debate
          <input type="time" id="horaInicioInput">
        </label>
        <div class="tiempos-fin">Hora estimada de finalización: <strong id="horaFinEstimada">—</strong></div>
      </div>

      <div class="tiempos-add">
        <select id="oradorSelect" aria-label="Elegir senador"></select>
        <input type="number" id="oradorMinutos" min="1" max="120" value="5" aria-label="Minutos de exposición">
        <button id="addOradorBtn" class="btn-brass">Agregar orador</button>
      </div>

      <div class="tiempos-pdf-import">
        <input type="file" id="oradoresPdfInput" accept="application/pdf" style="display:none">
        <button id="importPdfBtn" class="btn-neutral">&#128196; Cargar lista de oradores (PDF)</button>
        <span id="importPdfStatus" class="tiempos-pdf-status"></span>
      </div>

      <div id="oradoresList" class="oradores-list"></div>
    </div>
  </div>
  </div>

  <!-- SUB: REGLAMENTO HSN -->
  <div id="herr-vista-reglamento" class="sub-content">
  <div class="page">
    <header class="masthead">
      <div class="eyebrow">Congreso de la Nación Argentina · Cámara de Senadores</div>
      <h1>Reglamento HSN</h1>
      <p class="subhead">Reglamento del Honorable Senado de la Nación, a mano durante la sesión.</p>
    </header>

    <div class="card">
      <div class="reg-toolbar">
        <a href="Reglamento_HSN.pdf" target="_blank" rel="noopener" class="btn-brass" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none;">Abrir en pestaña nueva</a>
        <a href="Reglamento_HSN.pdf" download class="btn-neutral" style="display:inline-flex;align-items:center;justify-content:center;text-decoration:none;">Descargar PDF</a>
      </div>
      <div class="reg-frame-wrap">
        <iframe class="reg-frame" src="Reglamento_HSN.pdf" title="Reglamento HSN"></iframe>
        <p class="reg-fallback">Si el documento no se visualiza (por ejemplo, en algunos navegadores móviles), usá "Abrir en pestaña nueva" o "Descargar PDF".</p>
      </div>
    </div>
  </div>
  </div>

</div>

<div id="printView" class="print-view" hidden></div>
<div id="quorumPrintView" class="print-view" hidden></div>
</div>

<!-- ====================== MAIN: AYUDA MEMORIA ====================== -->
<div id="main-ayuda" class="mtab-content">
  <div id="am-root">
    <div class="am-sub-nav">
      <button class="am-sub-btn active" data-amvista="principal" onclick="setAmVista('principal')">Ayuda Memoria</button>
      <button class="am-sub-btn" data-amvista="preferencias" onclick="setAmVista('preferencias')">Preferencias</button>
    </div>

    <div id="am-vista-principal" class="am-sub-content active">
      <div class="section-block">
        <div class="section-header">
          <h2>Ayuda Memoria</h2>
          <span class="section-hint">&Oacute;rdenes del D&iacute;a del HSN</span>
        </div>
        <div class="section-body">
          <div class="am-controls">
            <input class="search-box" type="text" id="am-search" placeholder="Buscar por texto, autor o expediente&hellip;">
            <div class="select-wrapper">
              <select class="filter-select" id="am-comision-select">
                <option value="">Todas las comisiones</option>
              </select>
              <span class="select-arrow">&#9660;</span>
            </div>
            <div class="select-wrapper">
              <select class="filter-select" id="am-autor-select">
                <option value="">Todos los autores</option>
              </select>
              <span class="select-arrow">&#9660;</span>
            </div>
            <div class="select-wrapper">
              <select class="filter-select" id="am-bloque-select">
                <option value="">Todos los bloques (autor)</option>
              </select>
              <span class="select-arrow">&#9660;</span>
            </div>
          </div>
          <div class="am-chips" id="am-chips"></div>
          <div class="am-count-row">
            <div class="am-count" id="am-count"></div>
            <button class="btn-export" onclick="exportarAyudaMemoria()">&#128190; Exportar (seg&uacute;n filtros)</button>
          </div>
          <div class="am-grid" id="am-grid"></div>
        </div>
      </div>
    </div>

    <div id="am-vista-preferencias" class="am-sub-content">
      <div class="section-block">
        <div class="section-header">
          <h2>Preferencias</h2>
          <span class="section-hint">Mociones de preferencia aprobadas</span>
        </div>
        <div class="section-body">
          <div class="filter-row" id="sanc-pref-chips"></div>
          <div id="sanc-pref-list" class="sanc-grid"></div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="am-scrim" id="am-scrim">
  <div class="am-story">
    <div class="am-progress" id="am-progress"></div>
    <div class="am-story-head">
      <div class="id" id="am-story-id">OD 000/26</div>
      <button class="close" id="am-close">&#10005;</button>
    </div>
    <button class="am-story-nav prev" id="am-prev-zone"></button>
    <button class="am-story-nav next" id="am-next-zone"></button>
    <div class="am-story-body" id="am-story-body"></div>
    <div class="am-story-foot">
      <button id="am-btn-prev">&larr; Anterior</button>
      <div class="am-dots" id="am-dots"></div>
      <button id="am-btn-next">Siguiente &rarr;</button>
    </div>
  </div>
</div>

<!-- ====================== MAIN: SANCIONES HSN ====================== -->
<div id="main-sanciones" class="mtab-content">
  <div class="section-block">
    <div class="section-header">
      <h2>Sanciones HSN</h2>
      <span class="section-hint">Bolet&iacute;n de Novedades del HSN</span>
    </div>
    <div class="section-body">
      <div class="filter-row" id="sanc-chips"></div>
      <input class="search-box" type="text" id="sanc-search" placeholder="Buscar por n&uacute;mero de expediente o extracto&hellip;" oninput="renderSanciones()" style="max-width:360px">
      <div id="sanc-list" class="sanc-grid"></div>
    </div>
  </div>
</div>

<div id="dash-tooltip" class="dash-tooltip"></div>

<div id="fichaReunionOverlay" class="ficha-overlay" hidden>
  <div id="fichaReunionView" class="ficha-view"></div>
</div>

<div id="dpp-modal-overlay" class="dpp-modal-overlay" onclick="cerrarDppModal(event)">
  <div class="dpp-modal">
    <div class="dpp-modal-head">
      <span id="dpp-modal-title"></span>
      <button class="dpp-modal-close" onclick="cerrarDppModal()">&#10005;</button>
    </div>
    <div class="dpp-modal-body" id="dpp-modal-body"></div>
  </div>
</div>

<div id="ficha-overlay" class="dpp-modal-overlay" onclick="cerrarFicha(event)">
  <div class="dpp-modal ficha-modal">
    <div class="dpp-modal-head">
      <span id="ficha-titulo"></span>
      <button class="dpp-modal-close" onclick="cerrarFicha()">&#10005;</button>
    </div>
    <div class="dpp-modal-body">
      <div class="ficha-stepper" id="ficha-stepper"></div>
      <div class="ficha-body" id="ficha-body"></div>
    </div>
  </div>
</div>

<div class="footer">Prosecretar&iacute;a Parlamentaria &middot; Senado de la Naci&oacute;n Argentina<br>Datos al {fecha}</div>

<script>
var DATA = {datos};
var COMISIONES = {comisiones};
var AGENDA = {agenda};
var AYUDA_MEMORIA = {ayuda_memoria};
var SANCIONES_DATA = {sanciones};
var BLOQUE_TOTALES = {bloque_totales};
var FOTOS_SENADORES = {fotos_senadores};
var PLIEGOS_DATA = {pliegos_data};
var FONT_POPPINS_REGULAR = "{font_regular}";
var FONT_POPPINS_BOLD = "{font_bold}";
{js}
init();
if(location.hash&&!window.pjSyncHash()&&!abrirReunionDesdeHash())activateMain(location.hash.slice(1).split('/')[0]);
</script>
</body>
</html>"""


# Autoridades por comisión (pres/vice/secr) — fuente: repo comisiones-senado
# (no viene en el scraper de comisiones.json; roles no listados = Vocal).
AUTORIDADES = {
    'De Acuerdos': {'pres': 'PAGOTTO, Juan Carlos', 'vice': 'ABAD, Maximiliano', 'secr': 'GOERLING LARA, Enrique Martín'},
    'De Agricultura, Ganadería y Pesca': {'pres': 'BENEGAS LYNCH, Joaquín Alberto', 'vice': 'KRONEBERGER, Daniel Ricardo', 'secr': ''},
    'De Ambiente y Desarrollo Sustentable': {'pres': 'TERENZI, Edith Elizabeth', 'vice': '', 'secr': ''},
    'De Asuntos Administrativos y Municipales': {'pres': 'KRONEBERGER, Daniel Ricardo', 'vice': 'MARKS, Ana Inés', 'secr': ''},
    'De Asuntos Constitucionales': {'pres': 'COTO, Agustín Pedro', 'vice': 'LÓPEZ, María Florencia', 'secr': ''},
    'De Ciencia y Tecnología': {'pres': 'DE PEDRO, Eduardo Enrique', 'vice': 'ALMEIDA, Romina María', 'secr': ''},
    'De Coparticipación Federal de Impuestos': {'pres': 'VISCHI, Eduardo Alejandro', 'vice': 'ROYÓN, Flavia Gabriela', 'secr': ''},
    'De Defensa Nacional': {'pres': 'JUEZ, Luis Alfredo', 'vice': 'LINARES, Carlos Alberto', 'secr': ''},
    'De Deporte': {'pres': 'FERNÁNDEZ SAGASTI, Anabel', 'vice': 'ABAD, Maximiliano', 'secr': 'ABDALA, Bartolomé Esteban'},
    'De Derechos y Garantías': {'pres': 'BENSUSÁN, Daniel Pablo', 'vice': '', 'secr': 'CERVI, Mario Pablo'},
    'De Economía Nacional e Inversión': {'pres': 'GOERLING LARA, Enrique Martín', 'vice': '', 'secr': 'CORROZA, Julieta'},
    'De Economías Regionales, Economía Social, Micro, Pequeña y Mediana Empresa': {'pres': 'CAPITANICH, Jorge Milton', 'vice': '', 'secr': ''},
    'De Educación y Cultura': {'pres': 'ROJAS DECUT, Sonia Elizabeth', 'vice': 'VALENZUELA, Mercedes Gabriela', 'secr': ''},
    'De Industria y Comercio': {'pres': 'LEWANDOWSKI, Marcelo Néstor', 'vice': 'GADANO, Natalia Elena', 'secr': ''},
    'De Infraestructura, Vivienda y Transporte': {'pres': 'ÁVILA, Beatriz Luisa', 'vice': 'FULLONE, Enzo Paolo', 'secr': 'LEWANDOWSKI, Marcelo Néstor'},
    'De Justicia y Asuntos Penales': {'pres': 'GUZMÁN CORAITA, Gonzalo', 'vice': '', 'secr': ''},
    'De Legislación General': {'pres': 'MÁRQUEZ, Nadia Judith', 'vice': 'BENSUSÁN, Daniel Pablo', 'secr': ''},
    'De Minería, Energía y Combustibles': {'pres': 'ROYÓN, Flavia Gabriela', 'vice': 'FAMA, Flavio Sergio', 'secr': 'CERVI, Mario Pablo'},
    'De Población y Desarrollo Humano': {'pres': 'KIRCHNER, Alicia Margarita Antonia', 'vice': 'GODOY, Juan Cruz', 'secr': ''},
    'De Presupuesto y Hacienda': {'pres': 'MONTEVERDE, Agustín Aníbal', 'vice': 'SALINO, Fernando Aldo', 'secr': 'SCHNEIDER, Silvana Lorena'},
    'De Relaciones Exteriores y Culto': {'pres': 'PAOLTRONI, Francisco Manuel', 'vice': '', 'secr': ''},
    'De Salud': {'pres': 'ARRASCAETA, Ivanna Marcela', 'vice': 'ARCE, Carlos Omar', 'secr': ''},
    'De Seguridad Interior y Narcotráfico': {'pres': 'LOSADA, Carolina', 'vice': '', 'secr': ''},
    'De Sistemas, Medios de Comunicación y Libertad de Expresión': {'pres': 'MOISÉS, María Carolina', 'vice': '', 'secr': ''},
    'De Trabajo y Previsión Social': {'pres': 'ALVAREZ RIVERO, Carmen', 'vice': '', 'secr': ''},
    'De Turismo': {'pres': 'JURI, Mariana', 'vice': '', 'secr': ''},
}


def _cargar(nombre, default):
    path = os.path.join(DATA_DIR, nombre)
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except Exception:
            return default
    return default


def _norm_com(s):
    """Normaliza nombre de comisión: mayúsculas, sin tildes, sin prefijo 'DE '."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.upper().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"^DE\s+", "", s)
    s = re.sub(r"[^A-Z0-9, ]", "", s)
    return s


def _norm_nombre(s):
    """Normaliza nombre de senador para comparar: mayúsculas, sin tildes."""
    if not s:
        return ""
    s = unicodedata.normalize("NFD", s.upper().strip())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _nombres_coinciden(a, b):
    """Compara dos nombres 'APELLIDO, Nombre' tolerando nombres de pila
    incompletos (ej. 'FAMA, Flavio' vs 'FAMA, Flavio Sergio')."""
    na, nb = _norm_nombre(a), _norm_nombre(b)
    if na == nb:
        return True
    ap_a = na.split(",")[0].strip()
    ap_b = nb.split(",")[0].strip()
    if ap_a != ap_b:
        return False
    resto_a = na.split(",", 1)[1].strip() if "," in na else ""
    resto_b = nb.split(",", 1)[1].strip() if "," in nb else ""
    if not resto_a or not resto_b:
        return True
    return resto_a.startswith(resto_b) or resto_b.startswith(resto_a)


def construir_dpp_state(cambios):
    """Reproduce el log de DPP (misma lógica que buildState del repo
    comisiones-senado: rewrites aplicados inline en orden cronológico).
    Devuelve {comision_norm: [{nombre, dpp}]} — el roster VIGENTE
    (últimos designados) de cada comisión según el log, con el nombre
    tal como figura en el DPP que los designó."""
    state = {}
    rewrites_pend = {}
    for c in cambios:
        com = _norm_com(c["comision"])
        sen_orig = c.get("senador", "")
        sen = _norm_nombre(sen_orig)
        state.setdefault(com, {})
        if c["tipo"] == "rewrite":
            pr = rewrites_pend.get(com)
            if pr is None or pr["dpp"] != c["dpp"]:
                if pr is not None:
                    state[com] = pr["members"]
                rewrites_pend[com] = pr = {"dpp": c["dpp"], "members": {}}
            pr["members"][sen] = {"nombre": sen_orig, "dpp": c["dpp"]}
        else:
            if com in rewrites_pend:
                state[com] = dict(rewrites_pend[com]["members"])
                del rewrites_pend[com]
            d = state[com]
            if c["tipo"] == "add":
                d[sen] = {"nombre": sen_orig, "dpp": c["dpp"]}
            elif c["tipo"] == "replace":
                rem = _norm_nombre(c.get("reemplaza", ""))
                d.pop(rem, None)
                d[sen] = {"nombre": sen_orig, "dpp": c["dpp"]}
            elif c["tipo"] == "remove":
                d.pop(sen, None)
    for com, pr in rewrites_pend.items():
        state[com] = pr["members"]
    return {com: list(members.values()) for com, members in state.items()}


def _rol_de(nombre_com, nombre_miembro):
    aut = AUTORIDADES.get(nombre_com, {})
    if aut.get("pres") and _nombres_coinciden(aut["pres"], nombre_miembro):
        return "Presidente"
    if aut.get("vice") and _nombres_coinciden(aut["vice"], nombre_miembro):
        return "Vicepresidente"
    if aut.get("secr") and _nombres_coinciden(aut["secr"], nombre_miembro):
        return "Secretario"
    return "Vocal"


def construir_bloque_por_senador():
    """Mapa nombre_norm -> bloque, desde data/senadores.json (fuente
    principal) con fallback por apellido para nombres de pila incompletos."""
    senadores = _cargar("senadores.json", {})
    directo = {}
    por_apellido = {}
    for nombre, datos in senadores.items():
        n = _norm_nombre(nombre)
        bloque = datos.get("bloque", "")
        directo[n] = bloque
        apellido = n.split(",")[0].strip()
        por_apellido.setdefault(apellido, []).append((n, bloque))

    def buscar(nombre_buscado):
        n = _norm_nombre(nombre_buscado)
        if n in directo:
            return directo[n]
        apellido = n.split(",")[0].strip()
        candidatos = por_apellido.get(apellido, [])
        if len(candidatos) == 1:
            return candidatos[0][1]
        for k, bloque in candidatos:
            if _nombres_coinciden(k, n):
                return bloque
        return ""

    return buscar


def construir_provincia_por_senador():
    """Igual que construir_bloque_por_senador() pero para provincia -- se
    usa en la ficha de reunión (checklist de integrantes por comisión)."""
    senadores = _cargar("senadores.json", {})
    directo = {}
    por_apellido = {}
    for nombre, datos in senadores.items():
        n = _norm_nombre(nombre)
        provincia = datos.get("provincia", "")
        directo[n] = provincia
        apellido = n.split(",")[0].strip()
        por_apellido.setdefault(apellido, []).append((n, provincia))

    def buscar(nombre_buscado):
        n = _norm_nombre(nombre_buscado)
        if n in directo:
            return directo[n]
        apellido = n.split(",")[0].strip()
        candidatos = por_apellido.get(apellido, [])
        if len(candidatos) == 1:
            return candidatos[0][1]
        for k, provincia in candidatos:
            if _nombres_coinciden(k, n):
                return provincia
        return ""

    return buscar


def _parse_fecha_agenda(fecha_dd_mm, boletin_numero):
    """'17/06' + boletín '64/26' -> datetime(2026,6,17). Sin año -> None."""
    try:
        dia, mes = fecha_dd_mm.split("/")
        anio_suffix = (boletin_numero or "").split("/")[-1]
        anio = 2000 + int(anio_suffix)
        return datetime(anio, int(mes), int(dia))
    except Exception:
        return None


RE_EXP_NUMERO = re.compile(r"^([A-ZÑ.]+)-(\d+)/(\d+)$")


def _parse_exp_numero(numero):
    """'S-1271/25' -> ('S', 1271, 2025). 'P.E-133/26' -> ('PE', 133, 2026).
    Formato no reconocible (o vacío, como en ítems de temario sin EXPTE.) -> None."""
    if not numero:
        return None
    m = RE_EXP_NUMERO.match(numero.strip().upper())
    if not m:
        return None
    try:
        origen = m.group(1).replace(".", "")
        nro = int(m.group(2))
        anio = 2000 + int(m.group(3))
    except ValueError:
        return None
    return origen, nro, anio


def _nombre_com_display(s):
    return re.sub(r"^De\s+", "", s or "")


def _resolver_comisiones_reunion(raw_lines, comisiones):
    """Las comisiones de una reunión vienen del PDF como líneas sueltas: pueden
    ser el nombre de UNA comisión partido por el ancho de columna, o VARIAS
    comisiones distintas (reunión conjunta). Se resuelve buscando qué nombres
    oficiales de comisiones.json aparecen como substring del texto unido y
    normalizado; si ninguno matchea (ej. comisiones bicamerales, que no están
    en comisiones.json), se devuelve el texto crudo unido como fallback."""
    flat = _norm_com(" ".join(raw_lines or []))
    encontradas = []
    for com in comisiones:
        n = _norm_com(com["nombre"])
        if n and n in flat:
            encontradas.append(_nombre_com_display(com["nombre"]))
    if encontradas:
        return encontradas
    texto = " ".join(l.strip() for l in (raw_lines or []) if l.strip())
    return [texto] if texto else []


def _clave_override(fecha, hora, comisiones_raw):
    """Misma clave que clave_reunion() de scraper_agenda.py (fecha/hora tal
    como figuran en el boletín, sin resolver nombres) -- así una corrección
    de horario no rompe el match: el override se busca por el horario
    ORIGINAL publicado, no por el corregido."""
    return (fecha or "", hora or "", tuple(comisiones_raw or []))


def _cargar_overrides_agenda():
    data = _cargar("agenda_overrides.json", {})
    idx = {}
    for o in data.get("overrides", []):
        if o.get("nueva"):
            continue
        clave = _clave_override(o.get("fecha"), o.get("hora"), o.get("comisiones"))
        idx[clave] = o
    return idx


def construir_agenda(comisiones):
    """Procesa data/agenda.json para embeber en la web: resuelve nombres de
    comisión y agrega fecha completa (con año) y fecha ISO para ordenar/comparar
    en el cliente. Aplica encima data/agenda_overrides.json -- correcciones
    puntuales (horario, salón, expositores, aclaración, suspensión, tipo de
    reunión, expedientes agregados al temario) cargadas a mano desde
    editor.html, sin re-scrapear ni pasar por este script. También agrega ahí
    mismo las reuniones creadas enteramente a mano (sin boletín de origen)."""
    agenda = _cargar("agenda.json", {})
    reuniones = agenda.get("reuniones", []) if isinstance(agenda, dict) else agenda
    overrides_data = _cargar("agenda_overrides.json", {})
    todos_overrides = overrides_data.get("overrides", [])
    overrides_idx = _cargar_overrides_agenda()
    resultado = []
    claves_existentes = set()
    for r in reuniones:
        clave = _clave_override(r.get("fecha"), r.get("hora"), r.get("comisiones"))
        claves_existentes.add(clave)
        o = overrides_idx.get(clave)

        hora = (o.get("hora_nueva") if o and o.get("hora_nueva") else None) or r.get("hora", "")
        salon = (o.get("salon_nuevo") if o and o.get("salon_nuevo") else None) or r.get("salon", "")
        salon_completo = salon if (o and o.get("salon_nuevo")) else r.get("salon_completo", "")
        suspendida = o["suspendida"] if (o and "suspendida" in o) else r.get("suspendida", False)

        expositores = r.get("expositores")
        if o and o.get("expositores_extra"):
            expositores = (expositores + "\n" if expositores else "") + o["expositores_extra"]

        tipo = (o.get("tipo_nuevo") if o and o.get("tipo_nuevo") else None) or r.get("tipo", "")

        temario = list(r.get("temario", []))
        if o and o.get("temario_extra"):
            temario = temario + o["temario_extra"]

        fecha_dt = _parse_fecha_agenda(r.get("fecha", ""), r.get("boletin_numero", ""))
        fecha_completa, fecha_iso = r.get("fecha", ""), ""
        if fecha_dt:
            fecha_completa = fecha_dt.strftime("%d/%m/%Y")
            try:
                hh, mm = hora.split(":")
                fecha_iso = fecha_dt.replace(hour=int(hh), minute=int(mm)).isoformat()
            except Exception:
                fecha_iso = fecha_dt.isoformat()
        resultado.append({
            "dia": r.get("dia", ""),
            "fecha": r.get("fecha", ""),
            "fecha_completa": fecha_completa,
            "fecha_iso": fecha_iso,
            "hora": hora,
            "hora_boletin": r.get("hora", "") if (o and o.get("hora_nueva")) else None,
            "modalidad": r.get("modalidad", ""),
            "comisiones": _resolver_comisiones_reunion(r.get("comisiones", []), comisiones),
            "salon": salon,
            "salon_completo": salon_completo,
            "temario": temario,
            "expositores": expositores,
            "nota": (o.get("nota") or None) if o else None,
            "tipo": tipo,
            "boletin_numero": r.get("boletin_numero", ""),
            "suspendida": suspendida,
            "editada": bool(o),
            "creada": False,
        })

    # Reuniones creadas enteramente desde editor.html (sin boletín de origen).
    # Si más adelante el scraper termina trayendo la misma reunión (mismo
    # clave), gana la del boletín y ésta no se duplica.
    for o in todos_overrides:
        if not o.get("nueva"):
            continue
        clave = _clave_override(o.get("fecha"), o.get("hora"), o.get("comisiones"))
        if clave in claves_existentes:
            continue
        fecha_dt = _parse_fecha_agenda(o.get("fecha", ""), o.get("boletin_numero", "manual/00"))
        fecha_completa, fecha_iso = o.get("fecha", ""), ""
        if fecha_dt:
            fecha_completa = fecha_dt.strftime("%d/%m/%Y")
            try:
                hh, mm = (o.get("hora") or "").split(":")
                fecha_iso = fecha_dt.replace(hour=int(hh), minute=int(mm)).isoformat()
            except Exception:
                fecha_iso = fecha_dt.isoformat()
        salon = o.get("salon_nuevo") or ""
        resultado.append({
            "dia": o.get("dia", ""),
            "fecha": o.get("fecha", ""),
            "fecha_completa": fecha_completa,
            "fecha_iso": fecha_iso,
            "hora": o.get("hora", ""),
            "hora_boletin": None,
            "modalidad": "",
            "comisiones": _resolver_comisiones_reunion(o.get("comisiones", []), comisiones),
            "salon": salon,
            "salon_completo": salon,
            "temario": o.get("temario_extra") or [],
            "expositores": o.get("expositores_extra"),
            "nota": o.get("nota"),
            "tipo": o.get("tipo_nuevo") or "senadores",
            "boletin_numero": "Cargada a mano",
            "suspendida": bool(o.get("suspendida")),
            "editada": True,
            "creada": True,
        })
    return resultado


def cruzar_proyectos_agenda(proyectos, agenda_procesada):
    """Por cada proyecto, agrega (in place) un campo 'reuniones' con las
    reuniones en cuyo temario aparece su expediente, más recientes primero."""
    idx = {(p.get("origen"), p.get("nro"), p.get("anio")): p for p in proyectos}
    for r in agenda_procesada:
        comision_display = r["comisiones"][0] if r["comisiones"] else ""
        for item in r.get("temario", []):
            exp = _parse_exp_numero(item.get("numero", ""))
            if not exp:
                continue
            p = idx.get(exp)
            if not p:
                continue
            p.setdefault("reuniones", []).append({
                "fecha": r["fecha_completa"],
                "comision": comision_display,
                "tipo": r["tipo"],
                "iso": r["fecha_iso"],
            })
    for p in proyectos:
        if p.get("reuniones"):
            p["reuniones"].sort(key=lambda x: x["iso"] or "", reverse=True)


def construir_od():
    """Carga data/od.json (generado por scraper_od.py) para embeber en la web."""
    return _cargar("od.json", [])


def construir_sanciones():
    """Carga data/sanciones.json (generado por scraper_sanciones.py) para
    embeber en la web."""
    return _cargar("sanciones.json", [])


RE_LEY_NRO = re.compile(r"Ley N[°º]\s*[\d.]+")


def _fecha_iso_a_dmy(iso):
    partes = (iso or "").split("-")
    if len(partes) != 3:
        return iso or ""
    return f"{partes[2]}/{partes[1]}/{partes[0]}"


def cruzar_proyectos_sanciones(proyectos, sanciones_data):
    """Por cada proyecto, agrega (in place) hasta 3 badges según su
    expediente aparezca en data/sanciones.json (Boletín de Novedades):
      - badge_preferencia: moción de preferencia aprobada.
      - badge_sancionado: sanción/aprobación en ley, acuerdo o
        decreto/res/com/dec (con nro de ley si consta en observaciones).
      - badge_diputados: comunicado a la H. Cámara de Diputados.
    """
    idx = {}
    for it in sanciones_data:
        idx.setdefault(it.get("expediente"), []).append(it)

    for p in proyectos:
        exp = f"{p.get('origen')}-{p.get('nro')}/{str(p.get('anio'))[-2:]}"
        items = idx.get(exp)
        if not items:
            continue
        for it in items:
            seccion = it.get("seccion")
            resultado = (it.get("resultado") or "").upper()
            observaciones = it.get("observaciones") or ""
            fecha = _fecha_iso_a_dmy(it.get("fecha_sesion"))

            if seccion == "preferencia" and "badge_preferencia" not in p:
                p["badge_preferencia"] = {"fecha": fecha, "solicitante": it.get("solicitante")}

            elif seccion in ("ley", "acuerdo", "decreto_res_com_dec") and resultado in ("APROBADO", "APROBADA"):
                if "badge_sancionado" not in p:
                    m = RE_LEY_NRO.search(observaciones)
                    p["badge_sancionado"] = {"fecha": fecha, "ley": m.group(0) if m else None}
                if "Se comunica a la H. Cámara de Diputados" in observaciones and "badge_diputados" not in p:
                    p["badge_diputados"] = {"fecha": fecha}


def cruzar_proyectos_od(proyectos, od_data):
    """Por cada proyecto, agrega (in place) un campo 'od' con la primera OD
    (más reciente) en cuyos expedientes aparece, si tiene alguna."""
    idx = {(p.get("origen"), p.get("nro"), p.get("anio")): p for p in proyectos}
    for o in od_data:
        for exp in o.get("expedientes", []):
            p = idx.get((exp.get("origen"), exp.get("nro"), exp.get("anio")))
            if not p or p.get("od"):
                continue
            p["od"] = {
                "nro_od": o["nro_od"],
                "anio_od": o["anio_od"],
                "url_pdf": o["url_pdf"],
            }


def cruzar_proyectos_acuerdos(proyectos, acuerdos_data):
    """Por cada proyecto de tipo AC, agrega (in place) el estado del acuerdo
    según data/acuerdos.json (migrado a mano desde el CSV de la Prosecretaría):
      - dado_cuenta / fecha_dado_cuenta
      - aprobado_ac / fecha_aprobacion_ac
    """
    idx = {(a["nro"], a["anio"]): a for a in acuerdos_data}
    for p in proyectos:
        if p.get("tipo") != "AC":
            continue
        a = idx.get((p.get("nro"), p.get("anio")))
        if not a:
            continue
        p["dado_cuenta"] = a["dado_cuenta"]
        p["fecha_dado_cuenta"] = a["fecha_dado_cuenta"]
        p["aprobado_ac"] = a["aprobado"]
        p["fecha_aprobacion_ac"] = a["fecha_aprobacion"]


def construir_bloque_totales():
    """Cantidad de senadores vigentes por bloque, según data/senadores.json."""
    senadores = _cargar("senadores.json", {})
    totales = {}
    for datos in senadores.values():
        if not datos.get("vigente"):
            continue
        bloque = datos.get("bloque", "")
        totales[bloque] = totales.get(bloque, 0) + 1
    return totales


def _resolver_firmante(nombre_firmante, bloque_de_senador):
    """Un firmante de dictamen viene como 'Nombre M. Apellido' (orden
    inverso al de senadores.json, que es 'APELLIDO, Nombre'). Prueba el
    apellido como los últimos 3, 2 y 1 términos del nombre (más específico
    primero, para cubrir apellidos compuestos como 'Olivera Lucero' o 'de
    Pedro') armando la clave 'apellido, resto' que espera
    construir_bloque_por_senador(), sin duplicar su lógica de matching.
    Devuelve (apellido_para_ordenar, bloque)."""
    palabras = nombre_firmante.split()
    for k in range(min(3, len(palabras) - 1), 0, -1):
        apellido = " ".join(palabras[-k:])
        resto = " ".join(palabras[:-k])
        bloque = bloque_de_senador(f"{apellido}, {resto}")
        if bloque:
            return apellido, bloque
    return (palabras[-1] if palabras else nombre_firmante), ""


def _firmantes_por_bloque(firmantes, bloque_de_senador):
    por_bloque = {}
    for nombre in firmantes:
        apellido, bloque = _resolver_firmante(nombre, bloque_de_senador)
        por_bloque.setdefault(bloque or "Sin bloque identificado", []).append((apellido, nombre))
    return [
        {
            "bloque": bloque,
            "integrantes": [n for _, n in sorted(nombres, key=lambda x: x[0])],
        }
        for bloque, nombres in sorted(por_bloque.items(), key=lambda x: x[0])
    ]


_LABEL_DISIDENCIA = {"parcial": "En disidencia parcial", "total": "En disidencia total"}
_PARTICULAS_COM = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "E"}
RE_EXP_AM = re.compile(r"^([A-ZÑ.]+)-(\d+)/(\d{2,4})(?:-[A-Z]{2})?$")


def _norm_com_flexible(s):
    """Como _norm_com pero sin partículas (de/del/la/y...): la planilla de
    Ayuda Memoria a veces trae la comisión abreviada o con typos de
    partículas ("Medios Comunicación y Libertad Expresión")."""
    tokens = re.split(r"[ ,]+", _norm_com(s))
    return " ".join(t for t in tokens if t and t not in _PARTICULAS_COM)


def _clave_exp_am(codigo):
    m = RE_EXP_AM.match((codigo or "").strip().upper())
    if not m:
        return None
    anio = int(m.group(3))
    if anio < 100:
        anio += 2000
    return (m.group(1).replace(".", ""), int(m.group(2)), anio)


def construir_ayuda_memoria(proyectos=None):
    """Carga data/ayuda_memoria.json (generado a mano por
    scripts/parse_ayuda_memoria.py mientras el scraper del sitio del Senado
    esté bloqueado por el anti-bot), agrupa los firmantes de cada dictamen
    por bloque político (misma lógica de matching que construir_comisiones())
    y fusiona en un solo registro el dictamen de mayoría (tipoOD "NORMAL") con
    su anexo en minoría (tipoOD "ANEXO") cuando comparten número+período —
    hoy llegan como dos filas separadas del xlsx."""
    items = _cargar("ayuda_memoria.json", [])
    comisiones_oficiales = _cargar("comisiones.json", [])
    bloque_de_senador = construir_bloque_por_senador()
    nombres_com_oficiales = {_norm_com(c["nombre"]): c["nombre"] for c in comisiones_oficiales}
    nombres_com_flex = {_norm_com_flexible(c["nombre"]): c["nombre"] for c in comisiones_oficiales}

    def _com_oficial(nombre):
        return (nombres_com_oficiales.get(_norm_com(nombre))
                or nombres_com_flex.get(_norm_com_flexible(nombre))
                or nombre)

    # Una celda del xlsx admite un solo hipervínculo: en una OD con varios
    # expedientes sólo el primero llega con link. Los demás se completan
    # desde Proyectos (mismo origen/número/año).
    urls_por_exp = {}
    for p in (proyectos or []):
        if p.get("url"):
            urls_por_exp.setdefault((p.get("origen"), p.get("nro"), p.get("anio")), p["url"])
    bloques_por_exp = {
        (p.get("origen"), p.get("nro"), p.get("anio")): p.get("bloques") or []
        for p in (proyectos or [])
    }
    autores_por_exp = {
        (p.get("origen"), p.get("nro"), p.get("anio")): (p.get("autores") or []) + (p.get("coautores") or [])
        for p in (proyectos or [])
    }

    for it in items:
        for e in it.get("expedientes") or []:
            if not e.get("url"):
                e["url"] = urls_por_exp.get(_clave_exp_am(e.get("codigo")))
        # Bloques de los AUTORES de los proyectos dictaminados (no de quienes
        # firman el dictamen): es lo que filtra el selector de bloque.
        claves_exp = [_clave_exp_am(e.get("codigo")) for e in it.get("expedientes") or []]
        autores_det = {}
        for k in claves_exp:
            for nom in autores_por_exp.get(k, []):
                autores_det.setdefault(nom, bloque_de_senador(nom))
        it["autoresDet"] = [
            {"n": nom.title(), "b": b}
            for nom, b in sorted(autores_det.items())
        ]
        bloques = {b for b in autores_det.values() if b}
        if not bloques or not all(autores_det.values()):
            bloques.update(b for k in claves_exp for b in bloques_por_exp.get(k, []))
        it["bloquesAutor"] = sorted(bloques)
        it["comisiones"] = list(dict.fromkeys(_com_oficial(c) for c in (it.get("comisiones") or [])))
        if it.get("comisionCabecera") and it["comisionCabecera"] != "Acuerdos":
            it["comisionCabecera"] = _com_oficial(it["comisionCabecera"])

        firmantes = it.get("firmantesMayoria") or []
        if firmantes:
            it["firmantesPorBloque"] = _firmantes_por_bloque(firmantes, bloque_de_senador)
        # Quienes firmaron "en disidencia" (total/parcial/sin aclarar) vienen
        # aparte de los firmantes de mayoría; se agrupan por bloque igual.
        if it.get("disidencias"):
            it["disidenciasPorBloque"] = [
                {
                    "label": _LABEL_DISIDENCIA.get(d.get("tipo"), "En disidencia"),
                    "firmantesPorBloque": _firmantes_por_bloque(d.get("firmantes") or [], bloque_de_senador),
                }
                for d in it["disidencias"] if d.get("firmantes")
            ]

    grupos = {}
    orden = []
    for it in items:
        clave = (it.get("numero"), it.get("periodo"))
        grupos.setdefault(clave, []).append(it)
        if clave not in orden:
            orden.append(clave)

    resultado = []
    for clave in orden:
        grupo = grupos[clave]
        anexos = [g for g in grupo if g.get("tipoOD") == "ANEXO"]
        normales = [g for g in grupo if g.get("tipoOD") != "ANEXO"]
        base = normales[0] if normales else anexos.pop(0)
        if anexos:
            a = anexos[0]
            base["minoria"] = {
                "odLink": a.get("odLink"),
                "fechaDictamen": a.get("fechaDictamen"),
                "firmantesPorBloque": a.get("firmantesPorBloque") or [],
                "disidenciasPorBloque": a.get("disidenciasPorBloque") or [],
            }
        resultado.append(base)
    resultado.extend(_acuerdos_para_dar_cuenta(proyectos))
    return resultado


def _acuerdos_para_dar_cuenta(proyectos):
    """Pliegos/acuerdos que ingresaron pero todavía no se dieron cuenta en el
    recinto (data/acuerdos.json, dado_cuenta == False). No tienen OD ni
    dictamen: se muestran en Ayuda Memoria como categoría propia."""
    acuerdos = _cargar("acuerdos.json", [])
    pliegos = (_cargar("pliegos_data.json", {}) or {}).get("pliegos") or []
    pliego_de = {p.get("expediente"): p for p in pliegos}
    por_clave = {(p.get("origen"), p.get("nro"), p.get("anio")): p for p in (proyectos or [])}
    out = []
    for a in acuerdos:
        if a.get("dado_cuenta"):
            continue
        pr = por_clave.get((a.get("origen"), a.get("nro"), a.get("anio"))) or {}
        if pr.get("archivado"):
            continue
        anio2 = str(a["anio"])[-2:]
        codigo = "%s-%s/%s" % (a["origen"], a["nro"], anio2)
        texto = (pr.get("extracto") or a.get("caratula") or "").strip()
        if texto.isupper():
            texto = texto[:1] + texto[1:].lower()
        pl = pliego_de.get(codigo)
        out.append({
            "numero": "",
            "periodo": a["anio"],
            "origen": "Poder Ejecutivo",
            "categoria": "Acuerdo para dar cuenta",
            "pendienteCuenta": True,
            "autor": None,
            "descripcion": texto,
            "candidato": (pl.get("candidato") or "").title() or None if pl else None,
            "pliegoSlug": codigo.replace("/", "-") if pl else None,
            "expedientes": [{"codigo": codigo, "url": pr.get("url")}],
            "comisionCabecera": "De Acuerdos",
            "comisiones": ["DE ACUERDOS"],
            "fechaIngreso": pr.get("fecha"),
            "dae": a.get("dae"),
            "tipoOD": "NORMAL",
        })
    out.sort(key=lambda x: (x["periodo"], x["expedientes"][0]["codigo"]), reverse=True)
    return out


def construir_comisiones(proyectos):
    comisiones = _cargar("comisiones.json", [])
    agenda = _cargar("agenda.json", {})
    reuniones = agenda.get("reuniones", [])
    dpp_data = _cargar("dpp_cambios.json", {})
    dpp_cambios = dpp_data.get("cambios", [])
    dpp_fechas = dpp_data.get("fechas", {})
    dpp_state = construir_dpp_state(dpp_cambios)
    bloque_de_senador = construir_bloque_por_senador()
    provincia_de_senador = construir_provincia_por_senador()

    # Fallback de bloque: nombre_norm -> bloque, según el scrape de comisiones.json
    # (por si un senador no aparece en senadores.json).
    bloque_fallback = {}
    for com in comisiones:
        for m in com.get("miembros", []):
            bloque_fallback.setdefault(_norm_nombre(m["nombre"]), m.get("bloque", ""))

    # Conteo de proyectos en trámite por comisión (comisiones[0], normalizado)
    conteo_proyectos = {}
    for p in proyectos:
        coms = p.get("comisiones") or []
        if coms and coms[0]:
            key = _norm_com(coms[0])
            conteo_proyectos[key] = conteo_proyectos.get(key, 0) + 1

    # Próxima reunión futura por comisión (matching por prefijo normalizado,
    # porque agenda.json trae nombres truncados/mayúsculas del boletín)
    ahora = datetime.now()
    proxima = {}
    for r in reuniones:
        fecha_dt = _parse_fecha_agenda(r.get("fecha", ""), r.get("boletin_numero", ""))
        if not fecha_dt or fecha_dt <= ahora:
            continue
        for c_nombre in r.get("comisiones") or []:
            n_ag = _norm_com(c_nombre)
            if not n_ag:
                continue
            for com in comisiones:
                n_com = _norm_com(com["nombre"])
                if n_com.startswith(n_ag) or n_ag.startswith(n_com):
                    prev = proxima.get(com["nombre"])
                    if not prev or fecha_dt < prev["_dt"]:
                        proxima[com["nombre"]] = {
                            "_dt": fecha_dt,
                            "fecha": r.get("fecha", ""),
                            "hora": r.get("hora", ""),
                            "salon": r.get("salon_completo") or r.get("salon", ""),
                            "nExpedientes": len(r.get("temario") or []),
                        }
                    break

    resultado = []
    for com in comisiones:
        nombre = com["nombre"]
        com_norm = _norm_com(nombre)
        # El roster vigente sale del log de DPP (últimos designados), no del
        # scrape de comisiones.json — así todos los integrantes tienen el DPP
        # que los designó y no hay ambigüedad entre fuentes.
        estado_com = dpp_state.get(com_norm, [])
        # Si comisiones.json fue sincronizado con el Senado (scraper_comisiones.py marca
        # "fuente": "senado"), el roster y los cargos salen de ahí; del log de DPP se
        # toma solo el número de decreto (insignia) y el historial de cada integrante.
        desde_senado = com.get("fuente") == "senado"
        if desde_senado:
            estado_com = []
            for m in com.get("miembros", []):
                dpp_m = ""
                for d in dpp_state.get(com_norm, []):
                    if _nombres_coinciden(d["nombre"], m["nombre"]):
                        dpp_m = d["dpp"]
                        break
                estado_com.append({"nombre": m["nombre"], "dpp": dpp_m, "rol": m.get("rol") or "Vocal"})
        integrantes = []
        for e in estado_com:
            nom_norm = _norm_nombre(e["nombre"])
            hist = [
                {
                    "dpp": c["dpp"],
                    "fecha": dpp_fechas.get(c["dpp"], ""),
                    "tipo": c["tipo"],
                    "reemplaza": c.get("reemplaza", ""),
                }
                for c in dpp_cambios
                if _norm_com(c["comision"]) == com_norm
                and (_nombres_coinciden(c.get("senador", ""), e["nombre"])
                     or _nombres_coinciden(c.get("reemplaza", ""), e["nombre"]))
            ]
            bloque = bloque_de_senador(e["nombre"]) or bloque_fallback.get(nom_norm, "")
            integrantes.append({
                "nombre": e["nombre"],
                "bloque": bloque,
                "provincia": provincia_de_senador(e["nombre"]),
                "rol": e["rol"] if desde_senado else _rol_de(nombre, e["nombre"]),
                "dpp": e["dpp"],
                "hist": hist,
            })
        # Presidente/Vice/Secretario primero, luego Vocales
        orden_rol = {"Presidente": 0, "Vicepresidente": 1, "Secretario": 2, "Vocal": 3}
        integrantes.sort(key=lambda x: orden_rol.get(x["rol"], 9))

        pr = proxima.get(nombre)
        resultado.append({
            "nombre": nombre,
            "cupo": com.get("cupo", 0),
            "integrantes": integrantes,
            "nProyectos": conteo_proyectos.get(_norm_com(nombre), 0),
            "proximaReunion": {
                "fecha": pr["fecha"], "hora": pr["hora"],
                "salon": pr["salon"], "nExpedientes": pr["nExpedientes"],
            } if pr else None,
        })
    return resultado


def parse_fecha_sort(fecha_str):
    """Convierte 'DD/MM/AAAA' a 'AAAAMMDD' para orden cronológico."""
    if not fecha_str:
        return "00000000"
    parts = fecha_str.split("/")
    if len(parts) == 3:
        return f"{parts[2]}{parts[1].zfill(2)}{parts[0].zfill(2)}"
    return "00000000"


def _dpp_ultimo_txt(dpp_data):
    fechas = dpp_data.get("fechas", {})
    if not fechas:
        return ""
    def _clave(item):
        try:
            numero, anio = item[0].split("/")
            return (int(anio), int(numero))
        except ValueError:
            return (0, 0)
    numero, fecha = max(fechas.items(), key=_clave)
    return f"&Uacute;ltimo DPP: {numero} ({fecha})"


def _agenda_ultimo_boletin_txt(agenda):
    numeros = {r["boletin_numero"] for r in agenda if r.get("boletin_numero")}
    if not numeros:
        return ""
    def _clave(numero):
        try:
            n, anio = numero.split("/")
            return (int(anio), int(n))
        except ValueError:
            return (0, 0)
    ultimo = max(numeros, key=_clave)
    return f"&Uacute;ltimo bolet&iacute;n: {ultimo}"


PLIEGOS_URL = "https://raw.githubusercontent.com/bonifaciomariano/Pliegos-Poder-Judicial/main/pliegos_data.json"
PLIEGOS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pliegos")


def _cargar_pliegos_base():
    """Datos de la pestaña "Pliegos judiciales".

    Se mantienen en el repo Pliegos-Poder-Judicial (su pipeline arma
    pliegos_data.json); acá NO se edita nada a mano. En cada build se baja la
    última versión y se guarda como data/pliegos_data.json -- copia exacta
    del original, para que el sitio se pueda construir igual si GitHub no
    responde (y para ver en el historial qué cambió). PLIEGOS_OFFLINE=1 saltea
    la descarga (desarrollo sin red)."""
    cache = os.path.join(DATA_DIR, "pliegos_data.json")
    if os.getenv("PLIEGOS_OFFLINE") != "1":
        try:
            req = urllib.request.Request(PLIEGOS_URL, headers={
                "User-Agent": "HSN-SistemaLegislativo/1.0 (+https://github.com/bonifaciomariano/hsn-sistema-legislativo)"})
            with urllib.request.urlopen(req, timeout=30) as r:
                crudo = r.read()
            data = json.loads(crudo.decode("utf-8"))
            if isinstance(data.get("pliegos"), list) and data["pliegos"]:
                with open(cache, "wb") as f:
                    f.write(crudo)
                print(f"  pliegos: {len(data['pliegos'])} bajados del repo de origen (datos al {data.get('generado_al')})")
                return data
            print("  AVISO pliegos: el JSON de origen vino sin pliegos; uso la ultima copia")
        except Exception as e:
            print(f"  AVISO pliegos: no se pudo bajar ({e}); uso la ultima copia")
    data = _cargar("pliegos_data.json", None)
    if data and data.get("pliegos"):
        return data
    return {"generado_al": "", "total": 0, "provincias": [], "pliegos": []}


def _superponer_senado(data):
    """Corrige la planilla de Pliegos con lo que dice el Senado (data/pliegos_senado.json,
    lo escribe scripts/scraper_pliegos.py). Solo adelanta etapas, nunca las retrasa:
      - dado cuenta: si la planilla no tiene fecha y el Senado sí, la completa
      - orden del día: si la planilla no la tiene y el Senado sí, la completa
      - sanción / rechazo: si el Senado informa la resolución, la completa
    Después recalcula la categoría con el mismo orden de prioridad que data_builder.py.
    La planilla de origen no se modifica; si el archivo no existe, no hace nada."""
    s = _cargar("pliegos_senado.json", None)
    if not s or not s.get("pliegos"):
        return data
    por_exp = s["pliegos"]
    cambios = 0

    def _categoria(tl):
        if not (tl.get("dado_cuenta") or {}).get("fecha"):
            return "dar_cuenta"
        if tl.get("sancion"):
            return "sancionado"
        if tl.get("rechazo"):
            return "rechazado"
        if tl.get("orden_del_dia"):
            return "con_od"
        return "sin_audiencia"

    # Pliegos judiciales que el Senado ya recibió y la planilla todavía no tiene (los detecta scraper_pliegos.py)
    existentes = {p.get("expediente") for p in data.get("pliegos", [])}
    agregados = []
    for exp, z in por_exp.items():
        n = z.get("nuevo")
        if not n or exp in existentes:
            continue
        tl = {
            "ingreso": z.get("ingreso"),
            "dado_cuenta": {"sesion": (z.get("dae") or "").split("/")[0], "fecha": z.get("dado_cuenta")},
            "audiencia": None,
            "orden_del_dia": ({"numero": z["od"]["numero"], "anio": z["od"].get("anio") or "",
                               "fecha_dictamen": z["od"].get("fecha"), "firmantes": None} if z.get("od") else None),
            "sancion": z.get("sancion_fecha") if z.get("sancion") == "aprobada" else None,
            "rechazo": z.get("sancion_fecha") if z.get("sancion") == "rechazada" else None,
        }
        agregados.append({
            "expediente": exp, "url": n["url"], "candidato": n["candidato"], "cargo": n["cargo"],
            "provincia": n["provincia"], "rango": n["rango"], "fuero": n["fuero"],
            "categoria": _categoria(tl), "timeline": tl,
            "audiencia_programada": None, "audiencia_sin_dictamen": False,
        })
        print("  pliegos: NUEVO %s (%s) agregado desde el Senado" % (exp, n["candidato"]))
    if agregados:
        def _clave(p):
            m = re.match(r"PE-(\d+)/(\d{2})", p.get("expediente", ""))
            return (int(m.group(2)), int(m.group(1))) if m else (0, 0)
        data["pliegos"] = sorted(list(data.get("pliegos", [])) + agregados, key=_clave, reverse=True)
        data["total"] = len(data["pliegos"])
        provs = set(data.get("provincias") or []) | {a["provincia"] for a in agregados}
        data["provincias"] = sorted(provs, key=lambda x: "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn"))

    for p in data.get("pliegos", []):
        z = por_exp.get(p.get("expediente"))
        if not z:
            continue
        tl = p.setdefault("timeline", {})
        antes = p.get("categoria")
        dc = tl.get("dado_cuenta") or {}
        if not dc.get("fecha") and z.get("dado_cuenta"):
            tl["dado_cuenta"] = {"sesion": dc.get("sesion") or (z.get("dae") or "").split("/")[0], "fecha": z["dado_cuenta"]}
        if not tl.get("orden_del_dia") and z.get("od"):
            tl["orden_del_dia"] = {"numero": z["od"]["numero"], "anio": z["od"].get("anio") or "",
                                   "fecha_dictamen": z["od"].get("fecha"), "firmantes": None}
        if z.get("sancion") == "aprobada" and not tl.get("sancion"):
            tl["sancion"] = z.get("sancion_fecha")
        elif z.get("sancion") == "rechazada" and not tl.get("rechazo"):
            tl["rechazo"] = z.get("sancion_fecha")
        cat = _categoria(tl)
        p["categoria"] = cat
        if cat != antes:
            cambios += 1
            print("  pliegos: %s pasa de %s a %s (según el Senado)" % (p.get("expediente"), antes, cat))
    if cambios:
        print("  pliegos: %d actualizados con datos del Senado (%s)" % (cambios, s.get("generado", "")))
    return data


def cargar_pliegos():
    return _superponer_senado(_cargar_pliegos_base())


def _leer_asset_pliegos(nombre):
    with open(os.path.join(PLIEGOS_DIR, nombre), encoding="utf-8") as f:
        return f.read()


def aplicar_bloque_actual(proyectos):
    """El bloque que se muestra en Proyectos es el bloque ACTUAL del autor/a (data/senadores.json),
    no el que tenía al presentar el proyecto ni el que quedó guardado cuando se leyó el expediente.
    Si no se puede resolver (p. ej. ex-senadores que ya no están en el padrón), se deja el valor
    que ya tenía. El bloque anterior queda en "bloques_historico" solo si cambió."""
    buscar = construir_bloque_por_senador()
    cambios = 0
    for p in proyectos:
        autores = p.get("autores") or []
        if not autores:
            continue
        actuales, vistos = [], set()
        for a in autores:
            b = buscar(a)
            if b and b not in vistos:
                vistos.add(b)
                actuales.append(b)
        if not actuales:
            continue
        previo = [b for b in (p.get("bloques") or []) if b]
        def k(x):
            return _norm_nombre(x).replace(" POR ", " ")
        if sorted({k(x) for x in actuales}) != sorted({k(x) for x in previo}):
            p["bloques_historico"] = previo
            p["bloques"] = actuales
            cambios += 1
    print(f"  -> bloque actual del autor aplicado: {cambios} proyecto(s) cambiaron de bloque")
    return proyectos


def main():
    proyectos = _cargar("proyectos.json", [])
    # Orden: fecha ↓, luego año y número (más nuevo a más viejo)
    proyectos = sorted(
        proyectos,
        key=lambda x: (parse_fecha_sort(x.get("fecha", "")), x.get("anio", 0), x.get("nro", 0)),
        reverse=True,
    )

    total = len(proyectos)
    tipos_count = {}
    for p in proyectos:
        tipos_count[p.get("tipo", "")] = tipos_count.get(p.get("tipo", ""), 0) + 1

    comisiones_oficiales = _cargar("comisiones.json", [])
    agenda_procesada = construir_agenda(comisiones_oficiales)
    cruzar_proyectos_agenda(proyectos, agenda_procesada)

    od_procesada = construir_od()
    cruzar_proyectos_od(proyectos, od_procesada)

    sanciones_procesada = construir_sanciones()
    cruzar_proyectos_sanciones(proyectos, sanciones_procesada)

    acuerdos_procesados = _cargar("acuerdos.json", [])
    cruzar_proyectos_acuerdos(proyectos, acuerdos_procesados)

    ayuda_memoria_procesada = construir_ayuda_memoria(proyectos)

    dpp_data = _cargar("dpp_cambios.json", {})
    dpp_ultimo_txt = _dpp_ultimo_txt(dpp_data)
    com_hint = "Senado de la Naci&oacute;n"
    if dpp_ultimo_txt:
        com_hint += " &middot; " + dpp_ultimo_txt

    agenda_ultimo_txt = _agenda_ultimo_boletin_txt(agenda_procesada)
    agenda_hint = "Boletines de comisiones del HSN"
    if agenda_ultimo_txt:
        agenda_hint += " &middot; " + agenda_ultimo_txt

    # Campos de trazabilidad que usan sólo las páginas por bloque (repo Prosecretaria-
    # Parlamentaria-HSN): no se embeben acá para no agrandar el HTML principal.
    solo_bloques = {"autores_caratula", "bloques_caratula", "od_trazabilidad",
                    "fecha_dictamen", "sanciones_trazabilidad", "firmantes_trazabilidad"}
    proyectos = aplicar_bloque_actual(proyectos)
    datos_js = json.dumps([{k: v for k, v in p.items() if k not in solo_bloques} for p in proyectos],
                          ensure_ascii=False)
    comisiones_js = json.dumps(construir_comisiones(proyectos), ensure_ascii=False)
    agenda_js = json.dumps(agenda_procesada, ensure_ascii=False)
    ayuda_memoria_js = json.dumps(ayuda_memoria_procesada, ensure_ascii=False)
    sanciones_js = json.dumps(sanciones_procesada, ensure_ascii=False)
    bloque_totales_js = json.dumps(construir_bloque_totales(), ensure_ascii=False)
    fotos_senadores_raw = _cargar("fotos_senadores.json", {})
    fotos_por_nombre_norm = {}
    for k, v in fotos_senadores_raw.items():
        fotos_por_nombre_norm[_norm_nombre(k)] = v
        # El roster de comisiones (log de DPP) a veces usa sólo uno de los
        # nombres de pila y no necesariamente el primero ("REJAL, Fernando"
        # en vez de "REJAL, Jesús Fernando") -- se indexa también por
        # apellido + cada palabra individual del nombre para que la foto
        # igual aparezca.
        apellido, _, nombre = k.partition(",")
        for palabra in nombre.strip().split(" "):
            if palabra:
                clave_corta = _norm_nombre(f"{apellido}, {palabra}")
                fotos_por_nombre_norm.setdefault(clave_corta, v)
    fotos_senadores_js = json.dumps(fotos_por_nombre_norm, ensure_ascii=False)
    pliegos = cargar_pliegos()
    pliegos_js = json.dumps(pliegos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    fonts = _cargar("fonts_poppins.json", {})
    fecha = datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=-3))).strftime("%d/%m/%Y %H:%M")

    html = HTML_TEMPLATE.format(
        css=CSS + _leer_asset_pliegos("pliegos.css"),
        js=JS + _leer_asset_pliegos("pliegos.js"),
        pliegos_html=_leer_asset_pliegos("pliegos.html"),
        pliegos_data=pliegos_js,
        datos=datos_js,
        comisiones=comisiones_js,
        agenda=agenda_js,
        ayuda_memoria=ayuda_memoria_js,
        sanciones=sanciones_js,
        bloque_totales=bloque_totales_js,
        fotos_senadores=fotos_senadores_js,
        font_regular=fonts.get("regular", ""),
        font_bold=fonts.get("bold", ""),
        fecha=fecha,
        com_hint=com_hint,
        agenda_hint=agenda_hint,
        total=total,
        pl=tipos_count.get("PL", 0),
        pd=tipos_count.get("PD", 0),
        otros=total - tipos_count.get("PL", 0) - tipos_count.get("PD", 0),
    )

    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(html)

    mb = len(html.encode("utf-8")) / (1024 * 1024)
    print(f"index.html generado: {len(html):,} bytes ({mb:.2f} MB)")
    print(f"  -> {total} proyectos | {tipos_count.get('PL', 0)} PL | "
          f"{tipos_count.get('PD', 0)} PD | otros {total - tipos_count.get('PL', 0) - tipos_count.get('PD', 0)}")
    if mb > 15:
        print(f"  ADVERTENCIA: el HTML supera 15 MB ({mb:.2f} MB) -- considerar paginacion.")


if __name__ == "__main__":
    main()
