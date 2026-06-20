<template>
  <div class="leaderboard">
    <div v-for="(agent, i) in top10" :key="agent.agent_id" class="lb-row">
      <div class="lb-rank">{{ i + 1 }}</div>
      <div class="lb-name" :title="agent.agent_name">{{ agent.agent_name }}</div>
      <div class="lb-bars">
        <div class="bar-wrap">
          <div class="bar bar-t" :style="{ width: pct(agent.twitter_actions) + '%' }" title="Info Plaza"></div>
          <div class="bar bar-r" :style="{ width: pct(agent.reddit_actions) + '%' }" title="Topic Community"></div>
        </div>
        <span class="lb-total">{{ agent.total_actions }}</span>
      </div>
    </div>
    <div v-if="!top10.length" class="empty">No agent data yet</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  agents: { type: Array, default: () => [] }
})

const top10 = computed(() =>
  [...props.agents]
    .sort((a, b) => (b.total_actions || 0) - (a.total_actions || 0))
    .slice(0, 10)
)

const maxTotal = computed(() => Math.max(...top10.value.map(a => a.total_actions || 0), 1))

function pct(val) {
  return Math.round(((val || 0) / maxTotal.value) * 100)
}
</script>

<style scoped>
.leaderboard { display: flex; flex-direction: column; gap: 8px; }
.lb-row { display: flex; align-items: center; gap: 10px; font-size: 12px; }
.lb-rank { width: 18px; text-align: right; color: #555; flex-shrink: 0; }
.lb-name { width: 130px; color: #bbb; white-space: nowrap; overflow: hidden;
           text-overflow: ellipsis; flex-shrink: 0; }
.lb-bars { flex: 1; display: flex; align-items: center; gap: 8px; }
.bar-wrap { flex: 1; display: flex; flex-direction: column; gap: 3px; }
.bar { height: 5px; border-radius: 3px; min-width: 2px; transition: width 0.4s; }
.bar-t { background: #60a5fa; }
.bar-r { background: #fb923c; }
.lb-total { width: 36px; text-align: right; color: #a78bfa; font-variant-numeric: tabular-nums; }
.empty { color: #555; font-size: 13px; text-align: center; padding: 1rem; }
</style>
