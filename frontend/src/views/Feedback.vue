<script setup>
import { ref } from 'vue'
import { useFeedbackStore } from '@/stores/feedback'

const feedbackStore = useFeedbackStore()

const message = ref('')
const submitting = ref(false)
const submitError = ref(null)
const submitted = ref(false)

async function submit() {
  submitError.value = null
  submitting.value = true
  try {
    await feedbackStore.submitFeedback(message.value.trim())
    message.value = ''
    submitted.value = true
  } catch (error) {
    submitError.value = error.response?.data?.detail || 'Could not submit that. Try again.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="feedback-page">
    <h1>Feedback</h1>
    <p class="feedback-intro">Found a bug, or something you'd like EdgeLog to do differently? Let us know.</p>

    <form class="feedback-form" @submit.prevent="submit">
      <textarea
        v-model="message"
        rows="6"
        placeholder="What's on your mind?"
        maxlength="2000"
        required
      ></textarea>
      <button type="submit" :disabled="submitting || !message.trim()">Send feedback</button>
    </form>

    <p v-if="submitted" class="feedback-success">Thanks -- your feedback was sent.</p>
    <p v-if="submitError" class="submit-error">{{ submitError }}</p>
  </div>
</template>

<style scoped>
.feedback-page {
  padding: var(--el-space-8);
  max-width: 640px;
  margin: 0 auto;
}

.feedback-page h1 {
  font-size: var(--el-text-2xl);
  margin: 0 0 var(--el-space-2);
}

.feedback-intro {
  color: var(--el-text-muted);
  font-size: var(--el-text-sm);
  margin: 0 0 var(--el-space-6);
}

.feedback-form {
  display: flex;
  flex-direction: column;
  gap: var(--el-space-3);
}

.feedback-form textarea {
  padding: var(--el-space-3);
  background-color: var(--el-surface);
  border: 1px solid var(--el-border);
  border-radius: var(--el-radius-sm);
  color: var(--el-text);
  font-size: var(--el-text-sm);
  font-family: inherit;
  resize: vertical;
}

.feedback-form button {
  align-self: flex-start;
  padding: var(--el-space-2) var(--el-space-5);
  background-color: var(--el-copper);
  color: var(--el-bg);
  border: none;
  border-radius: var(--el-radius-sm);
  font-weight: 500;
  cursor: pointer;
}

.feedback-form button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.feedback-success {
  color: var(--el-positive);
  font-size: var(--el-text-sm);
  margin-top: var(--el-space-3);
}

.submit-error {
  color: var(--el-negative);
  font-size: var(--el-text-sm);
  margin-top: var(--el-space-3);
}
</style>
