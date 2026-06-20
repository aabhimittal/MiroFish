<template>
  <div class="results-dashboard">
    <div class="dash-header">
      <span class="dash-title">SIMULATION RESULTS</span>
      <span class="dash-id">{{ simulationId }}</span>
    </div>

    <!-- KPI Cards -->
    <div class="kpi-row">
      <div class="kpi-card">
        <div class="kpi-value">{{ fmt(totalActions) }}</div>
        <div class="kpi-label">Total Actions</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ fmt(peakRoundActions) }}</div>
        <div class="kpi-label">Peak Round</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ fmt(activeAgentCount) }}</div>
        <div class="kpi-label">Active Agents</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-value">{{ duration }}</div>
        <div class="kpi-label">Duration</div>
      </div>
    </div>

    <!-- Charts row -->
    <div class="charts-row">
      <div class="chart-card wide">
        <div class="card-title">Actions per Round</div>
        <TimelineChart :rounds="rounds" />
      </div>
      <div class="chart-card">
        <div class="card-title">Action Distribution</div>
        <ActionTypeChart :agents="agents" />
      </div>
    </div>

    <!-- Leaderboard + Posts -->
    <div class="bottom-row">
      <div class="chart-card">
        <div class="card-title">Agent Leaderboard</div>
        <div class="legend-hint">
          <span class="dot dot-blue"></span> Info Plaza
          <span class="dot dot-orange"></span> Topic Community
        </div>
        <AgentLeaderboard :agents="agents" />
      </div>
      <div class="chart-card wide">
        <div class="card-title">
          Top Posts
          <span class="platform-toggle">
            <button :class="{ active: postPlatform === 'all' }" @click="postPlatform = 'all'">All</button>
            <button :class="{ active: postPlatform === 'twitter' }" @click="postPlatform = 'twitter'">Info Plaza</button>
            <button :class="{ active: postPlatform === 'reddit' }" @click="postPlatform = 'reddit'">Topic Comm.</button>
          </span>
        </div>
        <div class="posts-feed" v-if="filteredPosts.length">
          <div v-for="post in filteredPosts" :key="post.post_id" class="post-card">
            <div class="post-header">
              <span class="post-badge" :class="post.platform">{{ post.platform === 'twitter' ? 'Info Plaza' : 'Topic Comm.' }}</span>
              <span class="post-agent">{{ post.agent_name || post.user_name || 'Agent' }}</span>
              <span class="post-likes">♥ {{ post.num_likes || 0 }}</span>
            </div>
            <div class="post-content">{{ truncate(post.content, 180) }}</div>
          </div>
        </div>
        <div v-else class="empty-posts">No posts available yet</div>
      </div>
    </div>

    <div v-if="loading" class="dash-loading">Loading simulation data…</div>
    <div v-if="error" class="dash-error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import TimelineChart from './charts/TimelineChart.vue'
import AgentLeaderboard from './charts/AgentLeaderboard.vue'
import ActionTypeChart from './charts/ActionTypeChart.vue'
import { getSimulationTimeline, getAgentStats, getSimulationPosts, getRunStatus } from '../api/simulation'

const props = defineProps({
  simulationId: { type: String, required: true }
})

const rounds = ref([])
const agents = ref([])
const posts = ref([])
const runState = ref(null)
const loading = ref(false)
const error = ref('')
const postPlatform = ref('all')

const totalActions = computed(() => (runState.value?.twitter_actions_count || 0) + (runState.value?.reddit_actions_count || 0))
const peakRoundActions = computed(() => rounds.value.reduce((m, r) => Math.max(m, (r.twitter_actions || 0) + (r.reddit_actions || 0)), 0))
const activeAgentCount = computed(() => agents.value.filter(a => (a.total_actions || 0) > 0).length)
const duration = computed(() => {
  const rs = runState.value
  if (!rs?.started_at) return '—'
  const end = rs.completed_at ? new Date(rs.completed_at) : new Date()
  const mins = Math.round((end - new Date(rs.started_at)) / 60000)
  return mins < 60 ? `${mins}m` : `${Math.floor(mins / 60)}h ${mins % 60}m`
})

const filteredPosts = computed(() => {
  const sorted = [...posts.value].sort((a, b) => (b.num_likes || 0) - (a.num_likes || 0))
  if (postPlatform.value === 'all') return sorted.slice(0, 10)
  return sorted.filter(p => p.platform === postPlatform.value).slice(0, 10)
})

function fmt(n) { return n === undefined || n === null ? '—' : n.toLocaleString() }
function truncate(text, len) { return text && text.length > len ? text.slice(0, len) + '…' : (text || '') }

async function loadData() {
  if (!props.simulationId) return
  loading.value = true
  error.value = ''
  try {
    const [tl, as, pt, rs] = await Promise.allSettled([
      getSimulationTimeline(props.simulationId),
      getAgentStats(props.simulationId),
      getSimulationPosts(props.simulationId, 'reddit', 100, 0),
      getRunStatus(props.simulationId),
    ])

    if (tl.status === 'fulfilled') rounds.value = tl.value.data?.data?.rounds || []
    if (as.status === 'fulfilled') agents.value = as.value.data?.data?.agents || []
    if (pt.status === 'fulfilled') {
      const rPosts = (pt.value.data?.data?.posts || []).map(p => ({ ...p, platform: 'reddit' }))
      // Also fetch twitter posts
      try {
        const tRes = await getSimulationPosts(props.simulationId, 'twitter', 100, 0)
        const tPosts = (tRes.data?.data?.posts || []).map(p => ({ ...p, platform: 'twitter' }))
        posts.value = [...rPosts, ...tPosts]
      } catch {
        posts.value = rPosts
      }
    }
    if (rs.status === 'fulfilled') runState.value = rs.value.data?.data || null
  } catch (e) {
    error.value = 'Failed to load dashboard data'
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
watch(() => props.simulationId, loadData)
</script>

<style scoped>
.results-dashboard {
  background: #0f1117;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.dash-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.dash-title { font-size: 11px; letter-spacing: 0.1em; color: #a78bfa; font-weight: 600; }
.dash-id { font-size: 11px; color: #444; font-family: monospace; }

/* KPI */
.kpi-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.kpi-card {
  flex: 1; min-width: 110px;
  background: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 8px;
  padding: 1rem; text-align: center;
}
.kpi-value { font-size: 1.6rem; font-weight: 700; color: #e2e8f0; font-variant-numeric: tabular-nums; }
.kpi-label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.08em; color: #555; margin-top: 4px; }

/* Chart cards */
.charts-row, .bottom-row { display: flex; gap: 1rem; flex-wrap: wrap; }
.chart-card {
  background: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 8px;
  padding: 1rem 1.25rem; flex: 1; min-width: 260px;
}
.chart-card.wide { flex: 2; min-width: 320px; }
.card-title {
  font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em;
  color: #666; margin-bottom: 12px; display: flex; align-items: center;
  justify-content: space-between; gap: 8px;
}

/* Legend hint */
.legend-hint { display: flex; gap: 12px; align-items: center; font-size: 11px; color: #555; margin-bottom: 10px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
.dot-blue { background: #60a5fa; }
.dot-orange { background: #fb923c; }

/* Platform toggle */
.platform-toggle { display: flex; gap: 4px; }
.platform-toggle button {
  background: none; border: 1px solid #2a2a3a; color: #555;
  font-size: 10px; padding: 2px 8px; border-radius: 4px; cursor: pointer;
}
.platform-toggle button.active { border-color: #a78bfa; color: #a78bfa; }

/* Posts feed */
.posts-feed { display: flex; flex-direction: column; gap: 8px; max-height: 340px; overflow-y: auto; }
.post-card {
  background: #0f1117; border: 1px solid #2a2a3a; border-radius: 6px;
  padding: 10px 12px;
}
.post-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 11px; }
.post-badge {
  padding: 2px 6px; border-radius: 3px; font-size: 10px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.05em;
}
.post-badge.twitter { background: #1e3a5f; color: #60a5fa; }
.post-badge.reddit { background: #3a1f0f; color: #fb923c; }
.post-agent { color: #888; flex: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.post-likes { color: #f472b6; margin-left: auto; }
.post-content { font-size: 12px; color: #bbb; line-height: 1.5; }
.empty-posts { color: #444; font-size: 13px; text-align: center; padding: 2rem; }

.dash-loading, .dash-error { font-size: 13px; text-align: center; padding: 1rem; color: #666; }
.dash-error { color: #f87171; }
</style>
