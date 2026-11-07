<script setup>
import { ref } from 'vue'
import { useDialogFocus } from '@/composables/useDialogFocus'
const emit = defineEmits(['close'])
const element = ref(null)
useDialogFocus(element, () => emit('close'))
</script>
<template><div ref="element" tabindex="-1"><slot /></div></template>
