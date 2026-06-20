<template>
  <div class="donut-wrap">
    <svg ref="svgRef" :width="size" :height="size"></svg>
    <div class="legend">
      <div v-for="(item, i) in slices" :key="item.label" class="legend-row">
        <span class="swatch" :style="{ background: colors[i % colors.length] }"></span>
        <span class="lbl">{{ item.label }}</span>
        <span class="cnt">{{ item.value }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, nextTick, computed } from 'vue'
import * as d3 from 'd3'

const props = defineProps({
  agents: { type: Array, default: () => [] }
})

const svgRef = ref(null)
const size = 180

const colors = ['#a78bfa','#60a5fa','#34d399','#fb923c','#f472b6','#facc15','#94a3b8']

const slices = computed(() => {
  const counts = {}
  for (const agent of props.agents) {
    for (const [action, count] of Object.entries(agent.action_types || {})) {
      counts[action] = (counts[action] || 0) + count
    }
  }
  return Object.entries(counts)
    .map(([label, value]) => ({ label, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 7)
})

function draw() {
  if (!svgRef.value || !slices.value.length) return
  const svg = d3.select(svgRef.value)
  svg.selectAll('*').remove()

  const r = size / 2
  const inner = r * 0.55
  const g = svg.append('g').attr('transform', `translate(${r},${r})`)

  const pie = d3.pie().value(d => d.value).sort(null)
  const arc = d3.arc().innerRadius(inner).outerRadius(r - 4)
  const arcHover = d3.arc().innerRadius(inner).outerRadius(r)

  const arcs = g.selectAll('path').data(pie(slices.value)).enter().append('path')
    .attr('d', arc)
    .attr('fill', (_, i) => colors[i % colors.length])
    .attr('stroke', '#0f1117').attr('stroke-width', 2)
    .on('mouseover', function() { d3.select(this).attr('d', arcHover) })
    .on('mouseout', function() { d3.select(this).attr('d', arc) })

  // Center total
  const total = slices.value.reduce((s, d) => s + d.value, 0)
  g.append('text').attr('text-anchor', 'middle').attr('dy', '-0.2em')
    .attr('fill', '#e0e0e0').attr('font-size', '20px').attr('font-weight', '600')
    .text(total)
  g.append('text').attr('text-anchor', 'middle').attr('dy', '1.2em')
    .attr('fill', '#666').attr('font-size', '10px').text('actions')
}

onMounted(() => nextTick(draw))
watch(() => props.agents, () => nextTick(draw), { deep: true })
</script>

<style scoped>
.donut-wrap { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
svg { flex-shrink: 0; }
.legend { display: flex; flex-direction: column; gap: 6px; }
.legend-row { display: flex; align-items: center; gap: 6px; font-size: 11px; }
.swatch { width: 10px; height: 10px; border-radius: 2px; flex-shrink: 0; }
.lbl { color: #aaa; flex: 1; white-space: nowrap; }
.cnt { color: #a78bfa; font-variant-numeric: tabular-nums; min-width: 32px; text-align: right; }
</style>
