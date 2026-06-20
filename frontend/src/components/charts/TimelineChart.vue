<template>
  <div class="timeline-chart-wrap">
    <svg ref="svgRef" :width="width" :height="height"></svg>
    <div v-if="tooltip.visible" class="chart-tooltip" :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }">
      <div class="tt-round">Round {{ tooltip.round }}</div>
      <div class="tt-row tt-blue">Info Plaza: <b>{{ tooltip.twitter }}</b></div>
      <div class="tt-row tt-orange">Topic Community: <b>{{ tooltip.reddit }}</b></div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted, nextTick } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  rounds: { type: Array, default: () => [] }
})

const svgRef = ref(null)
const width = ref(600)
const height = 220
const tooltip = ref({ visible: false, x: 0, y: 0, round: 0, twitter: 0, reddit: 0 })

let ro = null

function draw() {
  if (!svgRef.value || !props.rounds.length) return

  const margin = { top: 16, right: 20, bottom: 36, left: 44 }
  const W = width.value - margin.left - margin.right
  const H = height - margin.top - margin.bottom

  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`)

  const x = d3.scaleLinear()
    .domain([0, d3.max(props.rounds, d => d.round_num) || 1])
    .range([0, W])

  const maxY = d3.max(props.rounds, d => Math.max(d.twitter_actions || 0, d.reddit_actions || 0)) || 1
  const y = d3.scaleLinear().domain([0, maxY * 1.1]).range([H, 0])

  // Grid lines
  g.append('g').attr('class', 'grid')
    .call(d3.axisLeft(y).ticks(4).tickSize(-W).tickFormat(''))
    .call(gg => {
      gg.select('.domain').remove()
      gg.selectAll('.tick line').attr('stroke', '#2a2a3a').attr('stroke-dasharray', '3,3')
    })

  // Axes
  g.append('g').attr('transform', `translate(0,${H})`)
    .call(d3.axisBottom(x).ticks(Math.min(props.rounds.length, 8)).tickFormat(d => `R${d}`))
    .call(gg => {
      gg.select('.domain').attr('stroke', '#3a3a4a')
      gg.selectAll('.tick line').attr('stroke', '#3a3a4a')
      gg.selectAll('text').attr('fill', '#666').attr('font-size', '11px')
    })

  g.append('g')
    .call(d3.axisLeft(y).ticks(4))
    .call(gg => {
      gg.select('.domain').attr('stroke', '#3a3a4a')
      gg.selectAll('.tick line').attr('stroke', '#3a3a4a')
      gg.selectAll('text').attr('fill', '#666').attr('font-size', '11px')
    })

  const lineT = d3.line().x(d => x(d.round_num)).y(d => y(d.twitter_actions || 0)).curve(d3.curveMonotoneX)
  const lineR = d3.line().x(d => x(d.round_num)).y(d => y(d.reddit_actions || 0)).curve(d3.curveMonotoneX)

  // Area fills
  const areaT = d3.area().x(d => x(d.round_num)).y0(H).y1(d => y(d.twitter_actions || 0)).curve(d3.curveMonotoneX)
  const areaR = d3.area().x(d => x(d.round_num)).y0(H).y1(d => y(d.reddit_actions || 0)).curve(d3.curveMonotoneX)

  const defs = svg.append('defs')
  const gradT = defs.append('linearGradient').attr('id', 'gradT').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 1)
  gradT.append('stop').attr('offset', '0%').attr('stop-color', '#60a5fa').attr('stop-opacity', 0.25)
  gradT.append('stop').attr('offset', '100%').attr('stop-color', '#60a5fa').attr('stop-opacity', 0)
  const gradR = defs.append('linearGradient').attr('id', 'gradR').attr('x1', 0).attr('y1', 0).attr('x2', 0).attr('y2', 1)
  gradR.append('stop').attr('offset', '0%').attr('stop-color', '#fb923c').attr('stop-opacity', 0.2)
  gradR.append('stop').attr('offset', '100%').attr('stop-color', '#fb923c').attr('stop-opacity', 0)

  g.append('path').datum(props.rounds).attr('fill', 'url(#gradT)').attr('d', areaT)
  g.append('path').datum(props.rounds).attr('fill', 'url(#gradR)').attr('d', areaR)
  g.append('path').datum(props.rounds).attr('fill', 'none').attr('stroke', '#60a5fa').attr('stroke-width', 2).attr('d', lineT)
  g.append('path').datum(props.rounds).attr('fill', 'none').attr('stroke', '#fb923c').attr('stroke-width', 2).attr('d', lineR)

  // Hover overlay
  const bisect = d3.bisector(d => d.round_num).left
  const overlay = g.append('rect').attr('fill', 'transparent').attr('width', W).attr('height', H)
    .attr('cursor', 'crosshair')

  const vline = g.append('line').attr('stroke', '#555').attr('stroke-width', 1)
    .attr('stroke-dasharray', '4,4').attr('y1', 0).attr('y2', H).attr('opacity', 0)

  overlay.on('mousemove', (event) => {
    const [mx] = d3.pointer(event)
    const round = x.invert(mx)
    const i = bisect(props.rounds, round, 1)
    const d = props.rounds[Math.min(i, props.rounds.length - 1)]
    if (!d) return
    vline.attr('x1', x(d.round_num)).attr('x2', x(d.round_num)).attr('opacity', 1)
    const rect = svgRef.value.getBoundingClientRect()
    tooltip.value = {
      visible: true,
      x: event.clientX - rect.left + 12,
      y: event.clientY - rect.top - 20,
      round: d.round_num,
      twitter: d.twitter_actions || 0,
      reddit: d.reddit_actions || 0,
    }
  }).on('mouseleave', () => {
    vline.attr('opacity', 0)
    tooltip.value.visible = false
  })

  // Legend
  const legend = g.append('g').attr('transform', `translate(${W - 190}, -4)`)
  legend.append('line').attr('x1', 0).attr('y1', 7).attr('x2', 18).attr('y2', 7).attr('stroke', '#60a5fa').attr('stroke-width', 2)
  legend.append('text').attr('x', 22).attr('y', 11).attr('fill', '#666').attr('font-size', '11px').text('Info Plaza')
  legend.append('line').attr('x1', 100).attr('y1', 7).attr('x2', 118).attr('y2', 7).attr('stroke', '#fb923c').attr('stroke-width', 2)
  legend.append('text').attr('x', 122).attr('y', 11).attr('fill', '#666').attr('font-size', '11px').text('Topic Comm.')
}

function updateWidth() {
  if (svgRef.value) {
    width.value = svgRef.value.parentElement?.offsetWidth || 600
    draw()
  }
}

onMounted(() => {
  updateWidth()
  ro = new ResizeObserver(updateWidth)
  if (svgRef.value?.parentElement) ro.observe(svgRef.value.parentElement)
})

onUnmounted(() => ro?.disconnect())
watch(() => props.rounds, () => nextTick(draw), { deep: true })
</script>

<style scoped>
.timeline-chart-wrap { position: relative; width: 100%; }
svg { display: block; width: 100%; }
.chart-tooltip {
  position: absolute; pointer-events: none;
  background: #1e1e2e; border: 1px solid #3a3a4a; border-radius: 6px;
  padding: 8px 12px; font-size: 12px; white-space: nowrap; z-index: 10;
}
.tt-round { color: #888; margin-bottom: 4px; font-size: 11px; }
.tt-row { color: #ccc; }
.tt-blue b { color: #60a5fa; }
.tt-orange b { color: #fb923c; }
</style>
