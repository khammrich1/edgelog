<script setup>
import { onMounted } from 'vue'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

function formatDate(iso) {
  return new Date(iso).toLocaleDateString()
}

onMounted(() => {
  adminStore.fetchRoster()
  adminStore.fetchTraffic()
  adminStore.fetchFeedback()
})
</script>

<template>
  <div class="admin-page">
    <h1>Admin</h1>

    <h2 class="section-title">Account Roster</h2>
    <table class="admin-table">
      <thead>
        <tr>
          <th>Email</th>
          <th>Created</th>
          <th>Admin</th>
          <th>Last activity</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="account in adminStore.roster" :key="account.id">
          <td>{{ account.email }}</td>
          <td>{{ formatDate(account.created_at) }}</td>
          <td>{{ account.is_admin ? 'Yes' : '' }}</td>
          <td>
            <template v-if="account.last_activity_at">
              {{ formatDate(account.last_activity_at) }} ({{ account.last_activity_path }})
            </template>
            <template v-else>No activity yet</template>
          </td>
        </tr>
        <tr v-if="adminStore.roster.length === 0">
          <td colspan="4" class="empty-hint">No accounts yet.</td>
        </tr>
      </tbody>
    </table>

    <h2 class="section-title">Traffic -- Last 7 Days</h2>
    <table class="admin-table">
      <thead>
        <tr>
          <th>Path</th>
          <th>Hits</th>
          <th>Unique auth users</th>
          <th>Auth / unauth</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in adminStore.traffic" :key="row.path">
          <td class="path-cell">{{ row.path }}</td>
          <td>{{ row.hits }}</td>
          <td>{{ row.unique_auth_users }}</td>
          <td>{{ row.auth_hits }} / {{ row.unauth_hits }}</td>
        </tr>
        <tr v-if="adminStore.traffic.length === 0">
          <td colspan="4" class="empty-hint">No traffic recorded yet.</td>
        </tr>
      </tbody>
    </table>

    <h2 class="section-title">Feedback</h2>
    <table class="admin-table">
      <thead>
        <tr>
          <th>From</th>
          <th>Message</th>
          <th>Date</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in adminStore.feedback" :key="item.id">
          <td>{{ item.user_email || 'Unknown' }}</td>
          <td class="message-cell">{{ item.message }}</td>
          <td>{{ formatDate(item.created_at) }}</td>
        </tr>
        <tr v-if="adminStore.feedback.length === 0">
          <td colspan="3" class="empty-hint">No feedback submitted yet.</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.admin-page {
  padding: var(--el-space-8);
  max-width: 1000px;
  margin: 0 auto;
}

.admin-page h1 {
  font-size: var(--el-text-2xl);
  margin: 0 0 var(--el-space-6);
}

.section-title {
  font-size: var(--el-text-sm);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--el-text-muted);
  margin: var(--el-space-8) 0 var(--el-space-3);
}

.admin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--el-text-sm);
}

.admin-table th {
  text-align: left;
  padding: var(--el-space-2) var(--el-space-3);
  color: var(--el-text-subtle);
  font-size: var(--el-text-xs);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid var(--el-border);
}

.admin-table td {
  padding: var(--el-space-2) var(--el-space-3);
  border-bottom: 1px solid var(--el-border);
  color: var(--el-text);
  vertical-align: middle;
}

.path-cell {
  font-family: var(--el-font-mono);
}

.message-cell {
  max-width: 400px;
  white-space: pre-wrap;
}

.empty-hint {
  text-align: center;
  color: var(--el-text-subtle);
  padding: var(--el-space-6);
}

@media (max-width: 640px) {
  .admin-page {
    padding: var(--el-space-4);
  }

  .admin-table {
    display: block;
    overflow-x: auto;
    white-space: nowrap;
  }
}
</style>
